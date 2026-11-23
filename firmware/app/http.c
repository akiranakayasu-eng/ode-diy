/* HTTP（miseru の画面、/api/dmx、/setup）と WebSocket（/ws）。lwIP の raw TCP API で書いた小さなサーバ。
 * 仕様: docs/websocket-spec.md */
#include "app.h"
#include "assets.h"
#include "minijson.h"
#include "sha1.h"
#include "setup_page.h"
#include "lwip/tcp.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <stddef.h>
#include <strings.h>

#ifndef APP_CCM
#define APP_CCM
#endif

#define HTTP_SLOTS 8
#define REQ_MAX 1536
#define WS_MAX 600

typedef enum { HC_FREE = 0, HC_REQ, HC_SEND, HC_WS, HC_CLOSING, HC_UPLOAD } hc_mode_t;

typedef struct {
    hc_mode_t mode;
    struct tcp_pcb *pcb;
    /* HTTP */
    int slot;              /* 要求バッファの番号（HC_REQ のあいだ） */
    const uint8_t *tx;     /* 送り残し（フラッシュの中の画面） */
    uint32_t txlen;
    uint8_t close_after;   /* 送り終えたら閉じる */
    uint8_t reboot_after;  /* 送り終えたら再起動（設定の保存） */
    uint32_t up_left;      /* 画面のアップロードの残りバイト数 */
    const char *up_err;    /* NULL 以外なら本文を読み捨て、最後にこの JSON で断る */
    /* WebSocket */
    int conn;              /* box_core の接続番号 */
    uint8_t hdr[14];
    uint8_t hdrlen, hdrneed;
    uint8_t opcode, msgop, fin;
    uint8_t mask[4];
    uint32_t paylen, paypos;
    uint16_t msglen;
    uint8_t msg[WS_MAX];
} hconn_t;

#define MAX_HCONN (APP_MAX_CLIENTS + HTTP_SLOTS + 2)
static APP_CCM hconn_t hc[MAX_HCONN];
static APP_CCM char reqbuf[HTTP_SLOTS][REQ_MAX + 1];
static int reqlen[HTTP_SLOTS];
static uint8_t slot_used[HTTP_SLOTS];
static struct tcp_pcb *listen_pcb;
static uint32_t last_status_ms;
static uint8_t pending_reboot;
static uint32_t reboot_at;

static void hc_free(hconn_t *h);

/* ------------------------------------------------------------ 送信 */

static err_t write_copy(hconn_t *h, const void *data, u16_t len)
{
    if (!h->pcb) return ERR_CONN;
    if (tcp_sndbuf(h->pcb) < len || tcp_sndqueuelen(h->pcb) + 4 > TCP_SND_QUEUELEN) return ERR_MEM;
    err_t e = tcp_write(h->pcb, data, len, TCP_WRITE_FLAG_COPY);
    if (e == ERR_OK) tcp_output(h->pcb);
    return e;
}

static void pump_file(hconn_t *h)
{
    while (h->txlen > 0 && h->pcb) {
        u16_t room = tcp_sndbuf(h->pcb);
        if (room == 0 || tcp_sndqueuelen(h->pcb) + 4 > TCP_SND_QUEUELEN) break;
        u16_t n = h->txlen > room ? room : (u16_t)h->txlen;
        if (n > TCP_MSS * 2) n = TCP_MSS * 2;
        u8_t flags = h->txlen > n ? TCP_WRITE_FLAG_MORE : 0;
        if (tcp_write(h->pcb, h->tx, n, flags) != ERR_OK) break;   /* フラッシュの中身をそのまま渡す（コピーしない） */
        h->tx += n;
        h->txlen -= n;
    }
    if (h->pcb) tcp_output(h->pcb);
}

static void close_conn(hconn_t *h)
{
    struct tcp_pcb *pcb = h->pcb;
    if (h->conn >= 0) box_close(&g_box, h->conn);
    hc_free(h);
    if (pcb) {
        tcp_arg(pcb, NULL);
        tcp_recv(pcb, NULL);
        tcp_sent(pcb, NULL);
        tcp_err(pcb, NULL);
        tcp_poll(pcb, NULL, 0);
        tcp_close(pcb);   /* 失敗（メモリ不足）しても相手の切断か時間切れで消える */
    }
}

