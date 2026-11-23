#include "app.h"
#include <string.h>

box_core_t g_box;
settings_t g_settings;
static uint32_t last_out_version = 0xffffffff;
static uint32_t last_version;
static uint8_t saved_show_mode;

static bool allowed_cb(uint32_t ip) { return settings_allowed(&g_settings, ip); }

void app_init(struct netif *nif)
{
    box_init(&g_box, g_settings.pin, g_settings.show_mode);
    g_box.allowed = allowed_cb;
    ui_check();
    saved_show_mode = g_settings.show_mode;
    plat_dmx_write(g_box.output);   /* 起動直後はロック無し・全消灯（規則 6） */
    plat_led_lock(false);
    artnet_init(nif);
    sacn_init(nif);
    http_init();
}

static uint32_t ui_window_until;
static bool ui_window_on;
void app_ui_window_open(void) { ui_window_on = true; ui_window_until = plat_now_ms() + UI_WINDOW_MS; }
uint32_t app_ui_window_left_s(void)
{
    if (!ui_window_on) return 0;
    int32_t left = (int32_t)(ui_window_until - plat_now_ms());
    if (left <= 0) { ui_window_on = false; return 0; }
    return ((uint32_t)left + 999u) / 1000u;
}

void app_button(void)
{
    box_button(&g_box);
    ws_broadcast_status();
}

void app_poll(void)
{
    box_tick(&g_box, plat_now_ms());
    if (g_box.out_version != last_out_version) {
        last_out_version = g_box.out_version;
        plat_dmx_write(g_box.output);
    }
    if (g_box.version != last_version) {
        last_version = g_box.version;
        plat_led_lock(g_box.owner != OWNER_NONE);
        ws_broadcast_status();
        if (g_box.show_mode != saved_show_mode) {   /* 公演モードはフラッシュに残す（規則 6） */
            saved_show_mode = g_box.show_mode;
            g_settings.show_mode = g_box.show_mode;
            plat_settings_save(&g_settings);
        }
    }
    http_poll();
}
