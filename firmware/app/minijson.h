/* 小さな JSON の読み取り。トップレベルのオブジェクトから文字列か真偽値を 1 つ取り出すだけ。 */
#ifndef MINIJSON_H
#define MINIJSON_H
/* key の文字列値を out に入れる。見つからない・文字列でなければ 0、成功で 1 */
int mj_get_str(const char *json, int len, const char *key, char *out, int outsize);
/* key の真偽値。true=1 false=0 無い/違う=-1 */
int mj_get_bool(const char *json, int len, const char *key);
#endif