static void maybe_finish(hconn_t *h)
{
    if (h->mode == HC_SEND && h->txlen == 0 && h->close_after) {
        if (h->reboot_after) { pending_reboot = h->reboot_after; reboot_at = plat_now_ms() + 500; }
        close_conn(h);
    }
}

/* ------------------------------------------------------------ WebSocket の送信 */

static void ws_send(hconn_t *h, uint8_t op, const void *data, u16_t len)
{
    /* ヘッダと中身を 1 回の tcp_write で渡す（片方だけ入るとフレームが壊れるため）。入らなければ捨てる */
    uint8_t f[4 + 200];
    int hl;
    if (len > 200) return;
    f[0] = 0x80 | op;
    if (len < 126) { f[1] = len; hl = 2; }
    else { f[1] = 126; f[2] = len >> 8; f[3] = len & 0xff; hl = 4; }
    if (len) memcpy(f + hl, data, len);
    if (!h->pcb || tcp_sndbuf(h->pcb) < hl + len || tcp_sndqueuelen(h->pcb) + 2 > TCP_SND_QUEUELEN) return;
    if (tcp_write(h->pcb, f, hl + len, TCP_WRITE_FLAG_COPY) == ERR_OK) tcp_output(h->pcb);
}

static void ws_send_text(hconn_t *h, const char *s) { ws_send(h, 0x1, s, (u16_t)strlen(s)); }

static void ws_send_status(hconn_t *h)
{
    char buf[160];
    box_status_json(&g_box, h->conn, APP_MAX_CLIENTS, buf, sizeof(buf));
    ws_send_text(h, buf);
}

void ws_broadcast_status(void)
{
    for (int i = 0; i < MAX_HCONN; i++)
        if (hc[i].mode == HC_WS) ws_send_status(&hc[i]);
    last_status_ms = plat_now_ms();
}

static void ws_close_with(hconn_t *h, uint16_t code)
{
    uint8_t p[2] = { code >> 8, code & 0xff };
    ws_send(h, 0x8, p, 2);
    h->mode = HC_CLOSING;
    close_conn(h);
}

/* ------------------------------------------------------------ WebSocket の受信 */

static void ws_on_message(hconn_t *h, uint8_t op, const uint8_t *data, int len)
{
    uint32_t now = plat_now_ms();
    if (op == 0x2) {
        box_binary(&g_box, h->conn, data, len, now);
        return;
    }
    if (op != 0x1) return;
    char t[20], id[BOX_ID_MAX + 1], pin[24];
    const char *js = (const char *)data;
    if (!mj_get_str(js, len, "t", t, sizeof(t))) return;
    int has_id = mj_get_str(js, len, "id", id, sizeof(id));
    int has_pin = mj_get_str(js, len, "pin", pin, sizeof(pin));
    int on = mj_get_bool(js, len, "on");
    uint32_t before = g_box.version;
    int r = box_message(&g_box, h->conn, t, has_id ? id : NULL, has_pin ? pin : NULL, on, now);
    if (r & REPLY_DENIED_BUSY) ws_send_text(h, "{\"t\":\"denied\",\"reason\":\"busy\"}");
    if (r & REPLY_DENIED_NOTALLOWED) ws_send_text(h, "{\"t\":\"denied\",\"reason\":\"not_allowed\"}");
    if (r & REPLY_DENIED_NOHELLO) ws_send_text(h, "{\"t\":\"denied\",\"reason\":\"no_hello\"}");
    if (r & REPLY_PIN_OK) ws_send_text(h, "{\"t\":\"pin\",\"ok\":true}");
    if (r & REPLY_PIN_NG) ws_send_text(h, "{\"t\":\"pin\",\"ok\":false}");
    if (r & REPLY_STATUS) ws_send_status(h);
    if (g_box.version != before) ws_broadcast_status();
}

