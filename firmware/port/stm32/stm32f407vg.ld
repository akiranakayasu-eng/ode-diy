/* STM32F407VGT6: フラッシュ 1MB、SRAM 128KB（DMA 可）、CCM 64KB（DMA 不可）
 * v0.3.0〜: セクタ 0〜7（512KB）がファーム、セクタ 8〜10（0x08080000〜0x080DFFFF、384KB）は画面の差し替え用、
 * セクタ 11（0x080E0000）は設定。（v0.2.x までは画面がセクタ 10 だけ・128KB） */
ENTRY(Reset_Handler)
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
  CCM   (rw)  : ORIGIN = 0x10000000, LENGTH = 64K
}
_estack = ORIGIN(RAM) + LENGTH(RAM);
_Min_Heap_Size = 0x800;
_Min_Stack_Size = 0x1000;

SECTIONS
{
  .isr_vector : { . = ALIGN(4); KEEP(*(.isr_vector)) . = ALIGN(4); } >FLASH
  .text : {
    . = ALIGN(4);
    *(.text) *(.text*) *(.glue_7) *(.glue_7t) *(.eh_frame)
    KEEP (*(.init)) KEEP (*(.fini))
    . = ALIGN(4); _etext = .;
  } >FLASH
  .rodata : { . = ALIGN(4); *(.rodata) *(.rodata*) . = ALIGN(4); } >FLASH
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } >FLASH
  .ARM : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } >FLASH
  .preinit_array : { PROVIDE_HIDDEN (__preinit_array_start = .); KEEP (*(.preinit_array*)) PROVIDE_HIDDEN (__preinit_array_end = .); } >FLASH
  .init_array : { PROVIDE_HIDDEN (__init_array_start = .); KEEP (*(SORT(.init_array.*))) KEEP (*(.init_array*)) PROVIDE_HIDDEN (__init_array_end = .); } >FLASH
  .fini_array : { PROVIDE_HIDDEN (__fini_array_start = .); KEEP (*(SORT(.fini_array.*))) KEEP (*(.fini_array*)) PROVIDE_HIDDEN (__fini_array_end = .); } >FLASH

  _sidata = LOADADDR(.data);
  .data : { . = ALIGN(4); _sdata = .; *(.data) *(.data*) . = ALIGN(4); _edata = .; } >RAM AT> FLASH

  .bss : {
    . = ALIGN(4); _sbss = .; __bss_start__ = _sbss;
    *(.bss) *(.bss*) *(COMMON)
    . = ALIGN(4); _ebss = .; __bss_end__ = _ebss;
  } >RAM

  /* CCM: 0 で初期化しない領域。main の最初で 0 にする */
  .ccmram (NOLOAD) : { . = ALIGN(4); _sccm = .; *(.ccmram) *(.ccmram*) . = ALIGN(4); _eccm = .; } >CCM

  ._user_heap_stack : {
    . = ALIGN(8); PROVIDE ( end = . ); PROVIDE ( _end = . );
    . = . + _Min_Heap_Size; . = . + _Min_Stack_Size; . = ALIGN(8);
  } >RAM

  .ARM.attributes 0 : { *(.ARM.attributes) }
}
/* ファームの終わり = 画面の置き場（セクタ 8）の始まり。番地は RM0090 表 5 / ST の例 ADDR_FLASH_SECTOR_8 */
ASSERT(ORIGIN(FLASH) + LENGTH(FLASH) == 0x08080000, "FLASH の終わりがセクタ 8 の始まりと合わない")
