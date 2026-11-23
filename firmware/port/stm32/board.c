#include "board.h"
#include <stdarg.h>
#include <stdio.h>

volatile uint32_t g_ms;

void SysTick_Handler(void) { g_ms++; }

void board_delay_ms(uint32_t ms)
{
    uint32_t t = g_ms;
    while ((uint32_t)(g_ms - t) < ms) board_iwdg_kick();
}

/* HSE 8MHz → PLL（M=8, N=336, P=2, Q=7）→ SYSCLK 168MHz, USB 48MHz。APB1 42MHz, APB2 84MHz */
void board_clock_init(void)
{
    RCC->CR |= RCC_CR_HSEON;
    for (uint32_t i = 0; !(RCC->CR & RCC_CR_HSERDY); i++)
        if (i > 2000000) break;   /* 水晶が動かなければ HSI のまま進む（LED で分かる） */
    if (!(RCC->CR & RCC_CR_HSERDY)) { SystemCoreClockUpdate(); SysTick_Config(SystemCoreClock / 1000); return; }

    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    PWR->CR |= PWR_CR_VOS;
    RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2))
              | RCC_CFGR_HPRE_DIV1 | RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2;
    RCC->PLLCFGR = (8 << RCC_PLLCFGR_PLLM_Pos) | (336 << RCC_PLLCFGR_PLLN_Pos) | (0 << RCC_PLLCFGR_PLLP_Pos)
                 | RCC_PLLCFGR_PLLSRC_HSE | (7 << RCC_PLLCFGR_PLLQ_Pos);
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {}
    FLASH->ACR = FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_PRFTEN | FLASH_ACR_LATENCY_5WS;
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {}
    SystemCoreClockUpdate();
    SysTick_Config(SystemCoreClock / 1000);
}

static void pin_mode(GPIO_TypeDef *g, int pin, int mode, int otype, int speed, int pupd, int af)
{
    g->MODER = (g->MODER & ~(3u << (pin * 2))) | ((uint32_t)mode << (pin * 2));
    g->OTYPER = (g->OTYPER & ~(1u << pin)) | ((uint32_t)otype << pin);
    g->OSPEEDR = (g->OSPEEDR & ~(3u << (pin * 2))) | ((uint32_t)speed << (pin * 2));
    g->PUPDR = (g->PUPDR & ~(3u << (pin * 2))) | ((uint32_t)pupd << (pin * 2));
    if (pin < 8) g->AFR[0] = (g->AFR[0] & ~(0xfu << (pin * 4))) | ((uint32_t)af << (pin * 4));
    else g->AFR[1] = (g->AFR[1] & ~(0xfu << ((pin - 8) * 4))) | ((uint32_t)af << ((pin - 8) * 4));
}
#define IN 0
#define OUT 1
#define AF 2
#define PU 1

void board_gpio_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN | RCC_AHB1ENR_GPIOCEN | RCC_AHB1ENR_GPIODEN | RCC_AHB1ENR_GPIOEEN;
    (void)RCC->AHB1ENR;
    /* DMX: PE0/PE1 は High（マーク）で待つ。PD7（DE）は DMX を始めるときに High にする */
    GPIOE->BSRR = (1u << 0) | (1u << 1);
    pin_mode(GPIOE, 0, OUT, 0, 3, 0, 0);
    pin_mode(GPIOE, 1, OUT, 0, 3, 0, 0);
    GPIOD->BSRR = 1u << (7 + 16);
    pin_mode(GPIOD, 7, OUT, 0, 1, 0, 0);
    /* LED */
    GPIOC->BSRR = (1u << (10 + 16)) | (1u << (11 + 16));
    pin_mode(GPIOC, 10, OUT, 0, 0, 0, 0);
    pin_mode(GPIOC, 11, OUT, 0, 0, 0, 0);
    /* ボタン */
    pin_mode(GPIOD, 4, IN, 0, 0, PU, 0);
}

bool board_button_raw(void) { return (GPIOD->IDR & (1u << 4)) == 0; }
void board_led_stat(bool on) { GPIOC->BSRR = on ? (1u << 11) : (1u << (11 + 16)); }
void plat_led_lock(bool on) { GPIOC->BSRR = on ? (1u << 10) : (1u << (10 + 16)); }

/* 約 4 秒（LSI 32kHz / 64 / 2000）。フラッシュの消去（最大 2 秒）より長く */
void board_iwdg_init(void)
{
    DBGMCU->APB1FZ |= DBGMCU_APB1_FZ_DBG_IWDG_STOP;   /* デバッガで止めている間（書き込み中）は番犬も止める */
    IWDG->KR = 0x5555;
    IWDG->PR = 4;
    IWDG->RLR = 2000;
    IWDG->KR = 0xCCCC;
    IWDG->KR = 0xAAAA;
}

void board_uart_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    pin_mode(GPIOA, 9, AF, 0, 1, 0, 7);
    pin_mode(GPIOA, 10, AF, 0, 1, PU, 7);
    USART1->BRR = (84000000 + 115200 / 2) / 115200;   /* APB2 84MHz */
    USART1->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

static void uart_putc(char c)
{
    uint32_t t = 0;
    while (!(USART1->SR & USART_SR_TXE) && ++t < 100000) {}
    USART1->DR = (uint8_t)c;
}

void board_log(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n > (int)sizeof(buf) - 1) n = sizeof(buf) - 1;
    for (int i = 0; i < n; i++) { if (buf[i] == '\n') uart_putc('\r'); uart_putc(buf[i]); }
}

void plat_reboot(void) { NVIC_SystemReset(); }

/* ---- ファーム更新モード（USB DFU） ----
 * 目印をバックアップレジスタ（リセットでは消えない、電源を切ると消える）に書いてリセットし、
 * 起動直後の board_dfu_check で ROM のブートローダ（0x1FFF0000）へ飛ぶ。
 * ROM のブートローダは HSE 8MHz を使って J1 の USB-C（PA11/PA12、OTG_FS）で DFU として見える。 */
#define DFU_MAGIC 0x44465530u   /* "DFU0" */
void plat_enter_dfu(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR;
    PWR->CR |= PWR_CR_DBP;
    RTC->BKP0R = DFU_MAGIC;
    board_log("dfu: ファーム更新モードで再起動\n");
    for (volatile int i = 0; i < 200000; i++) {}
    NVIC_SystemReset();
}

void board_dfu_check(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR;
    PWR->CR |= PWR_CR_DBP;
    if (RTC->BKP0R != DFU_MAGIC) { PWR->CR &= ~PWR_CR_DBP; return; }
    RTC->BKP0R = 0;                                   /* 次の再起動は普通に起動する */
    PWR->CR &= ~PWR_CR_DBP;
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC->APB2ENR;
    SYSCFG->MEMRMP = SYSCFG_MEMRMP_MEM_MODE_0;        /* 0 番地にシステムメモリ */
    const uint32_t *sys = (const uint32_t *)0x1FFF0000u;
    __set_MSP(sys[0]);
    ((void (*)(void))sys[1])();
    for (;;) {}
}

void HardFault_Handler(void) { NVIC_SystemReset(); }
void NVIC_SystemReset_wrapper(void) { NVIC_SystemReset(); }