/* 受け取ったバイト列を 1 バイトずつ読む。閉じたら 0 を返す */
static int ws_feed(hconn_t *h, const uint8_t *p, int n)
{
    for (int i = 0; i < n; i++) {
        uint8_t b = p[i];
        if (h->hdrlen < h->hdrneed) {
            h->hdr[h->hdrlen++] = b;
            if (h->hdrlen == 2) {
                uint8_t l = h->hdr[1] & 0x7f;
                h->hdrneed = 2 + (l == 126 ? 2 : l == 127 ? 8 : 0) + ((h->hdr[1] & 0x80) ? 4 : 0);
            }
            if (h->hdrlen == h->hdrneed && h->hdrlen >= 2) {
                h->fin = h->hdr[0] & 0x80;
                h->opcode = h->hdr[0] & 0x0f;
                uint8_t l = h->hdr[1] & 0x7f;
                int k = 2;
                if (l == 126) { h->paylen = h->hdr[2] << 8 | h->hdr[3]; k = 4; }
                else if (l == 127) { h->paylen = (uint32_t)h->hdr[6] << 24 | (uint32_t)h->hdr[7] << 16 | h->hdr[8] << 8 | h->hdr[9]; k = 10; }
                else h->paylen = l;
                if (h->hdr[1] & 0x80) memcpy(h->mask, h->hdr + k, 4); else memset(h->mask, 0, 4);
                h->paypos = 0;
                if (h->opcode != 0x0 && h->opcode < 0x8) { h->msgop = h->opcode; h->msglen = 0; }
                if (h->paylen == 0) goto frame_done;
            }
            continue;
        }
        /* ペイロード */
        {
            uint8_t v = b ^ h->mask[h->paypos & 3];
            if (h->opcode < 0x8 && h->msglen < WS_MAX) {   /* 制御フレームの中身は使わない */
                h->msg[h->msglen++] = v;
            }
            h->paypos++;
            if (h->paypos < h->paylen) continue;
        }
    frame_done:
        if (h->opcode == 0x8) { ws_close_with(h, 1000); return 0; }
        if (h->opcode == 0x9) { ws_send(h, 0xA, NULL, 0); }
        else if (h->opcode < 0x8 && h->fin) { ws_on_message(h, h->msgop, h->msg, h->msglen); h->msglen = 0; }
        if (h->mode != HC_WS) return 0;
        h->hdrlen = 0; h->hdrneed = 2;
    }
    return 1;
}

/* ------------------------------------------------------------ HTTP */

static const char *hdr_find(const char *req, const char *name)
{
    size_t nl = strlen(name);
    for (const char *p = strstr(req, "\r\n"); p && p[2]; p = strstr(p + 2, "\r\n")) {
        const char *line = p + 2;
        if (line[0] == '\r') break;
        if (strncasecmp(line, name, nl) == 0 && line[nl] == ':') {
            line += nl + 1;
            while (*line == ' ') line++;
            return line;
        }
    }
    return NULL;
}

static void send_simple(hconn_t *h, const char *status, const char *type, const char *body, int len, int extra_close)
{
    char head[256];
    int hl = snprintf(head, sizeof(head),
                      "HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n",
                      status, type, len);
    h->mode = HC_SEND;
    h->close_after = 1;
    h->reboot_after = extra_close;
    if (write_copy(h, head, hl) != ERR_OK) { close_conn(h); return; }
    if (len > 0) {
        h->tx = (const uint8_t *)body;   /* body は送り終えるまで残っている所（静的領域）に置くこと */
        h->txlen = len;
        pump_file(h);
    }
    maybe_finish(h);
}

static void send_file(hconn_t *h, const ui_file_t *a)
{
    char head[320];
    int is_index = a->plen == 10 && memcmp(a->path, "index.html", 10) == 0;
    int hl = snprintf(head, sizeof(head),
                      "HTTP/1.1 200 OK\r\nContent-Type: %.*s\r\nContent-Length: %lu\r\n%sCache-Control: %s\r\nConnection: close\r\n\r\n",
                      a->mlen, a->mime, (unsigned long)a->len, a->gzip ? "Content-Encoding: gzip\r\n" : "",
                      is_index ? "no-cache" : "max-age=86400");
    h->mode = HC_SEND;
    h->close_after = 1;
    if (write_copy(h, head, hl) != ERR_OK) { close_conn(h); return; }
    h->tx = a->data;
    h->txlen = a->len;
    pump_file(h);
    maybe_finish(h);
}

