/* 管理画面からの画面の差し替え（仕様 v1: gzip 後で合計 120kB まで）。
 * 置き場（plat_ui_base）の形:
 *   0: "ODEUI1\0\0"、8: 中身の長さ（LE32）、12: 中身の CRC32（LE32）、16〜: 中身
 *   中身 = ファイルの並び: [パスの長さ u8][パス][MIME の長さ u8][MIME][gzip u8][長さ LE32][データ]
 * 中身を先に書き、最後に見出し（先頭 16 バイト）を書く。途中で切れたら見出しが無いので内蔵の画面に戻る。 */
#include "app.h"
#include "assets.h"
#include <string.h>

#define HDR 16
static const char MAGIC[8] = "ODEUI1\0";

bool g_ui_valid;
uint32_t g_ui_len;
static uint32_t up_len, up_pos, up_crc;
static bool up_active;

static uint32_t crc_update(uint32_t crc, const uint8_t *p, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) {
        crc ^= p[i];
        for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & -(crc & 1));
    }
    return crc;
}

static uint32_t rd32(const uint8_t *p) { return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24; }

/* 中身をたどる。cb が true を返したらそこで止める。形が壊れていれば -1、最後までたどれたら 0、止めたら 1 */
static int walk(const uint8_t *p, uint32_t len, bool (*cb)(const ui_file_t *, void *), void *arg)
{
    uint32_t i = 0;
    while (i < len) {
        ui_file_t f;
        if (i + 1 > len) return -1;
        f.plen = p[i++]; f.path = (const char *)p + i; i += f.plen;
        if (i + 1 > len) return -1;
        f.mlen = p[i++]; f.mime = (const char *)p + i; i += f.mlen;
        if (i + 5 > len) return -1;
        f.gzip = p[i++];
        f.len = rd32(p + i); i += 4;
        if (f.len > len - i) return -1;
        f.data = p + i; i += f.len;
        if (f.plen == 0) return -1;
        if (cb && cb(&f, arg)) return 1;
    }
    return i == len ? 0 : -1;
}

typedef struct { const char *path; ui_file_t *out; } find_t;
static bool match(const ui_file_t *f, void *arg)
{
    find_t *q = (find_t *)arg;
    if ((int)strlen(q->path) == f->plen && memcmp(q->path, f->path, f->plen) == 0) { *q->out = *f; return true; }
    return false;
}

void ui_check(void)
{
    const uint8_t *b = plat_ui_base();
    g_ui_valid = false;
    g_ui_len = 0;
    if (memcmp(b, MAGIC, 8) != 0) return;
    uint32_t len = rd32(b + 8), crc = rd32(b + 12);
    if (len == 0 || len > UI_MAX) return;
    if (~crc_update(0xFFFFFFFFu, b + HDR, len) != crc) return;
    ui_file_t f;
    find_t q = { "index.html", &f };
    if (walk(b + HDR, len, match, &q) != 1) return;
    g_ui_valid = true;
    g_ui_len = len;
}

bool ui_find(const char *path, ui_file_t *out)
{
    while (*path == '/') path++;
    if (g_ui_valid) {
        find_t q = { path, out };
        return walk(plat_ui_base() + HDR, g_ui_len, match, &q) == 1;
    }
    for (int i = 0; i < g_nassets; i++) {
        const asset_t *a = &g_assets[i];
        if (strcmp(a->path, path) == 0) {
            out->path = a->path; out->plen = (int)strlen(a->path);
            out->mime = a->mime; out->mlen = (int)strlen(a->mime);
            out->data = a->data; out->len = a->len; out->gzip = a->gzip;
            return true;
        }
    }
    return false;
}

bool ui_upload_begin(uint32_t len)
{
    if (len == 0 || len > UI_MAX) return false;
    g_ui_valid = false;          /* 消しているあいだは内蔵の画面を出す */
    plat_ui_erase();
    up_len = len; up_pos = 0; up_crc = 0xFFFFFFFFu; up_active = true;
    return true;
}

void ui_upload_data(const uint8_t *d, uint32_t n)
{
    if (!up_active) return;
    if (n > up_len - up_pos) n = up_len - up_pos;
    plat_ui_write(HDR + up_pos, d, n);
    up_crc = crc_update(up_crc, d, n);
    up_pos += n;
}

bool ui_upload_end(void)
{
    if (!up_active) return false;
    up_active = false;
    if (up_pos != up_len) return false;
    const uint8_t *b = plat_ui_base();
    ui_file_t f;
    find_t q = { "index.html", &f };
    if (walk(b + HDR, up_len, match, &q) != 1) { ui_reset(); return false; }
    uint32_t crc = ~up_crc;
    uint8_t hdr[HDR];
    memcpy(hdr, MAGIC, 8);
    for (int i = 0; i < 4; i++) { hdr[8 + i] = up_len >> (8 * i); hdr[12 + i] = crc >> (8 * i); }
    plat_ui_write(0, hdr, HDR);
    ui_check();
    return g_ui_valid;
}

void ui_reset(void)
{
    up_active = false;
    g_ui_valid = false;
    plat_ui_erase();
}
