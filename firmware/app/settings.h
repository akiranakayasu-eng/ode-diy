/* フラッシュに保存する設定 */
#ifndef SETTINGS_H
#define SETTINGS_H
#include <stdint.h>
#include <stdbool.h>

#define SETTINGS_MAGIC    0x4F444532u /* "ODE2"（v0.2〜、128 バイト） */
#define SETTINGS_MAGIC_V1 0x4F444531u /* "ODE1"（v0.1、80 バイト。読むときに v2 に直す） */
#define SETTINGS_V1_SIZE  80
#define ALLOW_MAX 8

typedef struct {
    uint32_t magic;
    uint32_t seq;          /* 書くたびに増える（ログ形式で最後の 1 件を探すため） */
    uint8_t  dhcp;         /* 0 = 固定 IP、1 = DHCP */
    uint8_t  show_mode;    /* 公演モード（電源を入れ直しても残す） */
    uint16_t universe;     /* Art-Net の 15 bit Port-Address（Net<<8 | Sub<<4 | Uni） */
    uint32_t ip, mask, gw; /* ネットワーク順（lwIP の ip4_addr_t.addr と同じ） */
    char     pin[16];      /* 先生の PIN */
    char     name[18];     /* ArtPollReply の短い名前 */
    /* ---- ここまで v1 と同じ並び（v1 ではこの先が 0 埋め） ---- */
    uint16_t sacn_universe;/* sACN（E1.31）のユニバース。0 なら 1 として扱う */
    uint8_t  sacn_off;     /* 1 = sACN を受けない（0 = 受ける） */
    uint8_t  allow_on;     /* 1 = 許可リストを使う */
    uint8_t  reserved[10];
    uint32_t allow[ALLOW_MAX]; /* 許可する IP（ネットワーク順、0 は空き） */
    uint8_t  reserved2[20];
    uint32_t crc;          /* ここより前の CRC32 */
} settings_t;              /* 128 バイト */

/* 初期値（miseru との取り決め） */
void settings_default(settings_t *s);
/* IP と PIN だけ初期値に戻す（ボタンを押したまま電源を入れたとき） */
void settings_reset_ip_pin(settings_t *s);
uint32_t settings_crc(const settings_t *s);
uint32_t crc32_buf(const void *p, unsigned len);
uint16_t settings_sacn_universe(const settings_t *s);
bool settings_allowed(const settings_t *s, uint32_t ip);  /* 許可リストが切なら常に true */
#endif
