#include "settings.h"
#include <string.h>
#include <stddef.h>

#define IP4(a,b,c,d) ((uint32_t)(a) | (uint32_t)(b) << 8 | (uint32_t)(c) << 16 | (uint32_t)(d) << 24)

void settings_reset_ip_pin(settings_t *s)
{
    s->dhcp = 0;
    s->ip = IP4(192, 168, 1, 223);
    s->mask = IP4(255, 255, 255, 0);
    s->gw = IP4(0, 0, 0, 0);
    memset(s->pin, 0, sizeof(s->pin));
    strcpy(s->pin, "1234");
}

void settings_default(settings_t *s)
{
    memset(s, 0, sizeof(*s));
    s->magic = SETTINGS_MAGIC;
    settings_reset_ip_pin(s);
    s->universe = 0;
    strcpy(s->name, "ODE-DIY");
}

uint32_t crc32_buf(const void *buf, unsigned len)
{
    const uint8_t *p = (const uint8_t *)buf;
    uint32_t crc = 0xFFFFFFFFu;
    for (unsigned i = 0; i < len; i++) {
        crc ^= p[i];
        for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & -(crc & 1));
    }
    return ~crc;
}

uint32_t settings_crc(const settings_t *s) { return crc32_buf(s, offsetof(settings_t, crc)); }

uint16_t settings_sacn_universe(const settings_t *s) { return s->sacn_universe ? s->sacn_universe : 1; }

bool settings_allowed(const settings_t *s, uint32_t ip)
{
    if (!s->allow_on) return true;
    for (int i = 0; i < ALLOW_MAX; i++) if (s->allow[i] && s->allow[i] == ip) return true;
    return false;
}

_Static_assert(sizeof(settings_t) == 128, "settings_t は 128 バイト");
_Static_assert(offsetof(settings_t, sacn_universe) == 58, "v1 と同じ並び");
