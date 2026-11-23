/* 機種に依らない部分（ロック、Art-Net、HTTP、WebSocket）。lwIP の raw API（NO_SYS=1）で動く。 */
#ifndef APP_H
#define APP_H
#include <stdint.h>
#include <stdbool.h>
#include "settings.h"
#include "box_core.h"
#include "lwip/netif.h"

#define FW_VERSION_STR "0.3.6"
#ifndef HTTP_PORT
#define HTTP_PORT 80
#endif

/* ---- 機種ごとに用意する関数（port/ 側） ---- */
uint32_t plat_now_ms(void);
void plat_dmx_write(const uint8_t *slots); /* 512 スロットを DMX の出力に渡す */
void plat_led_lock(bool on);
void plat_settings_save(const settings_t *s);
void plat_enter_dfu(void);                /* USB DFU（ROM のブートローダ）で再起動 */
void plat_reboot(void);                    /* 設定を変えたあとの再起動 */
const uint8_t *plat_mac(void);
/* 差し替え画面の置き場（STM32 はフラッシュのセクタ 8〜10、384KB）。消すと 0xFF、書けるのは 1 回だけ */
const uint8_t *plat_ui_base(void);
uint32_t plat_ui_size(void);
void plat_ui_erase(void);
void plat_ui_write(uint32_t off, const uint8_t *d, uint32_t n);

/* ---- アプリ ---- */
extern box_core_t g_box;
extern settings_t g_settings;
#define APP_MAX_CLIENTS BOX_MAX_CONN

void app_init(struct netif *nif);
void app_poll(void);        /* メインループから何度でも呼ぶ */
void app_button(void);      /* 押しボタン: ロック解除と全消灯 */
/* 本体ボタンの長押し（3 秒）で開く「差し替えの窓」（10 分）。開いている間だけ
 * 画面の差し替え・内蔵の画面に戻す・ファーム更新モードを受ける（2026-11-20 作者の決定） */
#define UI_WINDOW_MS (10u * 60u * 1000u)
void app_ui_window_open(void);
uint32_t app_ui_window_left_s(void);   /* 閉じていれば 0 */

/* artnet.c */
void artnet_init(struct netif *nif);
void artnet_poll(void);
/* ui.c（差し替え画面） */
#define UI_MAX (plat_ui_size() - 16u)   /* 見出し 16 バイトを除いた中身の上限（STM32 は 393,200 バイト） */
typedef struct {
    const char *path; int plen;
    const char *mime; int mlen;
    const uint8_t *data; uint32_t len;
    uint8_t gzip;
} ui_file_t;
extern bool g_ui_valid;
extern uint32_t g_ui_len;
void ui_check(void);
bool ui_find(const char *path, ui_file_t *out);   /* 差し替え画面があればそこから、無ければ内蔵から */
bool ui_upload_begin(uint32_t len);
void ui_upload_data(const uint8_t *d, uint32_t n);
bool ui_upload_end(void);
void ui_reset(void);
/* sacn.c */
void sacn_init(struct netif *nif);
/* http.c */
void http_init(void);
void http_poll(void);
void ws_broadcast_status(void);
#endif
