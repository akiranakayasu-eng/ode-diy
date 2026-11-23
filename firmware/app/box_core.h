/* 送信元ロック（門番）。miseru の src/box/core.ts を C に写したもの。
 * 仕様: docs/websocket-spec.md
 * ネットワークにも時計にも依存しない。時刻は呼び出し側が ms で渡す。 */
#ifndef BOX_CORE_H
#define BOX_CORE_H
#include <stdint.h>
#include <stdbool.h>

#define DMX_SLOTS 512
#define BOX_ID_MAX 64
#ifndef BOX_MAX_CONN
#define BOX_MAX_CONN 30
#endif
#define BOX_LOCK_TIMEOUT_MS 5000u

typedef enum { OWNER_NONE = 0, OWNER_WS, OWNER_ARTNET, OWNER_SACN } owner_kind_t;

typedef struct {
    bool used;
    bool teacher;
    char id[BOX_ID_MAX + 1]; /* 空なら hello 前 */
    uint32_t ip;             /* 相手の IP（許可リスト用） */
} box_conn_t;

typedef struct {
    uint8_t output[DMX_SLOTS];
    bool show_mode;
    uint32_t version;       /* ロックか公演モードが変わるたびに増える */
    uint32_t out_version;   /* output が変わるたびに増える */
    owner_kind_t owner;
    char owner_id[BOX_ID_MAX + 1];
    uint32_t owner_ip;      /* lwIP の ip4_addr の addr（ネットワーク順） */
    uint32_t last_seen;
    uint32_t timeout_ms;
    char pin[16];           /* 空なら先生の操作は使えない */
    box_conn_t conns[BOX_MAX_CONN];
    int nconns;
    bool (*allowed)(uint32_t ip); /* 許可リスト。NULL ならだれでもロックを取れる */
} box_core_t;

/* 返事。status は呼び出し側が box_status_json で作る */
typedef enum { REPLY_NONE = 0, REPLY_STATUS = 1, REPLY_DENIED_BUSY = 2, REPLY_DENIED_NOHELLO = 4, REPLY_PIN_OK = 8, REPLY_PIN_NG = 16, REPLY_DENIED_NOTALLOWED = 32 } box_reply_t;

void box_init(box_core_t *b, const char *pin, bool show_mode);
int  box_open(box_core_t *b, uint32_t ip);   /* 空きが無ければ -1 */
void box_close(box_core_t *b, int conn);
void box_binary(box_core_t *b, int conn, const uint8_t *data, int len, uint32_t now);
/* t: メッセージの種類。id/pin は該当するときだけ。on は show_mode の値 */
int  box_message(box_core_t *b, int conn, const char *t, const char *id, const char *pin, int on, uint32_t now);
void box_artnet(box_core_t *b, uint32_t ip, const uint8_t *slots, int len, uint32_t now);
/* Art-Net と同じ規則で、種類だけ変える（sACN は OWNER_SACN） */
void box_net(box_core_t *b, owner_kind_t kind, uint32_t ip, const uint8_t *slots, int len, uint32_t now);
/* sACN の Stream_Terminated: その送り手がロックを持っていれば外す（公演モード中は外さない） */
void box_net_terminated(box_core_t *b, owner_kind_t kind, uint32_t ip);
void box_tick(box_core_t *b, uint32_t now);
void box_button(box_core_t *b);
bool box_is_my_lock(const box_core_t *b, int conn);
/* status の JSON を buf に書く。conn < 0 なら接続に依らない形（you=false, teacher=false） */
int  box_status_json(const box_core_t *b, int conn, int max_clients, const char *name_esc, char *buf, int size); /* name_esc は JSON 用に逃がした箱の名前（仕様 v1.1） */
/* GET /api/dmx の holder 部分 */
int  box_holder_json(const box_core_t *b, int conn, char *buf, int size);
#endif
