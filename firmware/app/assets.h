#ifndef ASSETS_H
#define ASSETS_H
#include <stdint.h>
typedef struct {
    const char *path;   /* 先頭の / は付けない。index.html は "index.html" */
    const char *mime;
    const uint8_t *data;
    uint32_t len;
    uint8_t gzip;
} asset_t;
extern const asset_t g_assets[];
extern const int g_nassets;
#endif
