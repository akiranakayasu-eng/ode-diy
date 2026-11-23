/* STM32F407 の Ethernet MAC（RMII、LAN8742A）と lwIP のつなぎ。HAL を使わずレジスタで書いた。
 * 受信はメインループからのポーリング（割り込みなし）。DMA の記述子は普通の形（16 バイト、リング）。 */
#include "board.h"
#include "lwip/opt.h"
#include "lwip/pbuf.h"
#include "lwip/netif.h"
#include "lwip/etharp.h"
#include "lwip/dhcp.h"
#include "netif/ethernet.h"
#include <string.h>

#define RX_N 8
#define TX_N 4
#define BUF_SZ 1524

typedef struct { volatile uint32_t des0, des1, des2, des3; } desc_t;

static desc_t rxd[RX_N] __attribute__((aligned(4)));
static desc_t txd[TX_N] __attribute__((aligned(4)));
static uint8_t rxb[RX_N][BUF_SZ] __attribute__((aligned(4)));
static uint8_t txb[TX_N][BUF_SZ] __attribute__((aligned(4)));
static int rxi, txi;
static uint8_t g_mac[6];
uint16_t g_phy_id1, g_phy_id2;
int g_phy_addr = 0;

#define RDES0_OWN (1u << 31)
#define RDES0_ES  (1u << 15)
#define RDES0_FS  (1u << 9)
#define RDES0_LS  (1u << 8)
#define RDES1_RER (1u << 15)
#define TDES0_OWN (1u << 31)
#define TDES0_LS  (1u << 29)
#define TDES0_FS  (1u << 28)
#define TDES0_CIC (3u << 22)    /* IP ヘッダとペイロードのチェックサムを MAC が入れる */
#define TDES0_TER (1u << 21)

/* ---- PHY（MDIO） ---- */
static uint16_t phy_read(int addr, int reg)
{
    ETH->MACMIIAR = ((uint32_t)addr << 11) | ((uint32_t)reg << 6) | ETH_MACMIIAR_CR_Div102 | ETH_MACMIIAR_MB;
    for (uint32_t t = 0; (ETH->MACMIIAR & ETH_MACMIIAR_MB) && t < 100000; t++) {}
    return (uint16_t)ETH->MACMIIDR;
}
static void phy_write(int addr, int reg, uint16_t v)
{
    ETH->MACMIIDR = v;
    ETH->MACMIIAR = ((uint32_t)addr << 11) | ((uint32_t)reg << 6) | ETH_MACMIIAR_CR_Div102 | ETH_MACMIIAR_MW | ETH_MACMIIAR_MB;
    for (uint32_t t = 0; (ETH->MACMIIAR & ETH_MACMIIAR_MB) && t < 100000; t++) {}
}

static void af11(GPIO_TypeDef *g, int pin)
{
    g->MODER = (g->MODER & ~(3u << (pin * 2))) | (2u << (pin * 2));
    g->OSPEEDR |= 3u << (pin * 2);
    g->OTYPER &= ~(1u << pin);
    g->PUPDR &= ~(3u << (pin * 2));
    if (pin < 8) g->AFR[0] = (g->AFR[0] & ~(0xfu << (pin * 4))) | (11u << (pin * 4));
    else g->AFR[1] = (g->AFR[1] & ~(0xfu << ((pin - 8) * 4))) | (11u << ((pin - 8) * 4));
}

static void desc_init(void)
{
    for (int i = 0; i < RX_N; i++) {
        rxd[i].des1 = BUF_SZ | (i == RX_N - 1 ? RDES1_RER : 0);
        rxd[i].des2 = (uint32_t)rxb[i];
        rxd[i].des3 = 0;
        rxd[i].des0 = RDES0_OWN;
    }
    for (int i = 0; i < TX_N; i++) {
        txd[i].des0 = (i == TX_N - 1 ? TDES0_TER : 0);
        txd[i].des1 = 0;
        txd[i].des2 = (uint32_t)txb[i];
        txd[i].des3 = 0;
    }
    rxi = txi = 0;
    ETH->DMARDLAR = (uint32_t)rxd;
    ETH->DMATDLAR = (uint32_t)txd;
}

