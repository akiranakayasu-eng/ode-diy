/* 小さな JSON の読み取り。トップレベルのオブジェクトから文字列か真偽値を 1 つ取り出すだけ。 */
#ifndef MINIJSON_H
#define MINIJSON_H
/* key の文字列値を out に入れる。見つからない・文字列でなければ 0、成功で 1 */
int mj_get_str(const char *json, int len, const char *key, char *out, int outsize);
/* key の真偽値。true=1 false=0 無い/違う=-1 */
int mj_get_bool(const char *json, int len, const char *key);
/* s を JSON の文字列の中身として out に書く（" \ と制御文字を逃がす。UTF-8 として正しくないバイトは ? にする）。書いた長さを返す */
int mj_escape(const char *s, char *out, int outsize);
/* s の先頭から UTF-8 の正しい 1 文字の長さ（1〜4）。正しくなければ 0 */
int mj_utf8_len(const unsigned char *s);
/* s 全体が UTF-8 として正しければ 1 */
int mj_utf8_ok(const char *s);
#endif
