/* Linux で試す host 版。TAP（tap0）に lwIP を載せ、本物の箱と同じアプリを動かす。
 * DMX は出さず、変わったときに先頭の値を表示する。 */
#include "app.h"
#include "lwip/init.h"
#include "lwip/timeouts.h"
#include "lwip/etharp.h"
#include "lwip/dhcp.h"
#include "netif/ethernet.h"
#include <fcntl.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include <stdio.h>
#include <poll.h>

static int tapfd;
static struct netif nif;
static const uint8_t mac[6] = {0x02, 0x00, 0x0d, 0xe0, 0x00, 0x01};

uint32_t plat_now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}
u32_t sys_now(void) { return plat_now_ms(); }
void plat_dmx_write(const uint8_t *s) { printf("[dmx] %u %u %u %u ...\n", s[0], s[1], s[2], s[3]); fflush(stdout); }
void plat_led_lock(bool on) { printf("[led] lock %s\n", on ? "on" : "off"); fflush(stdout); }
void plat_settings_save(const settings_t *s) { printf("[flash] save show_mode=%d pin=%s\n", s->show_mode, s->pin); fflush(stdout); }
void plat_reboot(void) { static int once; if (!once++) { printf("[reboot]（試験版は再起動しない）\n"); fflush(stdout); } }
void plat_enter_dfu(void) { static int once; if (!once++) { printf("[dfu]\n"); fflush(stdout); } }
const uint8_t *plat_mac(void) { return mac; }
static uint8_t ui_area[3 * 0x20000];   /* STM32 と同じ 384KB */
const uint8_t *plat_ui_base(void) { return ui_area; }
uint32_t plat_ui_size(void) { return sizeof(ui_area); }
void plat_ui_erase(void) { memset(ui_area, 0xFF, sizeof(ui_area)); printf("[flash] ui erase\n"); fflush(stdout); }
void plat_ui_write(uint32_t off, const uint8_t *d, uint32_t n) { for (uint32_t i = 0; i < n && off + i < sizeof(ui_area); i++) ui_area[off + i] &= d[i]; }

static err_t tap_output(struct netif *n, struct pbuf *p)
{
    (void)n;
    uint8_t buf[1600];
    u16_t len = pbuf_copy_partial(p, buf, sizeof(buf), 0);
    if (write(tapfd, buf, len) < 0) perror("write");
    return ERR_OK;
}

static err_t tap_init(struct netif *n)
{
    n->name[0] = 'e'; n->name[1] = '0';
    n->output = etharp_output;
    n->linkoutput = tap_output;
    n->mtu = 1500;
    n->hwaddr_len = 6;
    memcpy(n->hwaddr, mac, 6);
    n->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_ETHARP | NETIF_FLAG_ETHERNET | NETIF_FLAG_IGMP;
    return ERR_OK;
}

int main(int argc, char **argv)
{
    const char *dev = argc > 1 ? argv[1] : "tap0";
    tapfd = open("/dev/net/tun", O_RDWR | O_NONBLOCK);
    struct ifreq ifr = {0};
    ifr.ifr_flags = IFF_TAP | IFF_NO_PI;
    strncpy(ifr.ifr_name, dev, IFNAMSIZ - 1);
    if (tapfd < 0 || ioctl(tapfd, TUNSETIFF, &ifr) < 0) { perror("tap"); return 1; }

    settings_default(&g_settings);
    memset(ui_area, 0xFF, sizeof(ui_area));
    lwip_init();
    ip4_addr_t ip, mask, gw;
    ip.addr = g_settings.ip; mask.addr = g_settings.mask; gw.addr = g_settings.gw;
    netif_add(&nif, &ip, &mask, &gw, NULL, tap_init, ethernet_input);
    netif_set_default(&nif);
    netif_set_up(&nif);
    netif_set_link_up(&nif);
    app_init(&nif);
    printf("ode host: %s http://%s/ (max_clients %d, pin %s)\n", dev, ip4addr_ntoa(&ip), APP_MAX_CLIENTS, g_settings.pin);
    fflush(stdout);
    for (;;) {
        struct pollfd pf[2] = { { tapfd, POLLIN, 0 }, { 0, POLLIN, 0 } };
        poll(pf, 2, 5);
        /* 標準入力で本体ボタンのまね: "b" = 短く押す、"l" = 3 秒の長押し（差し替えの窓を開く） */
        if (pf[1].revents & POLLIN) {
            char line[16];
            if (fgets(line, sizeof line, stdin)) {
                if (line[0] == 'b') { printf("[button] short\n"); app_button(); }
                if (line[0] == 'l') { printf("[button] long: ui window open（照明は消さない）\n"); app_ui_window_open(); }
                fflush(stdout);
            }
        }
        uint8_t buf[1600];
        ssize_t n;
        while ((n = read(tapfd, buf, sizeof(buf))) > 0) {
            struct pbuf *p = pbuf_alloc(PBUF_RAW, (u16_t)n, PBUF_POOL);
            if (!p) { printf("pbuf pool empty\n"); break; }
            pbuf_take(p, buf, (u16_t)n);
            if (nif.input(p, &nif) != ERR_OK) pbuf_free(p);
        }
        sys_check_timeouts();
        app_poll();
    }
}
