/* 設定をフラッシュのセクタ 11（0x080E0000、128KB）にログ形式で書く。
 * 記録を後ろへ足していき、読むときは最後の正しい記録を使う。満杯になったら消して先頭から。
 * 記録の長さは先頭の magic で決まる（v1 "ODE1" = 80 バイト、v2 "ODE2" = 128 バイト）。v1 は読むときに v2 に直す。 */
#include "board.h"
#include <string.h>
#include <stddef.h>

/* STM32F407 のセクタの番地（RM0090 表 5）: 0〜3 は 16KB、4 は 64KB、5〜11 は 128KB。
 * 番地を手で書かず、必ずこれで出す（v0.3.0 の作りかけで 8 番を 0x080A0000 と取り違えたため） */
#define F4_SECTOR_ADDR(n) ((n) < 4 ? 0x08000000u + (uint32_t)(n) * 0x4000u : (n) == 4 ? 0x08010000u : 0x08020000u + (uint32_t)((n) - 5) * 0x20000u)
#define SECTOR      11
#define BASE        0x080E0000u
#define SIZE        0x20000u

static uint32_t rec_len(uint32_t magic)
{
    if (magic == SETTINGS_MAGIC) return sizeof(settings_t);
    if (magic == SETTINGS_MAGIC_V1) return SETTINGS_V1_SIZE;
    return 0;
}

/* 最後の記録の次（書き足す位置）。壊れた記録があればそこで止める */
static uint32_t scan(settings_t *out, bool *found)
{
    uint32_t a = BASE;
    *found = false;
    while (a + 4 <= BASE + SIZE) {
        uint32_t m = *(const uint32_t *)a;
        if (m == 0xFFFFFFFFu) break;
        uint32_t n = rec_len(m);
        if (!n || a + n > BASE + SIZE) { a = BASE + SIZE; break; }   /* 読めない → 満杯扱い（次の保存で消す） */
        if (m == SETTINGS_MAGIC) {
            const settings_t *s = (const settings_t *)a;
            if (s->crc == settings_crc(s)) { if (out) memcpy(out, s, sizeof(*s)); *found = true; }
        } else {
            uint32_t crc = *(const uint32_t *)(a + SETTINGS_V1_SIZE - 4);
            if (crc == crc32_buf((const void *)a, SETTINGS_V1_SIZE - 4)) {
                if (out) {
                    memset(out, 0, sizeof(*out));
                    memcpy(out, (const void *)a, SETTINGS_V1_SIZE - 4);   /* v1 の並びは v2 の前半と同じ */
                    out->magic = SETTINGS_MAGIC;
                }
                *found = true;
            }
        }
        a += n;
    }
    return a;
}

bool flash_settings_load(settings_t *out)
{
    bool found;
    scan(out, &found);
    return found;
}

static void wait_busy(void) { while (FLASH->SR & FLASH_SR_BSY) board_iwdg_kick(); }

void flash_unlock(void)
{
    if (FLASH->CR & FLASH_CR_LOCK) { FLASH->KEYR = 0x45670123; FLASH->KEYR = 0xCDEF89AB; }
    FLASH->SR = FLASH_SR_EOP | FLASH_SR_OPERR | FLASH_SR_WRPERR | FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR;
}

void flash_erase_sector(int sector)
{
    __disable_irq();     /* DMX の割り込みは止まるが、その間 線は MARK のまま（消去は 1〜2 秒） */
    board_iwdg_kick();
    flash_unlock();
    wait_busy();
    FLASH->CR = FLASH_CR_PSIZE_1 | FLASH_CR_SER | ((uint32_t)sector << FLASH_CR_SNB_Pos);
    FLASH->CR |= FLASH_CR_STRT;
    wait_busy();
    FLASH->CR = FLASH_CR_LOCK;
    __enable_irq();
}

/* バイト単位で書く（どの位置からでも書ける） */
void flash_program_bytes(uint32_t addr, const uint8_t *d, uint32_t n)
{
    flash_unlock();
    for (uint32_t i = 0; i < n; i++) {
        wait_busy();
        FLASH->CR = FLASH_CR_PG;                       /* PSIZE = x8 */
        *(volatile uint8_t *)(addr + i) = d[i];
    }
    wait_busy();
    FLASH->CR = FLASH_CR_LOCK;
}

void flash_settings_save(const settings_t *in)
{
    settings_t s;
    memcpy(&s, in, sizeof(s));
    s.magic = SETTINGS_MAGIC;
    s.seq++;
    s.crc = settings_crc(&s);
    bool found;
    uint32_t a = scan(NULL, &found);
    if (a + sizeof(s) > BASE + SIZE) { flash_erase_sector(SECTOR); a = BASE; }
    __disable_irq();
    const uint32_t *w = (const uint32_t *)&s;
    flash_unlock();
    for (uint32_t i = 0; i < sizeof(s) / 4; i++) {
        wait_busy();
        FLASH->CR = FLASH_CR_PSIZE_1 | FLASH_CR_PG;
        *(volatile uint32_t *)(a + i * 4) = w[i];
    }
    wait_busy();
    FLASH->CR = FLASH_CR_LOCK;
    __enable_irq();
}

void plat_settings_save(const settings_t *s) { flash_settings_save(s); }

/* ---- 差し替え画面の置き場: セクタ 8〜10（0x08080000〜0x080DFFFF、128KB × 3 = 384KB、v0.3.0〜） ----
 * 消去は 1 セクタ 1〜2 秒、その間は割り込みが止まる。まとめて消すと 3〜6 秒止まるので、
 * plat_ui_erase は先頭のセクタだけを消し、書き込みが次のセクタに入るときにそのセクタを消す。 */
#define UI_SECTOR0  8
#define UI_SECTORS  3
#define UI_SECTSZ   0x20000u
#define UI_BASE     F4_SECTOR_ADDR(UI_SECTOR0)   /* = 0x08080000 */
_Static_assert(F4_SECTOR_ADDR(8) == 0x08080000u && F4_SECTOR_ADDR(10) == 0x080C0000u && F4_SECTOR_ADDR(11) == 0x080E0000u, "sector table");
_Static_assert(F4_SECTOR_ADDR(UI_SECTOR0 + UI_SECTORS) == BASE, "画面の置き場の終わり = 設定のセクタ 11 の始まり");
static uint32_t ui_erased_end;     /* ここまでは消してある（置き場の先頭からのバイト数） */
const uint8_t *plat_ui_base(void) { return (const uint8_t *)UI_BASE; }
uint32_t plat_ui_size(void) { return UI_SECTORS * UI_SECTSZ; }
void plat_ui_erase(void) { flash_erase_sector(UI_SECTOR0); ui_erased_end = UI_SECTSZ; }
void plat_ui_write(uint32_t off, const uint8_t *d, uint32_t n)
{
    if (off + n > plat_ui_size()) return;
    while (off + n > ui_erased_end) {
        flash_erase_sector(UI_SECTOR0 + (int)(ui_erased_end / UI_SECTSZ));
        ui_erased_end += UI_SECTSZ;
    }
    flash_program_bytes(UI_BASE + off, d, n);
}