/* GET /api/dmx */
static char dmx_json[2700];
static void send_api_dmx(hconn_t *h)
{
    char holder[64];
    box_holder_json(&g_box, -1, holder, sizeof(holder));
    int n = snprintf(dmx_json, sizeof(dmx_json), "{\"holder\":%s,\"show_mode\":%s,\"max_clients\":%d,\"output\":[",
                     holder, g_box.show_mode ? "true" : "false", APP_MAX_CLIENTS);
    for (int i = 0; i < DMX_SLOTS; i++) n += snprintf(dmx_json + n, sizeof(dmx_json) - n, i ? ",%u" : "%u", g_box.output[i]);
    n += snprintf(dmx_json + n, sizeof(dmx_json) - n, "]}");
    /* dmx_json は次の要求で上書きされるので、ここでコピーして送る */
    char head[200];
    int hl = snprintf(head, sizeof(head), "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n", n);
    h->mode = HC_SEND;
    h->close_after = 1;
    if (write_copy(h, head, hl) != ERR_OK) { close_conn(h); return; }
    if (write_copy(h, dmx_json, (u16_t)n) != ERR_OK) { close_conn(h); return; }
    maybe_finish(h);
}

/* GET /api/settings（PIN は返さない） */
static char settings_json[900];
static int ipstr(char *o, int n, uint32_t a) { const uint8_t *p = (const uint8_t *)&a; return snprintf(o, n, "%u.%u.%u.%u", p[0], p[1], p[2], p[3]); }
static void send_api_settings(hconn_t *h)
{
    char ip[16], m[16], g[16], allow[ALLOW_MAX * 17 + 2];
    ipstr(ip, sizeof ip, g_settings.ip); ipstr(m, sizeof m, g_settings.mask); ipstr(g, sizeof g, g_settings.gw);
    int an = 0;
    for (int i = 0; i < ALLOW_MAX; i++) if (g_settings.allow[i]) {
        if (an) allow[an++] = ',';
        an += ipstr(allow + an, sizeof(allow) - an, g_settings.allow[i]);
    }
    allow[an] = 0;
    const uint8_t *mac = plat_mac();
    int n = snprintf(settings_json, sizeof(settings_json),
                     "{\"dhcp\":%s,\"ip\":\"%s\",\"mask\":\"%s\",\"gw\":\"%s\",\"universe\":%u,\"name\":\"%s\","
                     "\"sacn\":%s,\"sacn_universe\":%u,\"allow_on\":%s,\"allow\":\"%s\","
                     "\"ui\":\"%s\",\"ui_size\":%lu,\"ui_max\":%lu,\"ui_open\":%lu,"
                     "\"mac\":\"%02x:%02x:%02x:%02x:%02x:%02x\",\"max_clients\":%d,\"version\":\"%s\"}",
                     g_settings.dhcp ? "true" : "false", ip, m, g, g_settings.universe, g_settings.name,
                     g_settings.sacn_off ? "false" : "true", settings_sacn_universe(&g_settings), g_settings.allow_on ? "true" : "false", allow,
                     g_ui_valid ? "uploaded" : "builtin", (unsigned long)g_ui_len, (unsigned long)UI_MAX, (unsigned long)app_ui_window_left_s(),
                     mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], APP_MAX_CLIENTS, FW_VERSION_STR);
    send_simple(h, "200 OK", "application/json", settings_json, n, 0);
}

/* フォームの値（application/x-www-form-urlencoded）を 1 つ取り出す */
static int form_get(const char *body, const char *key, char *out, int size)
{
    size_t kl = strlen(key);
    const char *p = body;
    while (p && *p) {
        if (strncmp(p, key, kl) == 0 && p[kl] == '=') {
            p += kl + 1;
            int o = 0;
            while (*p && *p != '&' && o < size - 1) {
                char c = *p++;
                if (c == '+') c = ' ';
                else if (c == '%' && isxdigit((unsigned char)p[0]) && isxdigit((unsigned char)p[1])) {
                    char hx[3] = { p[0], p[1], 0 };
                    c = (char)strtol(hx, NULL, 16);
                    p += 2;
                }
                out[o++] = c;
            }
            out[o] = 0;
            return 1;
        }
        p = strchr(p, '&');
        if (p) p++;
    }
    return 0;
}

static int parse_ip(const char *s, uint32_t *out)
{
    unsigned a, b, c, d;
    char tail;
    if (sscanf(s, "%u.%u.%u.%u%c", &a, &b, &c, &d, &tail) != 4 || a > 255 || b > 255 || c > 255 || d > 255) return 0;
    *out = a | b << 8 | c << 16 | (uint32_t)d << 24;
    return 1;
}

