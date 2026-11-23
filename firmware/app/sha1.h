#ifndef SHA1_H
#define SHA1_H
#include <stdint.h>
#include <stddef.h>
void sha1(const uint8_t *data, size_t len, uint8_t out[20]);
int base64_encode(const uint8_t *in, int len, char *out, int outsize);
#endif
