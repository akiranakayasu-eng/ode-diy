# ode_main — 自作 ODE（Art-Net → DMX512 2 ポート）rev A

ENTTEC ODE Mk2 の代わりに使う Art-Net / sACN → DMX ノード。miseru との [WebSocket 仕様](../../../docs/websocket-spec.md)に合わせる。（ENTTEC・ODE は ENTTEC 社の商標で、このプロジェクトは ENTTEC 社と関係がない）
ポートは 2 つ分の場所があり、初回は 1 ポートだけ実装してもよい（ポート 2 は後付け）。

## 状態（2026-11-23）

- 回路図: ERC 0、ネット照合 0。PCB rev A（100 × 84 mm、4 層）: DRC エラー 0 / 未接続 0、回路図との不一致 0
- JLCPCB で基板を作り、DMX 1 系統だけを手で実装した 1 台が動いている（2026-11-10 立ち上げ、[記録](docs/実機立ち上げ記録_2026-11-10.md)）。ファーム v0.2.0 で Ethernet・画面・WebSocket・Art-Net・sACN・DMX 出力を実機で確認済み
- 発注前レビュー: docs/PCBレビュー_2026-10-25.md
- ガーバー: ode_main_revA_gerber.zip（JLCPCB 用、4 層）
- 部品リスト: 部品リスト_revA.md、店ごとの買い物リスト 買い物リスト_revA.md
- **実装時の注意**: F1 は基板のパッドが 1206 だが、買い物リストの秋月 113955 PICOSMDC110S-2 は 0805。はんだを多めにして付けた（1206 の 0ZCJ0110FF2E なら合う）。ほかの代替部品は[立ち上げ記録](docs/実機立ち上げ記録_2026-11-10.md)の「実装時の注意・代替部品」

## 構成

| 部分 | 部品 | 内容 |
|---|---|---|
| MCU | U1 STM32F407VGT6（LQFP-100） | Ethernet MAC + LwIP で Art-Net を受ける。管理画面（HTTP / WebSocket）もここ |
| PHY / RJ45 | U3 LAN8742A + Y2 25MHz、J5 RJMG1BD3B8K1ANR | sacn_node_main と同じ回路（RMII、REF_CLK を PHY から出す） |
| 電源 | J1 USB-C（5V シンク、CC 5.1k）、U5 USBLC6、F1 PTC 1.1A、Q1 AO3401A 突入制限、U6 AP7361C-33E | 5V → +3V3。ADM2587E は +5V 直接 |
| DMX 出力 | U11 / U21 ADM2587E（絶縁 2.5kV）、U7 / U8 / U9 74AHCT1G125（3.3→5V） | XLR3 メス（J11 / J21）と JST XH 3P（J12 / J22）を並列。1 = GND、2 = Data−、3 = Data+ |
| MAC | U4 24AA02E48 | EUI-48 入り EEPROM |
| 操作 | SW1 RESET、SW2 LOCK、LED PWR / LOCK / STAT | LOCK ボタンを押したまま電源を入れると IP と PIN を初期値に戻す |
| 書き込み | J3 SWD 10 ピン、USB DFU（PA11 / PA12、JP1 = BOOT0）、J4 UART | |

### MCU ピン割り当て

| 機能 | ピン |
|---|---|
| DMX TX1 / TX2 | PE0 / PE1（タイマ起動の DMA で GPIO へ。sacn_node と同じ方式） |
| DE（2 ポート共通、10k プルダウン） | PD7 |
| RMII | PA1 REF_CLK, PA2 MDIO, PA7 CRS_DV, PC1 MDC, PC4 RXD0, PC5 RXD1, PB11 TX_EN, PB12 TXD0, PB13 TXD1, PB14 PHY nRST |
| USB | PA11 D−, PA12 D+ |
| LED / ボタン | PC10 LOCK, PC11 STAT / PD4 LOCK ボタン |
| I2C1（EEPROM） | PB6 SCL, PB7 SDA |
| デバッグ | PA13 SWDIO, PA14 SWCLK, PB3 SWO, PA9 / PA10 USART1 |

## 既定の設定

- IP 192.168.1.223（固定。ボタンでの初期化でこの値に戻る）
- WebSocket の同時接続数の上限 = 機器としての上限（30、実機で確定）。超えたら 1013 で閉じる

## 作り直し方（docker の kicad 10）

```
python3 scripts/gen_sch.py                     # 回路図
cat scripts/_pcb_*.py ... > scripts/gen_pcb.py  # 分割した部品を連結（順番は _pcb_body, _netlist, _pcb_place, _pcb_build, _refs, _pcb_tail）
python3 scripts/gen_pcb.py --geom && python3 scripts/route.py && python3 scripts/gen_pcb.py
bash scripts/_fin.sh                           # DRC、verify_pcb、3D 図
bash scripts/gerb.sh                           # ガーバー zip
```
