/* Art-Net 4 の受信。ArtDmx（Port-Address が設定と同じもの）をロックに渡し、ArtPoll に ArtPollReply を返す。 */
#include "app.h"
#include "lwip/udp.h"
#include <string.h>
#include <stdio.h>

#define ARTNET_PORT 6454
#define OP_POLL 0x2000
#define OP_POLLREPLY 0x2100
#define OP_DMX 0x5000
#define FW_VERSION 0x0001

static struct udp_pcb *pcb;
static struct netif *g_nif;
static uint32_t dmx_count, poll_count;

static void send_poll_reply(const ip_addr_t *to)
{
    struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, 239, PBUF_RAM);
    if (!p) return;
    uint8_t *r = (uint8_t *)p->payload;
    memset(r, 0, 239);
    memcpy(r, "Art-Net", 8);
    r[8] = OP_POLLREPLY & 0xff; r[9] = OP_POLLREPLY >> 8;
    memcpy(r + 10, &netif_ip4_addr(g_nif)->addr, 4);
    r[14] = ARTNET_PORT & 0xff; r[15] = ARTNET_PORT >> 8;
    r[16] = FW_VERSION >> 8; r[17] = FW_VERSION & 0xff;
    uint16_t pa = g_settings.universe;
    r[18] = (pa >> 8) & 0x7f;        /* NetSwitch */
    r[19] = (pa >> 4) & 0x0f;        /* SubSwitch */
    r[20] = 0x00; r[21] = 0xff;      /* OEM: 未登録 */
    r[23] = 0xe0;                    /* Status1: 表示灯は通常、設定はネットワーク（Web）から */
    r[24] = 0xf0; r[25] = 0x7f;      /* ESTA: 0x7FF0（試作用） */
    strncpy((char *)r + 26, g_settings.name, 17);
    snprintf((char *)r + 44, 64, "ODE-DIY rev A Art-Net/sACN to DMX");
    snprintf((char *)r + 108, 64, "#0001 [%04lu] OK dmx=%lu", (unsigned long)(poll_count % 10000), (unsigned long)dmx_count);
    r[172] = 0; r[173] = 1;          /* ポート 1 つ */
    r[174] = 0x80;                   /* 出力、DMX512 */
    r[182] = (g_box.owner == OWNER_ARTNET) ? 0x80 : 0x00; /* GoodOutputA: 出力中 */
    r[190] = pa & 0x0f;              /* SwOut */
    r[200] = 0x00;                   /* StNode */
    memcpy(r + 201, plat_mac(), 6);
    memcpy(r + 207, &netif_ip4_addr(g_nif)->addr, 4);
    r[211] = 1;                      /* BindIndex */
    r[212] = 0x08 | 0x04 | (g_settings.dhcp ? 0x02 : 0) | 0x01; /* 15bit PA、DHCP 可、DHCP 中、Web 設定 */
    r[213] = 0xc0;                   /* GoodOutputB: RDM なし、連続送出 */
    udp_sendto(pcb, p, to, ARTNET_PORT);
    pbuf_free(p);
}

static void recv_cb(void *arg, struct udp_pcb *upcb, struct pbuf *p, const ip_addr_t *addr, u16_t port)
{
    (void)arg; (void)upcb; (void)port;
    static uint8_t buf[18 + DMX_SLOTS];
    uint16_t n = pbuf_copy_partial(p, buf, sizeof(buf), 0);
    pbuf_free(p);
    if (n < 12 || memcmp(buf, "Art-Net", 8) != 0) return;
    uint16_t op = buf[8] | buf[9] << 8;
    if (op == OP_DMX) {
        if (n < 18) return;
        uint16_t pa = buf[14] | (buf[15] & 0x7f) << 8;
        if (pa != g_settings.universe) return;
        int len = buf[16] << 8 | buf[17];
        if (len > n - 18) len = n - 18;
        if (len > DMX_SLOTS) len = DMX_SLOTS;
        dmx_count++;
        uint32_t before = g_box.version;
        box_artnet(&g_box, ip_2_ip4(addr)->addr, buf + 18, len, plat_now_ms());
        if (g_box.version != before) ws_broadcast_status();
    } else if (op == OP_POLL) {
        poll_count++;
        send_poll_reply(addr);
    }
}

void artnet_init(struct netif *nif)
{
    g_nif = nif;
    pcb = udp_new();
    ip_set_option(pcb, SOF_BROADCAST);
    udp_bind(pcb, IP_ADDR_ANY, ARTNET_PORT);
    udp_recv(pcb, recv_cb, NULL);
}
