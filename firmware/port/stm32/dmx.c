/* DMX512 の送出。TIM8 の更新（4µs = 250kbit/s）ごとに DMA2 Stream1 が 1 バイトを GPIOE->ODR の下位 8 bit に書く。
 * bit0 = PE0（ポート 1）、bit1 = PE1（ポート 2、rev A は未実装。同じ値を出す）。PE2〜PE7 は未使用（入力のまま）。
 * 1 フレーム: BREAK 176µs（44 bit）、MAB 16µs（4 bit）、スタートコード 0 + 512 スロット（各 11 bit: start 0, 8 bit LSB 先, stop 2）、
 * 最後に MARK 1 bit。約 22.8ms で 1 フレーム（約 44 フレーム/秒）。フレームの合間（割り込みで作り直すあいだ）は MARK。 */
#include "board.h"
#include <string.h>

#define BREAK_BITS 44
#define MAB_BITS   4
#define FRAME_BITS (BREAK_BITS + MAB_BITS + 513 * 11 + 1)
#define LOW  0x00
#define HIGH 0x03

static uint8_t bits[FRAME_BITS];          /* SRAM（DMA が読む。CCM には置かない） */
static uint8_t pending[512];
static volatile uint8_t pending_flag;
static uint8_t current[512];
volatile uint32_t g_dmx_frames;

static void build(void)
{
    uint8_t *p = bits;
    memset(p, LOW, BREAK_BITS); p += BREAK_BITS;
    memset(p, HIGH, MAB_BITS); p += MAB_BITS;
    for (int s = -1; s < 512; s++) {
        uint8_t v = s < 0 ? 0 : current[s];
        *p++ = LOW;                                   /* start bit */
        for (int b = 0; b < 8; b++) *p++ = (v >> b) & 1 ? HIGH : LOW;
        *p++ = HIGH; *p++ = HIGH;                     /* stop bit 2 つ */
    }
    *p++ = HIGH;
}

static void start(void)
{
    DMA2_Stream1->CR &= ~DMA_SxCR_EN;
    while (DMA2_Stream1->CR & DMA_SxCR_EN) {}
    DMA2->LIFCR = 0x3Du << 6;                         /* Stream1 のフラグを消す */
    DMA2_Stream1->M0AR = (uint32_t)bits;
    DMA2_Stream1->NDTR = FRAME_BITS;
    DMA2_Stream1->CR |= DMA_SxCR_EN;
    TIM8->CNT = 0;
    TIM8->CR1 |= TIM_CR1_CEN;
}

void DMA2_Stream1_IRQHandler(void)
{
    if (DMA2->LISR & DMA_LISR_TCIF1) {
        TIM8->CR1 &= ~TIM_CR1_CEN;
        DMA2->LIFCR = DMA_LIFCR_CTCIF1;
        if (pending_flag) { memcpy(current, pending, 512); pending_flag = 0; }
        build();                                      /* 約 0.1ms。そのあいだ線は MARK のまま */
        g_dmx_frames++;
        start();
    } else {
        DMA2->LIFCR = 0x3Du << 6;
    }
}

void dmx_set(const uint8_t *slots)
{
    /* 割り込みと取り合わないよう、書くあいだだけ DMA の割り込みを止める */
    NVIC_DisableIRQ(DMA2_Stream1_IRQn);
    memcpy(pending, slots, 512);
    pending_flag = 1;
    NVIC_EnableIRQ(DMA2_Stream1_IRQn);
}

void plat_dmx_write(const uint8_t *slots) { dmx_set(slots); }

void dmx_init(void)
{
    memset(current, 0, sizeof(current));
    build();
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA2EN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM8EN;
    (void)RCC->APB2ENR;

    TIM8->CR1 = 0;
    TIM8->PSC = 0;
    TIM8->ARR = 168 * 4 - 1;                          /* TIM8 は 168MHz → 4µs */
    TIM8->DIER = TIM_DIER_UDE;
    TIM8->EGR = TIM_EGR_UG;
    TIM8->SR = 0;

    DMA2_Stream1->CR = 0;
    DMA2_Stream1->PAR = (uint32_t)&GPIOE->ODR;        /* 下位 8 bit にバイトで書く */
    DMA2_Stream1->FCR = 0;                            /* ダイレクトモード */
    DMA2_Stream1->CR = (7u << DMA_SxCR_CHSEL_Pos)     /* TIM8_UP */
                     | (3u << DMA_SxCR_PL_Pos)        /* 優先度 最高 */
                     | DMA_SxCR_MINC
                     | (1u << DMA_SxCR_DIR_Pos)       /* メモリ → 周辺 */
                     | DMA_SxCR_TCIE;
    NVIC_SetPriority(DMA2_Stream1_IRQn, 1);
    NVIC_EnableIRQ(DMA2_Stream1_IRQn);

    GPIOD->BSRR = 1u << 7;                            /* DE = High（送信許可） */
    start();
}
