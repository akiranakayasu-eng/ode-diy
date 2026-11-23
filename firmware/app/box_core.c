#include "box_core.h"
#include <string.h>
#include <stdio.h>

static void release_lock(box_core_t *b)
{
    memset(b->output, 0, DMX_SLOTS);
    b->out_version++;
    if (b->owner != OWNER_NONE) {
        b->owner = OWNER_NONE;
        b->owner_id[0] = 0;
        b->owner_ip = 0;
        b->version++;
    }
}

void box_init(box_core_t *b, const char *pin, bool show_mode)
{
    memset(b, 0, sizeof(*b));
    b->timeout_ms = BOX_LOCK_TIMEOUT_MS;
    strncpy(b->pin, pin ? pin : "", sizeof(b->pin) - 1);
    b->show_mode = show_mode;
}

int box_open(box_core_t *b, uint32_t ip)
{
    for (int i = 0; i < BOX_MAX_CONN; i++) {
        if (!b->conns[i].used) {
            memset(&b->conns[i], 0, sizeof(b->conns[i]));
            b->conns[i].used = true;
            b->conns[i].ip = ip;
            b->nconns++;
            return i;
        }
    }
    return -1;
}

void box_close(box_core_t *b, int conn)
{
    /* ロックは外さない。同じ id で戻れば続けられ、戻らなければ時間切れで外れる */
    if (conn < 0 || conn >= BOX_MAX_CONN || !b->conns[conn].used) return;
    b->conns[conn].used = false;
    b->nconns--;
}

bool box_is_my_lock(const box_core_t *b, int conn)
{
    if (conn < 0 || conn >= BOX_MAX_CONN) return false;
    const box_conn_t *c = &b->conns[conn];
    return c->used && c->id[0] && b->owner == OWNER_WS && strcmp(b->owner_id, c->id) == 0;
}

static void take_ws(box_core_t *b, const char *id, uint32_t now)
{
    b->owner = OWNER_WS;
    strncpy(b->owner_id, id, BOX_ID_MAX);
    b->owner_id[BOX_ID_MAX] = 0;
    b->last_seen = now;
    b->version++;
}

void box_binary(box_core_t *b, int conn, const uint8_t *data, int len, uint32_t now)
{
    if (!box_is_my_lock(b, conn)) return;
    if (len < 2 || data[0] != 0x01) return;
    /* data[1] はポート番号。v0 は 0 だけ */
    int n = len - 2;
    if (n > DMX_SLOTS) n = DMX_SLOTS;
    memcpy(b->output, data + 2, n);
    if (n < DMX_SLOTS) memset(b->output + n, 0, DMX_SLOTS - n);
    b->out_version++;
    b->last_seen = now;
}

int box_message(box_core_t *b, int conn, const char *t, const char *id, const char *pin, int on, uint32_t now)
{
    if (conn < 0 || conn >= BOX_MAX_CONN || !b->conns[conn].used || !t) return REPLY_NONE;
    box_conn_t *c = &b->conns[conn];
    if (!strcmp(t, "hello")) {
        if (!id || !id[0] || strlen(id) > BOX_ID_MAX) return REPLY_NONE;
        strcpy(c->id, id);
        if (box_is_my_lock(b, conn)) b->last_seen = now;
        return REPLY_STATUS;
    }
    if (!strcmp(t, "claim")) {
        if (!c->id[0]) return REPLY_DENIED_NOHELLO;
        if (box_is_my_lock(b, conn)) { b->last_seen = now; return REPLY_NONE; }
        if (b->owner != OWNER_NONE) return REPLY_DENIED_BUSY;
        if (b->allowed && !b->allowed(c->ip)) return REPLY_DENIED_NOTALLOWED;
        take_ws(b, c->id, now);
        return REPLY_NONE;
    }
    if (!strcmp(t, "ping")) {
        if (box_is_my_lock(b, conn)) b->last_seen = now;
        return REPLY_NONE;
    }
    if (!strcmp(t, "release")) {
        if (box_is_my_lock(b, conn)) release_lock(b);
        return REPLY_NONE;
    }
    if (!strcmp(t, "pin")) {
        if (!pin) return REPLY_NONE;
        bool ok = b->pin[0] && strcmp(pin, b->pin) == 0;
        c->teacher = ok;
        return (ok ? REPLY_PIN_OK : REPLY_PIN_NG) | REPLY_STATUS;
    }
    if (!strcmp(t, "force_release")) {
        if (c->teacher) release_lock(b);
        return REPLY_NONE;
    }
    if (!strcmp(t, "show_mode")) {
        if (on < 0) return REPLY_NONE;
        if (c->teacher && b->show_mode != (bool)on) {
            b->show_mode = on;
            b->version++;
        }
        return REPLY_NONE;
    }
    return REPLY_NONE;
}

void box_net(box_core_t *b, owner_kind_t kind, uint32_t ip, const uint8_t *slots, int len, uint32_t now)
{
    if (b->owner == OWNER_NONE) {
        if (b->allowed && !b->allowed(ip)) return;
        b->owner = kind;
        b->owner_ip = ip;
        b->last_seen = now;
        b->version++;
    }
    if (b->owner != kind || b->owner_ip != ip) return;
    if (len > DMX_SLOTS) len = DMX_SLOTS;
    if (len < 0) len = 0;
    memcpy(b->output, slots, len);
    if (len < DMX_SLOTS) memset(b->output + len, 0, DMX_SLOTS - len);
    b->out_version++;
    b->last_seen = now;
}

void box_artnet(box_core_t *b, uint32_t ip, const uint8_t *slots, int len, uint32_t now)
{
    box_net(b, OWNER_ARTNET, ip, slots, len, now);
}

void box_net_terminated(box_core_t *b, owner_kind_t kind, uint32_t ip)
{
    if (b->owner == kind && b->owner_ip == ip && !b->show_mode) release_lock(b);
}

void box_tick(box_core_t *b, uint32_t now)
{
    if (b->owner != OWNER_NONE && !b->show_mode && (uint32_t)(now - b->last_seen) >= b->timeout_ms)
        release_lock(b);
}

void box_button(box_core_t *b) { release_lock(b); }

int box_holder_json(const box_core_t *b, int conn, char *buf, int size)
{
    if (b->owner == OWNER_WS)
        return snprintf(buf, size, "{\"kind\":\"ws\",\"you\":%s}", box_is_my_lock(b, conn) ? "true" : "false");
    if (b->owner == OWNER_ARTNET || b->owner == OWNER_SACN) {
        const uint8_t *p = (const uint8_t *)&b->owner_ip;
        return snprintf(buf, size, "{\"kind\":\"%s\",\"ip\":\"%u.%u.%u.%u\"}", b->owner == OWNER_SACN ? "sacn" : "artnet", p[0], p[1], p[2], p[3]);
    }
    return snprintf(buf, size, "null");
}

int box_status_json(const box_core_t *b, int conn, int max_clients, char *buf, int size)
{
    char h[64];
    box_holder_json(b, conn, h, sizeof(h));
    bool teacher = conn >= 0 && conn < BOX_MAX_CONN && b->conns[conn].used && b->conns[conn].teacher;
    return snprintf(buf, size, "{\"t\":\"status\",\"holder\":%s,\"show_mode\":%s,\"teacher\":%s,\"max_clients\":%d}",
                    h, b->show_mode ? "true" : "false", teacher ? "true" : "false", max_clients);
}
