/* ode_main rev A のファーム（STM32F407VGT6）。Art-Net 受信 → DMX ポート 1、miseru の画面と WebSocket、送信元ロック。 */
#include "board.h"
#include "app.h"
#include "lwip/init.h"
#include "lwip/timeouts.h"
#include "lwip/dhcp.h"
#include "netif/ethernet.h"
#include <string.h>

static struct netif nif;
static uint8_t mac[6];

uint32_t plat_now_ms(void) { return g_ms; }
u32_t sys_now(void) { return g_ms; }
const uint8_t *plat_mac(void) { return mac; }

static void make_fallback_mac(void)
{
    /* EEPROM が読めないとき: チップ固有の ID から作る（ローカル管理アドレス 02:xx） */
    const uint32_t *uid = (const uint32_t *)UID_BASE;
    uint32_t h = uid[0] ^ (uid[1] * 2654435761u) ^ (uid[2] * 40503u);
    mac[0] = 0x02; mac[1] = 0x0D; mac[2] = 0xE0;
    mac[3] = h >> 16; mac[4] = h >> 8; mac[5] = h;
}

static void status_cb(struct netif *n)
{
    const uint8_t *ip = (const uint8_t *)&netif_ip4_addr(n)->addr;
    board_log("ip: %u.%u.%u.%u\n", ip[0], ip[1], ip[2], ip[3]);
}

static void link_cb(struct netif *n)
{
    if (netif_is_link_up(n) && g_settings.dhcp) dhcp_start(n);
}

/* ボタンを押したまま電源を入れたら、IP と PIN を初期値に戻す（仕様 v1） */
static void boot_button_check(void)
{
    if (!board_button_raw()) return;
    for (int i = 0; i < 30; i++) {            /* 1.5 秒押し続けたら */
        board_delay_ms(50);
        if (!board_button_raw()) return;
    }
    settings_reset_ip_pin(&g_settings);
    flash_settings_save(&g_settings);
    board_log("settings: IP と PIN を初期値に戻した\n");
    for (int i = 0; i < 10; i++) {            /* 両方の LED を 5 回点滅して知らせる */
        board_led_stat(i & 1); plat_led_lock(i & 1);
        board_delay_ms(150);
    }
    while (board_button_raw()) board_delay_ms(10);
}

extern uint32_t _sccm, _eccm;

int main(void)
{
    board_dfu_check();                        /* クロックを触る前に（リセット直後の HSI のまま渡す） */
    for (uint32_t *p = &_sccm; p < &_eccm; p++) *p = 0;   /* CCM の変数を 0 に */
    board_clock_init();
    board_gpio_init();
    DBGMCU->APB1FZ |= DBGMCU_APB1_FZ_DBG_IWDG_STOP;   /* デバッガで止めたときは番犬も止める */
    board_iwdg_init();
    board_uart_init();
    board_log("\node_main fw %s (%s %s)\n", FW_VERSION_STR, __DATE__, __TIME__);
    if (RCC->CSR & RCC_CSR_IWDGRSTF) board_log("reset: watchdog\n");
    RCC->CSR |= RCC_CSR_RMVF;

    dmx_init();                               /* 起動直後から全消灯を出し続ける（規則 6） */

    if (!flash_settings_load(&g_settings)) settings_default(&g_settings);
    boot_button_check();

    if (!mac_eeprom_read(mac)) { make_fallback_mac(); board_log("mac: EEPROM が読めない。仮の値を使う\n"); }
    board_log("mac: %02x:%02x:%02x:%02x:%02x:%02x\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    lwip_init();
    eth_init(&nif, mac);
    ip4_addr_t ip, mask, gw;
    ip.addr = g_settings.dhcp ? 0 : g_settings.ip;
    mask.addr = g_settings.dhcp ? 0 : g_settings.mask;
    gw.addr = g_settings.dhcp ? 0 : g_settings.gw;
    netif_add(&nif, &ip, &mask, &gw, NULL, eth_netif_init, ethernet_input);
    netif_set_default(&nif);
    netif_set_hostname(&nif, "ode");
    netif_set_status_callback(&nif, status_cb);
    netif_set_link_callback(&nif, link_cb);
    netif_set_up(&nif);
    app_init(&nif);

    uint32_t t_link = 0, t_led = 0, t_btn = 0, t_press = 0;
    bool btn_prev = false, long_done = false;
    for (;;) {
        board_iwdg_kick();
        eth_poll(&nif);
        sys_check_timeouts();
        app_poll();

        uint32_t now = g_ms;
        if ((uint32_t)(now - t_link) >= 250) { t_link = now; eth_link_poll(&nif); }
        /* STAT LED: リンクあり = 1 秒ごとに点滅、リンクなし = 速い点滅 */
        uint32_t period = netif_is_link_up(&nif) ? 1000 : 200;
        if ((uint32_t)(now - t_led) >= period / 2) { t_led = now; board_led_stat(!(GPIOC->ODR & (1u << 11))); }
        /* ボタン（30ms のチャタリング除け）。短押しは離した瞬間にロック解除と全消灯、3 秒の長押しは差し替えの窓 */
        if ((uint32_t)(now - t_btn) >= 30) {
            t_btn = now;
            bool b = board_button_raw();
            /* v0.3.0: 短押し（3 秒未満で離す）は離した瞬間にロック解除と全消灯。長押しは窓を開くだけで照明は消さない
             * （2026-11-23 作者の決定、別スレッドのチェックの中 1） */
            if (b && !btn_prev) { t_press = now; long_done = false; }
            if (!b && btn_prev && !long_done) { board_log("button: release lock\n"); app_button(); }
            /* 3 秒押し続けたら、画面の差し替えとファーム更新モードを 10 分だけ受ける（v0.3.0） */
            if (b && btn_prev && !long_done && (uint32_t)(now - t_press) >= 3000) {
                long_done = true;
                app_ui_window_open();
                board_log("button: 差し替えの窓を 10 分開いた\n");
                for (int i = 0; i < 6; i++) {       /* 両方の LED を 3 回点滅して知らせる */
                    board_led_stat(!(i & 1)); plat_led_lock(!(i & 1));
                    board_delay_ms(100);
                }
                plat_led_lock(g_box.owner != OWNER_NONE);
            }
            btn_prev = b;
        }
    }
}