static char post_reply[200];
static bool pin_ok(const char *pin) { return g_settings.pin[0] && strcmp(pin, g_settings.pin) == 0; }
static void send_json(hconn_t *h, const char *status, const char *json)
{
    int n = snprintf(post_reply, sizeof(post_reply), "%s", json);
    send_simple(h, status, "application/json", post_reply, n, 0);
}
#define ERR_BUTTON "{\"ok\":false,\"error\":\"button\"}"   /* 本体ボタンの長押しで開く窓が閉じている */
static void handle_post_settings(hconn_t *h, const char *body)
{
    char pin[24], v[40];
    if (!form_get(body, "pin", pin, sizeof(pin)) || !pin_ok(pin)) {
        int n = snprintf(post_reply, sizeof(post_reply), "{\"ok\":false,\"error\":\"pin\"}");
        send_simple(h, "403 Forbidden", "application/json", post_reply, n, 0);
        return;
    }
    settings_t s = g_settings;
    if (form_get(body, "dhcp", v, sizeof(v))) s.dhcp = (v[0] == '1');
    if (form_get(body, "ip", v, sizeof(v)) && v[0] && !parse_ip(v, &s.ip)) goto bad;
    if (form_get(body, "mask", v, sizeof(v)) && v[0] && !parse_ip(v, &s.mask)) goto bad;
    if (form_get(body, "gw", v, sizeof(v)) && v[0] && !parse_ip(v, &s.gw)) goto bad;
    if (form_get(body, "universe", v, sizeof(v)) && v[0]) {
        long u = strtol(v, NULL, 10);
        if (u < 0 || u > 0x7fff) goto bad;
        s.universe = (uint16_t)u;
    }
    if (form_get(body, "name", v, sizeof(v)) && v[0]) { memset(s.name, 0, sizeof(s.name)); strncpy(s.name, v, sizeof(s.name) - 1); }
    if (form_get(body, "sacn", v, sizeof(v))) s.sacn_off = (v[0] != '1');
    if (form_get(body, "sacn_universe", v, sizeof(v)) && v[0]) {
        long u = strtol(v, NULL, 10);
        if (u < 1 || u > 63999) goto bad;
        s.sacn_universe = (uint16_t)u;
    }
    if (form_get(body, "allow_on", v, sizeof(v))) s.allow_on = (v[0] == '1');
    {
        char list[ALLOW_MAX * 17 + 8];
        if (form_get(body, "allow", list, sizeof(list))) {
            uint32_t tmp[ALLOW_MAX] = {0};
            int k = 0;
            for (char *t = strtok(list, ", \r\n"); t; t = strtok(NULL, ", \r\n")) {
                if (k >= ALLOW_MAX || !parse_ip(t, &tmp[k])) goto bad;
                k++;
            }
            if (s.allow_on && k == 0) goto bad;   /* 空の許可リストを入にするとだれも使えなくなる */
            memcpy(s.allow, tmp, sizeof(tmp));
        }
    }
    if (s.allow_on && !s.allow[0]) goto bad;
    if (form_get(body, "newpin", v, sizeof(v)) && v[0]) {
        if (strlen(v) >= sizeof(s.pin)) goto bad;
        memset(s.pin, 0, sizeof(s.pin));
        strcpy(s.pin, v);
    }
    {
        /* PIN だけが変わったときは再起動しない（v0.3.0。/setup は PIN の変更だけになった） */
        settings_t a = s, b = g_settings;
        memset(a.pin, 0, sizeof(a.pin)); memset(b.pin, 0, sizeof(b.pin));
        bool only_pin = memcmp(&a, &b, sizeof(a)) == 0;
        plat_settings_save(&s);
        g_settings = s;
        if (only_pin) {
            memset(g_box.pin, 0, sizeof(g_box.pin));
            strncpy(g_box.pin, g_settings.pin, sizeof(g_box.pin) - 1);
            send_json(h, "200 OK", "{\"ok\":true,\"reboot\":false}");
        } else {
            int n = snprintf(post_reply, sizeof(post_reply), "{\"ok\":true,\"reboot\":true}");
            send_simple(h, "200 OK", "application/json", post_reply, n, 1);
        }
    }
    return;
bad:
    {
        int n = snprintf(post_reply, sizeof(post_reply), "{\"ok\":false,\"error\":\"value\"}");
        send_simple(h, "400 Bad Request", "application/json", post_reply, n, 0);
    }
}

