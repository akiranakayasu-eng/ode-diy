/* U4 24AA02E48（I2C アドレス 0x50）の 0xFA〜0xFF から MAC アドレスを読む。PB6 SCL / PB7 SDA をソフトで動かす（外付けプルアップあり） */
#include "board.h"

#define SCL 6
#define SDA 7

static void dly(void) { for (volatile int i = 0; i < 200; i++) {} }   /* 約 100kHz */
static void scl(int v) { GPIOB->BSRR = v ? (1u << SCL) : (1u << (SCL + 16)); dly(); }
static void sda(int v) { GPIOB->BSRR = v ? (1u << SDA) : (1u << (SDA + 16)); dly(); }
static int  sda_in(void) { return (GPIOB->IDR >> SDA) & 1; }

static void i2c_start(void) { sda(1); scl(1); sda(0); scl(0); }
static void i2c_stop(void) { sda(0); scl(1); sda(1); }
static int i2c_write(uint8_t b)
{
    for (int i = 7; i >= 0; i--) { sda((b >> i) & 1); scl(1); scl(0); }
    sda(1); scl(1);
    int ack = !sda_in();
    scl(0);
    return ack;
}
static uint8_t i2c_read(int ack)
{
    uint8_t b = 0;
    sda(1);
    for (int i = 7; i >= 0; i--) { scl(1); b |= (uint8_t)(sda_in() << i); scl(0); }
    sda(!ack); scl(1); scl(0); sda(1);
    return b;
}

bool mac_eeprom_read(uint8_t mac[6])
{
    GPIOB->BSRR = (1u << SCL) | (1u << SDA);
    GPIOB->OTYPER |= (1u << SCL) | (1u << SDA);                  /* オープンドレイン */
    GPIOB->MODER = (GPIOB->MODER & ~((3u << (SCL * 2)) | (3u << (SDA * 2)))) | (1u << (SCL * 2)) | (1u << (SDA * 2));
    for (int i = 0; i < 9; i++) { scl(1); scl(0); }              /* 途中で止まった相手を解く */
    i2c_stop();
    bool ok = false;
    i2c_start();
    if (i2c_write(0xA0) && i2c_write(0xFA)) {
        i2c_start();
        if (i2c_write(0xA1)) {
            for (int i = 0; i < 6; i++) mac[i] = i2c_read(i < 5);
            ok = true;
        }
    }
    i2c_stop();
    if (ok && (mac[0] & 1)) ok = false;                          /* マルチキャストの値なら使わない */
    if (ok && !(mac[0] | mac[1] | mac[2])) ok = false;
    return ok;
}
