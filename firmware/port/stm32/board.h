/* ode_main rev A のピン割り当て（回路図 ode_main.kicad_sch / netlist.net から）
 *
 *   DMX TX1 / TX2   PE0 / PE1  → U7 / U8 74AHCT1G125 → U11 / U21 ADM2587E TxD（rev A は U8・U21 未実装）
 *   DE（送信許可）  PD7 EN_M   → U9 → ADM2587E DE と ~RE（R74 10k でプルダウン。High で送信）
 *   RMII            PA1 REF_CLK, PA2 MDIO, PA7 CRS_DV, PC1 MDC, PC4 RXD0, PC5 RXD1, PB11 TX_EN, PB12 TXD0, PB13 TXD1
 *   PHY nRST        PB14（R64 でプルアップ）。LAN8742A の PHYAD0 は未接続（内部プルダウン）→ アドレス 0
 *   LED             PC10 LOCK（D5）、PC11 STAT（D6）。High で点灯（680Ω → LED → GND）
 *   ボタン          PD4 LOCK（SW2 → GND、外付けプルアップなし → 内部プルアップ）
 *   EEPROM          PB6 SCL, PB7 SDA（U4 24AA02E48、MAC は 0xFA〜0xFF）
 *   UART            PA9 TX, PA10 RX（J4: 1 GND, 2 TX, 3 RX、115200bps 8N1、3.3V）
 *   HSE             8MHz（Y1）
 */
#ifndef BOARD_H
#define BOARD_H
#include "stm32f4xx.h"
#include <stdint.h>
#include <stdbool.h>

extern volatile uint32_t g_ms;

void board_dfu_check(void);           /* 目印があれば ROM の USB DFU へ飛ぶ（main の最初に呼ぶ） */
void board_clock_init(void);
void board_gpio_init(void);
void board_iwdg_init(void);
static inline void board_iwdg_kick(void) { IWDG->KR = 0xAAAA; }
bool board_button_raw(void);          /* 押されていれば true */
void board_led_stat(bool on);
void board_uart_init(void);
void board_log(const char *fmt, ...);
void board_delay_ms(uint32_t ms);

/* eth.c */
struct netif;
int  eth_init(struct netif *nif, const uint8_t mac[6]);   /* lwIP の netif_add に渡す初期化は eth_netif_init */
signed char eth_netif_init(struct netif *nif);
void eth_poll(struct netif *nif);       /* 受信をすべて lwIP に渡す */
void eth_link_poll(struct netif *nif);  /* 250ms ごとにリンクを見る */
extern uint16_t g_phy_id1, g_phy_id2;
extern int g_phy_addr;

/* dmx.c */
void dmx_init(void);
void dmx_set(const uint8_t *slots512);
extern volatile uint32_t g_dmx_frames;

/* flash_settings.c */
#include "settings.h"
bool flash_settings_load(settings_t *s);
void flash_settings_save(const settings_t *s);

/* mac_eeprom.c */
bool mac_eeprom_read(uint8_t mac[6]);
#endif