static void ws_upgrade(hconn_t *h, const char *req)
{
    const char *key = hdr_find(req, "Sec-WebSocket-Key");
    if (!key) { send_simple(h, "400 Bad Request", "text/plain", "", 0, 0); return; }
    char k[80];
    int kl = 0;
    while (key[kl] && key[kl] != '\r' && kl < 60) { k[kl] = key[kl]; kl++; }
    strcpy(k + kl, "258EAFA5-E914-47DA-95CA-C5AB0DC85B11");
    uint8_t dig[20];
    sha1((const uint8_t *)k, strlen(k), dig);
    char acc[40];
    base64_encode(dig, 20, acc, sizeof(acc));
    char resp[200];
    int n = snprintf(resp, sizeof(resp),
                     "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n", acc);
    if (write_copy(h, resp, n) != ERR_OK) { close_conn(h); return; }
    int conn = box_open(&g_box, ip_2_ip4(&h->pcb->remote_ip)->addr);
    h->mode = HC_WS;
    h->conn = conn;
    h->hdrlen = 0; h->hdrneed = 2; h->msglen = 0;
    if (conn < 0) {
        /* 上限を超えた接続はいったん受けてから 1013 で閉じる（仕様 v1） */
        h->conn = -1;
        ws_close_with(h, 1013);
        return;
    }
    ws_send_status(h);
}

static void handle_request(hconn_t *h, char *req, int len)
{
    (void)len;
    char method[8] = {0}, path[128] = {0};
    if (sscanf(req, "%7s %127s", method, path) != 2) { close_conn(h); return; }
    char query[64] = {0};
    char *q = strchr(path, '?');
    if (q) { strncpy(query, q + 1, sizeof(query) - 1); *q = 0; }

    if (strcmp(method, "GET") == 0) {
        if (strcmp(path, "/ws") == 0) {
            const char *up = hdr_find(req, "Upgrade");
            if (up && strncasecmp(up, "websocket", 9) == 0) { ws_upgrade(h, req); return; }
        }
        if (strcmp(path, "/api/dmx") == 0) { send_api_dmx(h); return; }
        if (strcmp(path, "/api/settings") == 0) { send_api_settings(h); return; }
        if (strcmp(path, "/setup") == 0) { send_simple(h, "200 OK", "text/html; charset=utf-8", SETUP_PAGE, (int)strlen(SETUP_PAGE), 0); return; }
        ui_file_t f;
        if (ui_find(path, &f) || ui_find("index.html", &f)) send_file(h, &f);   /* 知らないパスには index.html（SPA の fallback） */
        else send_simple(h, "404 Not Found", "text/plain", "no ui", 5, 0);
        return;
    }
    if (strcmp(method, "POST") == 0 && strcmp(path, "/api/dfu") == 0) {
        /* ファーム更新モード: 返事を送り終えたら USB DFU（ROM のブートローダ）で再起動する */
        /* v0.3.0: 本体ボタンの長押しで開く窓の間だけ、PIN も要る */
        char pin[24];
        if (!app_ui_window_left_s()) { send_json(h, "403 Forbidden", ERR_BUTTON); return; }
        if (!form_get(query, "pin", pin, sizeof(pin)) || !pin_ok(pin)) { send_json(h, "403 Forbidden", "{\"ok\":false,\"error\":\"pin\"}"); return; }
        int n = snprintf(post_reply, sizeof(post_reply), "{\"ok\":true,\"mode\":\"dfu\"}");
        send_simple(h, "200 OK", "application/json", post_reply, n, 2);
        return;
    }
    if (strcmp(method, "POST") == 0 && strcmp(path, "/api/ui/reset") == 0) {
        /* v0.3.0: PIN は要らない。本体ボタンの長押しで開く窓の間だけ */
        if (!app_ui_window_left_s()) { send_json(h, "403 Forbidden", ERR_BUTTON); return; }
        ui_reset();
        send_json(h, "200 OK", "{\"ok\":true,\"ui\":\"builtin\"}");
        return;
    }
    if (strcmp(method, "POST") == 0 && strcmp(path, "/api/settings") == 0) {
        char *body = strstr(req, "\r\n\r\n");
        handle_post_settings(h, body ? body + 4 : "");
        return;
    }
    send_simple(h, "405 Method Not Allowed", "text/plain", "", 0, 0);
}