int eth_init(struct netif *nif, const uint8_t mac[6])
{
    (void)nif;
    memcpy(g_mac, mac, 6);
    /* RMII を選んでから MAC のクロックを入れる */
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC->APB2ENR;
    SYSCFG->PMC |= SYSCFG_PMC_MII_RMII_SEL;

    af11(GPIOA, 1); af11(GPIOA, 2); af11(GPIOA, 7);
    af11(GPIOB, 11); af11(GPIOB, 12); af11(GPIOB, 13);
    af11(GPIOC, 1); af11(GPIOC, 4); af11(GPIOC, 5);

    /* PHY をリセット（PB14 を 1ms Low）。REF_CLK（50MHz）は PHY から来る */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << 28)) | (1u << 28);
    GPIOB->BSRR = 1u << (14 + 16);
    board_delay_ms(2);
    GPIOB->BSRR = 1u << 14;
    board_delay_ms(10);

    RCC->AHB1ENR |= RCC_AHB1ENR_ETHMACEN | RCC_AHB1ENR_ETHMACTXEN | RCC_AHB1ENR_ETHMACRXEN;
    RCC->AHB1RSTR |= RCC_AHB1RSTR_ETHMACRST;
    RCC->AHB1RSTR &= ~RCC_AHB1RSTR_ETHMACRST;

    ETH->DMABMR |= ETH_DMABMR_SR;
    uint32_t t0 = g_ms;
    while (ETH->DMABMR & ETH_DMABMR_SR) {
        if ((uint32_t)(g_ms - t0) > 500) { board_log("eth: DMA reset timeout (REF_CLK?)\n"); return -1; }
    }

    ETH->MACMIIAR = ETH_MACMIIAR_CR_Div102;
    /* PHY のアドレスを探す（基板では 0 のはず） */
    g_phy_addr = -1;
    for (int a = 0; a < 32; a++) {
        uint16_t id1 = phy_read(a, 2);
        if (id1 != 0xFFFF && id1 != 0x0000) { g_phy_addr = a; g_phy_id1 = id1; g_phy_id2 = phy_read(a, 3); break; }
    }
    if (g_phy_addr < 0) { board_log("eth: PHY not found\n"); g_phy_addr = 0; }
    board_log("eth: PHY addr %d id %04x %04x\n", g_phy_addr, g_phy_id1, g_phy_id2);
    phy_write(g_phy_addr, 0, 0x8000);                 /* ソフトリセット */
    board_delay_ms(5);
    for (uint32_t t = g_ms; (phy_read(g_phy_addr, 0) & 0x8000) && (uint32_t)(g_ms - t) < 500;) {}
    phy_write(g_phy_addr, 0, 0x1000);                 /* オートネゴシエーション */

    ETH->MACA0HR = (uint32_t)mac[5] << 8 | mac[4];
    ETH->MACA0LR = (uint32_t)mac[3] << 24 | (uint32_t)mac[2] << 16 | (uint32_t)mac[1] << 8 | mac[0];
    ETH->MACFFR = ETH_MACFFR_PAM;                     /* 自分宛て、ブロードキャスト、マルチキャスト（sACN）を受ける */
    ETH->MACFCR = 0;
    ETH->MACCR = ETH_MACCR_IPCO | ETH_MACCR_FES | ETH_MACCR_DM;

    desc_init();
    ETH->DMABMR = ETH_DMABMR_AAB | ETH_DMABMR_FB | ETH_DMABMR_RDP_32Beat | ETH_DMABMR_PBL_32Beat | ETH_DMABMR_USP;
    ETH->DMAOMR = ETH_DMAOMR_RSF | ETH_DMAOMR_TSF;
    ETH->DMAIER = 0;

    ETH->MACCR |= ETH_MACCR_TE;
    ETH->DMAOMR |= ETH_DMAOMR_FTF;
    while (ETH->DMAOMR & ETH_DMAOMR_FTF) {}
    ETH->MACCR |= ETH_MACCR_RE;
    ETH->DMAOMR |= ETH_DMAOMR_ST | ETH_DMAOMR_SR;
    return 0;
}

