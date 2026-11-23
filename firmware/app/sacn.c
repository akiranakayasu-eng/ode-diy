/* sACN（ANSI E1.31）の受信。設定のユニバース（初期 1）のデータを、Art-Net と同じロックの規則で DMX に出す。
 * マルチキャスト 239.255.<上位>.<下位> に参加し、ユニキャストも受ける。プレビューのデータは使わない。
 * 優先度（priority）と同期（E1.31 Sync）は見ない（送り手は 1 つだけロックできるため）。 */
#include "app.h"
#include "lwip/udp.h"
#include "lwip/igmp.h"
#include <string.h>

#define SACN_PORT 5568

static struct udp_pcb *pcb;
static const uint8_t ACN_ID[12] = { 'A', 'S', 'C', '-', 'E', '1', '.', '1', '7', 0, 0, 0 };

static uint32_t be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | p[2] << 8 | p[3]; }

static void recv_cb(void *arg, struct udp_pcb *upcb, struct pbuf *p, const ip_addr_t *addr, u16_t port)
{
    (void)arg; (void)upcb; (void)port;
    static uint8_t buf[126 + DMX_SLOTS];
    uint16_t n = pbuf_copy_partial(p, buf, sizeof(buf), 0);
    pbuf_free(p);
    if (g_settings.sacn_off) return;
    if (n < 126) return;
    if (buf[0] != 0x00 || buf[1] != 0x10 || memcmp(buf + 4, ACN_ID, 12) != 0) return;
    if (be32(buf + 18) != 0x00000004) return;            /* VECTOR_ROOT_E131_DATA */
    if (be32(buf + 40) != 0x00000002) return;            /* VECTOR_E131_DATA_PACKET */
    uint8_t options = buf[112];
    uint16_t universe = buf[113] << 8 | buf[114];
    if (universe != settings_sacn_universe(&g_settings)) return;
    if (options & 0x80) return;                          /* Preview_Data */
    uint32_t ip = ip_2_ip4(addr)->addr;
    uint32_t before = g_box.version;
    if (options & 0x40) {                                /* Stream_Terminated */
        box_net_terminated(&g_box, OWNER_SACN, ip);
    } else {
        if (buf[117] != 0x02 || buf[118] != 0xa1) return; /* DMP の vector と address type */
        int count = (buf[123] << 8 | buf[124]) - 1;       /* スタートコードの分を引く */
        if (buf[125] != 0x00) return;                    /* スタートコード 0 だけ */
        if (count > n - 126) count = n - 126;
        if (count < 0) return;
        box_net(&g_box, OWNER_SACN, ip, buf + 126, count, plat_now_ms());
    }
    if (g_box.version != before) ws_broadcast_status();
}

void sacn_init(struct netif *nif)
{
    pcb = udp_new();
    udp_bind(pcb, IP_ADDR_ANY, SACN_PORT);
    udp_recv(pcb, recv_cb, NULL);
    if (g_settings.sacn_off) return;
    uint16_t u = settings_sacn_universe(&g_settings);
    ip4_addr_t group;
    IP4_ADDR(&group, 239, 255, u >> 8, u & 0xff);
    igmp_joingroup_netif(nif, &group);
}