/* 要求がそろったか（ヘッダの終わりと Content-Length 分の本文） */
static int request_complete(const char *req, int len)
{
    const char *end = strstr(req, "\r\n\r\n");
    if (!end) return 0;
    const char *cl = hdr_find(req, "Content-Length");
    int need = cl ? atoi(cl) : 0;
    return (int)(len - (end + 4 - req)) >= need;
}

/* ------------------------------------------------------------ 画面のアップロード（POST /api/ui、本文は ui.c の形）
 * v0.3.0: PIN は要らない（?pin= が付いていても見ない）。本体ボタンの長押しで開く窓（10 分）の間だけ受ける */

static void upload_feed(hconn_t *h, const uint8_t *d, uint32_t n)
{
    if (n > h->up_left) n = h->up_left;
    if (!h->up_err) ui_upload_data(d, n);
    h->up_left -= n;
    if (h->up_left == 0) {
        if (h->up_err) { h->mode = HC_SEND; send_json(h, "403 Forbidden", h->up_err); return; }
        bool ok = ui_upload_end();
        h->mode = HC_SEND;
        if (ok) {
            char j[80];
            snprintf(j, sizeof(j), "{\"ok\":true,\"ui\":\"uploaded\",\"size\":%lu}", (unsigned long)g_ui_len);
            send_json(h, "200 OK", j);
        } else {
            send_json(h, "400 Bad Request", "{\"ok\":false,\"error\":\"bundle\"}");
        }
    }
}

/* ヘッダがそろい、それが POST /api/ui なら、アップロードを始めて true */
static bool upload_start(hconn_t *h)
{
    int s = h->slot;
    char *req = reqbuf[s];
    if (strncmp(req, "POST /api/ui?", 13) != 0 && strncmp(req, "POST /api/ui ", 13) != 0) return false;
    char *end = strstr(req, "\r\n\r\n");
    if (!end) return false;
    const char *cl = hdr_find(req, "Content-Length");
    long len = cl ? atol(cl) : 0;
    uint8_t *body = (uint8_t *)end + 4;
    int have = reqlen[s] - (int)(body - (uint8_t *)req);
    slot_used[s] = 0;
    h->slot = -1;
    h->mode = HC_SEND;
    if (len <= 0 || len > 4L * 1024 * 1024) { send_json(h, "413 Payload Too Large", "{\"ok\":false,\"error\":\"size\"}"); return true; }
    h->up_err = NULL;
    if (!app_ui_window_left_s()) h->up_err = ERR_BUTTON;
    else if ((uint32_t)len > UI_MAX) h->up_err = "{\"ok\":false,\"error\":\"size\"}";
    else ui_upload_begin((uint32_t)len);    /* 消去に 1〜2 秒かかる */
    h->mode = HC_UPLOAD;
    h->up_left = (uint32_t)len;
    if (have > 0) upload_feed(h, body, (uint32_t)have);
    return true;
}

/* ------------------------------------------------------------ lwIP のコールバック */

static void hc_free(hconn_t *h)
{
    if (h->mode == HC_REQ && h->slot >= 0) slot_used[h->slot] = 0;
    h->mode = HC_FREE;
    h->pcb = NULL;
    h->slot = -1;
    h->conn = -1;
}