static err_t low_level_output(struct netif *nif, struct pbuf *p)
{
    (void)nif;
    desc_t *d = &txd[txi];
    for (uint32_t t = g_ms; d->des0 & TDES0_OWN;) if ((uint32_t)(g_ms - t) > 20) return ERR_TIMEOUT;
    if (p->tot_len > BUF_SZ) return ERR_BUF;
    pbuf_copy_partial(p, txb[txi], p->tot_len, 0);
    d->des1 = p->tot_len;
    d->des0 = (d->des0 & TDES0_TER) | TDES0_FS | TDES0_LS | TDES0_CIC | TDES0_OWN;
    txi = (txi + 1) % TX_N;
    if (ETH->DMASR & ETH_DMASR_TBUS) { ETH->DMASR = ETH_DMASR_TBUS; }
    ETH->DMATPDR = 0;
    return ERR_OK;
}

void eth_poll(struct netif *nif)
{
    for (int n = 0; n < RX_N; n++) {
        desc_t *d = &rxd[rxi];
        uint32_t s = d->des0;
        if (s & RDES0_OWN) break;
        if ((s & (RDES0_FS | RDES0_LS)) == (RDES0_FS | RDES0_LS) && !(s & RDES0_ES)) {
            uint16_t len = (uint16_t)(((s >> 16) & 0x3FFF) - 4);   /* CRC の 4 バイトを除く */
            struct pbuf *p = pbuf_alloc(PBUF_RAW, len, PBUF_POOL);
            if (p) {
                pbuf_take(p, rxb[rxi], len);
                if (nif->input(p, nif) != ERR_OK) pbuf_free(p);
            }
        }
        d->des0 = RDES0_OWN;
        rxi = (rxi + 1) % RX_N;
    }
    if (ETH->DMASR & ETH_DMASR_RBUS) { ETH->DMASR = ETH_DMASR_RBUS; ETH->DMARPDR = 0; }
}

void eth_link_poll(struct netif *nif)
{
    uint16_t bsr = phy_read(g_phy_addr, 1);
    bsr = phy_read(g_phy_addr, 1);                    /* リンク状態は 2 回読んで今の値 */
    bool up = (bsr & 0x0004) != 0;
    if (up && !netif_is_link_up(nif)) {
        if (!(bsr & 0x0020)) return;                  /* オートネゴシエーションの完了を待つ */
        uint16_t sc = phy_read(g_phy_addr, 31);
        int speed100 = (sc >> 3) & 1, full = (sc >> 4) & 1;
        uint32_t cr = ETH->MACCR & ~(ETH_MACCR_FES | ETH_MACCR_DM);
        if (speed100) cr |= ETH_MACCR_FES;
        if (full) cr |= ETH_MACCR_DM;
        ETH->MACCR = cr;
        board_log("eth: link up %s %s\n", speed100 ? "100M" : "10M", full ? "full" : "half");
        netif_set_link_up(nif);
    } else if (!up && netif_is_link_up(nif)) {
        board_log("eth: link down\n");
        netif_set_link_down(nif);
    }
}

signed char eth_netif_init(struct netif *nif)
{
    nif->name[0] = 'e';
    nif->name[1] = '0';
    nif->output = etharp_output;
    nif->linkoutput = low_level_output;
    nif->mtu = 1500;
    nif->hwaddr_len = 6;
    memcpy(nif->hwaddr, g_mac, 6);
    nif->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_ETHARP | NETIF_FLAG_ETHERNET | NETIF_FLAG_IGMP;
    return ERR_OK;
}
