# ode_main rev A のファーム（STM32F407VGT6）: make
# 出力: build/ode_main.elf / .hex / .bin（STM32CubeProgrammer で 0x08000000 に書く）
LWIP ?= vendor/lwip
PREFIX = arm-none-eabi-
CC = $(PREFIX)gcc
OBJCOPY = $(PREFIX)objcopy
SIZE = $(PREFIX)size

CPU = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
DEFS = -DSTM32F407xx -DHSE_VALUE=8000000 -DODE_HW_CHECKSUM '-DAPP_CCM=__attribute__((section(".ccmram")))'
INC = -Iapp -Iport/common -Iport/stm32 -Ivendor/cmsis/Include -Ivendor/cmsis_f4 -I$(LWIP)/src/include
CFLAGS = $(CPU) $(DEFS) $(INC) -Os -g -Wall -Wno-unused-function -ffunction-sections -fdata-sections -std=gnu11
LDFLAGS = $(CPU) -Tport/stm32/stm32f407vg.ld -Wl,--gc-sections -Wl,-Map=build/ode_main.map --specs=nano.specs --specs=nosys.specs -Wl,--print-memory-usage

LWIP_SRC = $(LWIP)/src/core/init.c $(LWIP)/src/core/def.c $(LWIP)/src/core/inet_chksum.c $(LWIP)/src/core/ip.c \
  $(LWIP)/src/core/mem.c $(LWIP)/src/core/memp.c $(LWIP)/src/core/netif.c $(LWIP)/src/core/pbuf.c \
  $(LWIP)/src/core/tcp.c $(LWIP)/src/core/tcp_in.c $(LWIP)/src/core/tcp_out.c $(LWIP)/src/core/timeouts.c \
  $(LWIP)/src/core/udp.c $(wildcard $(LWIP)/src/core/ipv4/*.c) $(LWIP)/src/netif/ethernet.c
APP_SRC = app/ui.c app/sacn.c app/app.c app/box_core.c app/artnet.c app/http.c app/minijson.c app/sha1.c app/settings.c app/assets_gen.c
PORT_SRC = port/stm32/main.c port/stm32/board.c port/stm32/eth.c port/stm32/dmx.c port/stm32/flash_settings.c \
  port/stm32/mac_eeprom.c port/stm32/system_stm32f4xx.c
ASM_SRC = port/stm32/startup_stm32f407xx.s

OBJ = $(patsubst %.c,build/obj/%.o,$(notdir $(APP_SRC) $(PORT_SRC) $(LWIP_SRC))) build/obj/startup.o
vpath %.c app port/stm32 $(LWIP)/src/core $(LWIP)/src/core/ipv4 $(LWIP)/src/netif

all: build/ode_main.hex build/ode_main.bin

build/obj/%.o: %.c $(wildcard app/*.h port/stm32/*.h port/common/*.h)
	@mkdir -p build/obj
	$(CC) $(CFLAGS) -c $< -o $@
build/obj/startup.o: $(ASM_SRC)
	@mkdir -p build/obj
	$(CC) $(CPU) -c $< -o $@
build/ode_main.elf: $(OBJ) port/stm32/stm32f407vg.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJ)
	$(SIZE) $@
build/ode_main.hex: build/ode_main.elf
	$(OBJCOPY) -O ihex $< $@
build/ode_main.bin: build/ode_main.elf
	$(OBJCOPY) -O binary $< $@

host:
	$(MAKE) -f Makefile.host LWIP=$(LWIP)
clean:
	rm -rf build
.PHONY: all host clean