static err_t on_recv(void *arg, struct tcp_pcb *pcb, struct pbuf *p, err_t err)
{
    hconn_t *h = (hconn_t *)arg;
    if (!h) { if (p) pbuf_free(p); return ERR_OK; }
    if (!p || err != ERR_OK) {           /* 相手が閉じた */
        if (p) pbuf_free(p);
        close_conn(h);
        return ERR_OK;
    }
    tcp_recved(pcb, p->tot_len);
    if (h->mode == HC_REQ) {
        int s = h->slot;
        for (struct pbuf *q = p; q && h->mode != HC_FREE; q = q->next) {
            const uint8_t *d = (const uint8_t *)q->payload;
            int n = q->len;
            while (n > 0 && h->mode == HC_REQ) {
                int room = REQ_MAX - reqlen[s];
                int c = n < room ? n : room;
                memcpy(reqbuf[s] + reqlen[s], d, c);
                reqlen[s] += c;
                reqbuf[s][reqlen[s]] = 0;
                d += c; n -= c;
                if (upload_start(h)) break;     /* 画面のアップロード: ここから先は本文として書く */
                if (reqlen[s] >= REQ_MAX) break;
            }
            if (h->mode == HC_UPLOAD && n > 0) upload_feed(h, d, n);
        }
        pbuf_free(p);
        if (h->mode == HC_REQ) {
            if (request_complete(reqbuf[s], reqlen[s])) {
                slot_used[s] = 0;
                h->slot = -1;
                h->mode = HC_SEND;
                handle_request(h, reqbuf[s], reqlen[s]);
            } else if (reqlen[s] >= REQ_MAX) {
                close_conn(h);
            }
        }
        return ERR_OK;
    }
    if (h->mode == HC_UPLOAD) {
        for (struct pbuf *q = p; q && h->mode == HC_UPLOAD; q = q->next) upload_feed(h, (const uint8_t *)q->payload, q->len);
        pbuf_free(p);
        return ERR_OK;
    }
    if (h->mode == HC_WS) {
        for (struct pbuf *q = p; q; q = q->next)
            if (!ws_feed(h, (const uint8_t *)q->payload, q->len)) break;
    }
    pbuf_free(p);
    return ERR_OK;
}

static err_t on_sent(void *arg, struct tcp_pcb *pcb, u16_t len)
{
    (void)pcb; (void)len;
    hconn_t *h = (hconn_t *)arg;
    if (!h) return ERR_OK;
    if (h->mode == HC_SEND) { pump_file(h); maybe_finish(h); }
    return ERR_OK;
}

static void on_err(void *arg, err_t err)
{
    (void)err;
    hconn_t *h = (hconn_t *)arg;
    if (!h) return;
    if (h->conn >= 0) box_close(&g_box, h->conn);
    hc_free(h);   /* pcb はもう lwIP が解放している */
}

static err_t on_poll(void *arg, struct tcp_pcb *pcb)
{
    hconn_t *h = (hconn_t *)arg;
    if (!h) { tcp_abort(pcb); return ERR_ABRT; }
    if (h->mode == HC_SEND) { pump_file(h); maybe_finish(h); }
    return ERR_OK;
}

static err_t on_accept(void *arg, struct tcp_pcb *pcb, err_t err)
{
    (void)arg;
    if (err != ERR_OK || !pcb) return ERR_VAL;
    hconn_t *h = NULL;
    int s = -1;
    for (int i = 0; i < HTTP_SLOTS; i++) if (!slot_used[i]) { s = i; break; }
    for (int i = 0; i < MAX_HCONN && s >= 0; i++) if (hc[i].mode == HC_FREE) { h = &hc[i]; break; }
    if (!h) { tcp_abort(pcb); return ERR_ABRT; }
    memset(h, 0, offsetof(hconn_t, msg));
    h->mode = HC_REQ;
    h->pcb = pcb;
    h->slot = s;
    h->conn = -1;
    slot_used[s] = 1;
    reqlen[s] = 0;
    tcp_setprio(pcb, TCP_PRIO_MIN);
    tcp_nagle_disable(pcb);
    tcp_arg(pcb, h);
    tcp_recv(pcb, on_recv);
    tcp_sent(pcb, on_sent);
    tcp_err(pcb, on_err);
    tcp_poll(pcb, on_poll, 2);
    return ERR_OK;
}

void http_init(void)
{
    for (int i = 0; i < MAX_HCONN; i++) { hc[i].mode = HC_FREE; hc[i].slot = -1; hc[i].conn = -1; }
    struct tcp_pcb *pcb = tcp_new();
    tcp_bind(pcb, IP_ADDR_ANY, HTTP_PORT);
    listen_pcb = tcp_listen_with_backlog(pcb, 8);
    tcp_accept(listen_pcb, on_accept);
}

void http_poll(void)
{
    uint32_t now = plat_now_ms();
    if ((uint32_t)(now - last_status_ms) >= 1000) ws_broadcast_status();
    if (pending_reboot && (int32_t)(now - reboot_at) >= 0) {
        if (pending_reboot == 2) plat_enter_dfu(); else plat_reboot();
    }
}
