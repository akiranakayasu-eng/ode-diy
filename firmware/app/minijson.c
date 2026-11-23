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
