/* WebSocket の握手（Sec-WebSocket-Accept）用の SHA-1 と Base64 */
#include "sha1.h"
#include <string.h>

#define ROL(v, n) (((v) << (n)) | ((v) >> (32 - (n))))

static void block(uint32_t h[5], const uint8_t *p)
{
    uint32_t w[80];
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4*i] << 24 | (uint32_t)p[4*i+1] << 16 | (uint32_t)p[4*i+2] << 8 | p[4*i+3];
    for (int i = 16; i < 80; i++) w[i] = ROL(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
    for (int i = 0; i < 80; i++) {
        uint32_t f, k;
        if (i < 20) { f = (b & c) | (~b & d); k = 0x5A827999; }
        else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
        else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
        else { f = b ^ c ^ d; k = 0xCA62C1D6; }
        uint32_t t = ROL(a, 5) + f + e + k + w[i];
        e = d; d = c; c = ROL(b, 30); b = a; a = t;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
}

void sha1(const uint8_t *data, size_t len, uint8_t out[20])
{
    uint32_t h[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};
    uint8_t buf[64];
    size_t i = 0;
    for (; i + 64 <= len; i += 64) block(h, data + i);
    size_t rem = len - i;
    memset(buf, 0, 64);
    memcpy(buf, data + i, rem);
    buf[rem] = 0x80;
    if (rem >= 56) { block(h, buf); memset(buf, 0, 64); }
    uint64_t bits = (uint64_t)len * 8;
    for (int j = 0; j < 8; j++) buf[63 - j] = (uint8_t)(bits >> (8 * j));
    block(h, buf);
    for (int j = 0; j < 5; j++) { out[4*j] = h[j] >> 24; out[4*j+1] = h[j] >> 16; out[4*j+2] = h[j] >> 8; out[4*j+3] = h[j]; }
}

int base64_encode(const uint8_t *in, int len, char *out, int outsize)
{
    static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    int o = 0;
    for (int i = 0; i < len; i += 3) {
        uint32_t v = (uint32_t)in[i] << 16 | (i + 1 < len ? (uint32_t)in[i+1] << 8 : 0) | (i + 2 < len ? in[i+2] : 0);
        if (o + 4 >= outsize) return -1;
        out[o++] = T[(v >> 18) & 63];
        out[o++] = T[(v >> 12) & 63];
        out[o++] = i + 1 < len ? T[(v >> 6) & 63] : '=';
        out[o++] = i + 2 < len ? T[v & 63] : '=';
    }
    out[o] = 0;
    return o;
}
