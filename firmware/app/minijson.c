#include "minijson.h"
#include <string.h>

/* トップレベル（深さ 1）のキーを探し、値の先頭位置を返す。無ければ -1 */
static int find_value(const char *s, int len, const char *key)
{
    int depth = 0, klen = (int)strlen(key);
    for (int i = 0; i < len; i++) {
        char ch = s[i];
        if (ch == '"') {
            int start = i + 1, j = start;
            while (j < len && s[j] != '"') { if (s[j] == '\\') j++; j++; }
            if (j >= len) return -1;
            if (depth == 1) {
                int k = j + 1;
                while (k < len && (s[k] == ' ' || s[k] == '\t' || s[k] == '\r' || s[k] == '\n')) k++;
                if (k < len && s[k] == ':') {
                    if (j - start == klen && memcmp(s + start, key, klen) == 0) {
                        k++;
                        while (k < len && (s[k] == ' ' || s[k] == '\t' || s[k] == '\r' || s[k] == '\n')) k++;
                        return k;
                    }
                }
            }
            i = j;
        } else if (ch == '{' || ch == '[') depth++;
        else if (ch == '}' || ch == ']') depth--;
    }
    return -1;
}

int mj_get_str(const char *s, int len, const char *key, char *out, int outsize)
{
    int i = find_value(s, len, key);
    if (i < 0 || i >= len || s[i] != '"') return 0;
    int o = 0;
    for (i++; i < len && s[i] != '"'; i++) {
        char c = s[i];
        if (c == '\\' && i + 1 < len) {
            c = s[++i];
            if (c == 'n') c = '\n'; else if (c == 't') c = '\t'; else if (c == 'u') return 0; /* \u は扱わない */
        }
        if (o >= outsize - 1) return 0;
        out[o++] = c;
    }
    if (i >= len) return 0;
    out[o] = 0;
    return 1;
}

int mj_get_bool(const char *s, int len, const char *key)
{
    int i = find_value(s, len, key);
    if (i < 0) return -1;
    if (len - i >= 4 && !memcmp(s + i, "true", 4)) return 1;
    if (len - i >= 5 && !memcmp(s + i, "false", 5)) return 0;
    return -1;
}

int mj_utf8_len(const unsigned char *s)
{
    unsigned c = s[0];
    if (c < 0x80) return 1;
    int n; unsigned min;
    if (c >= 0xC2 && c <= 0xDF) { n = 2; min = 0x80; }
    else if ((c & 0xF0) == 0xE0) { n = 3; min = 0x800; }
    else if (c >= 0xF0 && c <= 0xF4) { n = 4; min = 0x10000; }
    else return 0;
    unsigned cp = c & (0x7F >> n);
    for (int i = 1; i < n; i++) {
        if ((s[i] & 0xC0) != 0x80) return 0;   /* 文字の途中で終わる・続きのバイトでない */
        cp = (cp << 6) | (s[i] & 0x3F);
    }
    if (cp < min || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) return 0;
    return n;
}

int mj_utf8_ok(const char *s)
{
    const unsigned char *p = (const unsigned char *)s;
    while (*p) { int n = mj_utf8_len(p); if (!n) return 0; p += n; }
    return 1;
}

int mj_escape(const char *s, char *out, int outsize)
{
    static const char hx[] = "0123456789abcdef";
    const unsigned char *p = (const unsigned char *)s;
    int n = 0;
    if (outsize <= 0) return 0;
    while (*p) {
        unsigned char c = *p;
        char tmp[7]; int k = 0, adv = 1;
        if (c == '"' || c == '\\') { tmp[k++] = '\\'; tmp[k++] = (char)c; }
        else if (c < 0x20) { tmp[k++] = '\\'; tmp[k++] = 'u'; tmp[k++] = '0'; tmp[k++] = '0'; tmp[k++] = hx[c >> 4]; tmp[k++] = hx[c & 15]; }
        else if (c < 0x80) tmp[k++] = (char)c;
        else {
            int u = mj_utf8_len(p);
            if (u) { for (int i = 0; i < u; i++) tmp[k++] = (char)p[i]; adv = u; }
            else tmp[k++] = '?';   /* 壊れたバイトは 1 バイトずつ ? に（WebSocket のテキストは UTF-8 でないと切られる） */
        }
        if (n + k >= outsize) break;
        for (int i = 0; i < k; i++) out[n++] = tmp[i];
        p += adv;
    }
    out[n] = 0;
    return n;
}
