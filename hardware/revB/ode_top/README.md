# ode_top rev B（ode_main rev B の天板）回路図 1 版（2026-11-23）

天板 = ケースの上の板（1.6mm FR-4）。四隅の M3 スペーサーで本体の上 35mm に留める（構成案_revB.md のケース）。

- 回路図 1 版: ERC 0、設計意図との照合 0（28 ピン / 11 ネット）。別スレッドのチェックはまだ（PCB と一緒に頼む）
- J1 JST PH 8P: 本体 J6 と 1:1 のケーブル（1 +3V3 / 2 GND / 3 EN_PANEL / 4 BTN_LOCK / 5 LED_LAN / 6 LED_DMX / 7 LED_LOCK / 8 予備）
- D1 PWR（+3V3 から常時）、D2 LAN、D3 DMX、D4 LOCK。R1〜R4 680Ω（rev A と同じ約 2mA。D2〜D4 は本体の R84〜R86 100Ω も通る）
- SW1 LOCK（BTN_LOCK → GND、本体 IO7 の内部プルアップ、本体に R83 1k＋C78 100n）
- SW2 RESET（EN_PANEL → GND、本体 R79 1k を通して EN）。クリップで押す
- H1〜H4 M3 穴（本体・底板とそろえる）

未定: LED の色と型番、スイッチの型番と高さ（クリップで押す穴の作り方）は PCB で決める。

作り直し: `KICAD_SYMDIR=<KiCad 10 の symbols> python3 scripts/gen_sch.py`（2 回）→ `sh run_erc.sh`
