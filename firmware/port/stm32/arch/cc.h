#ifndef ARCH_CC_H
#define ARCH_CC_H
#include <stdint.h>
#include <stdlib.h>
#define LWIP_PLATFORM_DIAG(x) do { } while (0)
#define LWIP_PLATFORM_ASSERT(x) do { NVIC_SystemReset_wrapper(); } while (0)
void NVIC_SystemReset_wrapper(void);
#define LWIP_RAND() ((u32_t)rand())
#define LWIP_NO_UNISTD_H 1
#endif
