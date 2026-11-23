---
title: ode_main rev A 部品リスト
updated: 2026-10-25
---

# ode_main rev A 部品リスト（2026-10-25）

自作 ODE（Art-Net → DMX 2 ポート）のメイン基板 1 枚分。調達の優先: 秋月 → マルツ → Digi-Key。価格は税込の概算。
「要確認」は sacn_node の部品リストの単価を流用したものか、Digi-Key の円建てを直接取っていない概算。
カートへの投入と注文はしていない。

| 参照 | 部品 | 型番 | 数 | 購入先 | コード | 単価 | 小計 | 備考 |
|---|---|---|---|---|---|---|---|---|
| U1 | MCU LQFP-100 | STM32F407VGT6 | 1 | Digi-Key | [497-11605-ND](https://www.digikey.jp/ja/products/result?keywords=STM32F407VGT6) | ¥2,400 (要確認) | ¥2,400 | sacn_node_main と同じ。マルツ M1430-5658 |
| U3 | Ethernet PHY VQFN-24 | LAN8742A-CZ-TR | 1 | Digi-Key | [LAN8742A-CZ-CT-ND](https://www.digikey.jp/ja/products/result?keywords=LAN8742A-CZ-TR) | ¥300 (要確認) | ¥300 | sacn_node_main と同じ |
| U4 | EUI-48 EEPROM SOT-23-5 | 24AA02E48T-I/OT | 1 | Digi-Key | [24AA02E48T-I/OTCT-ND](https://www.digikey.jp/ja/products/result?keywords=24AA02E48T-I/OT) | ¥70 (要確認) | ¥70 | MAC アドレス入り |
| U11 U21 | 絶縁 RS-485 SOIC-20W | ADM2587EBRWZ | 2 | 秋月 | [113300](https://akizukidenshi.com/catalog/g/g113300/) | ¥1,800 | ¥3,600 | ポート 2 は後付け可（初回は 1 個でもよい） |
| U5 | USB ESD 保護 SOT-23-6 | USBLC6-2SC6 | 1 | Digi-Key | [497-5235-1-ND](https://www.digikey.jp/ja/products/result?keywords=USBLC6-2SC6) | ¥60 (要確認) | ¥60 |  |
| U6 | LDO 3.3V 1A SOT-223 | MCP1826ST-3302E/DB | 1 | Digi-Key | [MCP1826ST-3302E/DBCT-ND](https://www.digikey.jp/ja/products/detail/microchip-technology/MCP1826ST-3302E-DB/1635505) | ¥150 | ¥150 | 2026-10-25 AP7361C-33E-13 から変更（入荷日未定のため）。DS22057B で 1=VIN 2(タブ)=GND 3=VOUT を確認、基板どおり |
| U7 U8 U9 | バッファ 3.3→5V SOT-23-5 | SN74AHCT1G125DBVR | 3 | Digi-Key | [296-1010-1-ND](https://www.digikey.jp/ja/products/result?keywords=SN74AHCT1G125DBVR) | ¥50 (要確認) | ¥150 |  |
| Q1 | P-ch MOSFET SOT-23 (突入電流制限) | AO3401A | 1 | Digi-Key | [785-1001-1-ND](https://www.digikey.jp/ja/products/result?keywords=AO3401A) | ¥40 (要確認) | ¥40 | 秋月にもあれば秋月で |
| J1 | USB-C レセプタクル 16P | HRO TYPE-C-31-M-12 | 1 | LCSC/秋月 | [C165948](https://www.lcsc.com/product-detail/C165948.html) | ¥80 (要確認) | ¥80 | 秋月で同じフットプリントの品があればそちら |
| J5 | RJ45 トランス・LED 内蔵 | RJMG1BD3B8K1ANR | 1 | Digi-Key | [RJMG1BD3B8K1ANR-ND](https://www.digikey.jp/ja/products/result?keywords=RJMG1BD3B8K1ANR) | ¥900 (要確認) | ¥900 | sacn_node_main と同じ |
| J11 J21 | XLR3 メス 基板用 水平 | NC3FAH | 2 | Digi-Key | [6473-NC3FAH-ND](https://www.digikey.jp/ja/products/result?keywords=NC3FAH) | ¥480 (要確認) | ¥960 |  |
| J12 J22 | JST XH 3P ベース 縦型 | B3B-XH-A | 2 | 秋月 | [112248](https://akizukidenshi.com/catalog/g/g112248/) | ¥10 | ¥20 | XLR と並列 |
| J3 | ピンヘッダ 1.27mm 2×5 (SWD) | PH11-2x5SAG | 1 | 秋月 | [113800](https://akizukidenshi.com/catalog/g/g113800/) | ¥25 | ¥25 |  |
| J4 JP1 | ピンヘッダ 2.54mm (UART 1×3、BOOT0 1×2) | PH-1X40SG を切る | 1 | 秋月 | [100167](https://akizukidenshi.com/catalog/g/g100167/) | ¥35 | ¥35 | JP1 にはジャンパーピンも |
| SW1 SW2 | タクト SW 面実装 6mm | TL3342F160QG/TR | 2 | Digi-Key | [EG2531CT-ND](https://www.digikey.jp/ja/products/result?keywords=TL3342F160QG) | ¥90 (要確認) | ¥180 |  |
| Y1 | 水晶 3225 8MHz | 8M10PB | 1 | 秋月 | [130238](https://akizukidenshi.com/catalog/g/g130238/) | ¥63 | ¥63 |  |
| Y2 | 水晶 3225 25MHz | FA-238 25.0000MB-K | 1 | 秋月 | [102459](https://akizukidenshi.com/catalog/g/g102459/) | ¥50 | ¥50 |  |
| D11 D21 | TVS RS-485 用 SOT-23 | SM712 | 2 | Digi-Key | [1655-SM712CT-ND](https://www.digikey.jp/ja/products/result?keywords=SM712) | ¥90 (要確認) | ¥180 |  |
| F1 | PTC 1206 1.1A 6V | 0ZCJ0110FF2E | 1 | Digi-Key | [F3466CT-ND](https://www.digikey.jp/ja/products/result?keywords=0ZCJ0110FF2E) | ¥40 (要確認) | ¥40 |  |
| FB1 FB2 FB101 FB102 FB201 FB202 | フェライトビーズ 2012 | BLM21PG331SN1D | 6 | 秋月 | [104053](https://akizukidenshi.com/catalog/g/g104053/) | ¥4 | ¥24 | 221 の代替 |
| D4 D12 D22 | チップ LED 2012 緑 (PWR, ISO) | OSG50805C1C | 3 | 秋月 | [106423](https://akizukidenshi.com/catalog/g/g106423/) | ¥20 | ¥60 |  |
| D5 D6 | チップ LED 2012 黄 (LOCK, STAT) | OSY50805C1C | 2 | 秋月 | [106420](https://akizukidenshi.com/catalog/g/g106420/) | ¥10 | ¥20 |  |
| C61 C109 C209 | MLCC 3216 1nF 2kV | C1206C102KGRACTU | 3 | Digi-Key | [399-C1206C102KGRACTUCT-ND](https://www.digikey.jp/ja/products/result?keywords=C1206C102KGRACTU) | ¥60 (要確認) | ¥180 |  |
| C3 | MLCC 3225 22µF 10V以上 | GRM32ER61C226KE20 | 1 | 秋月 | (秋月で 3225 22µF を検索) | ¥30 (要確認) | ¥30 |  |
| C5 | MLCC 3225 10µF 10V以上 | GRM32DR71E106KA12 | 1 | 秋月 | (秋月で 3225 10µF を検索) | ¥30 (要確認) | ¥30 |  |
| C104 C106 C204 C206 | MLCC 2012 10µF 16V | CL21A106KOQNNNE | 4 | 秋月 | [113161](https://akizukidenshi.com/catalog/g/g113161/) | ¥10 (要確認) | ¥40 | ADM2587E の VISO / VCC |
| C1 C37 C57 | MLCC 2012 4.7µF 16V | GRM21BR71C475KE51 | 3 | 秋月 | [131147](https://akizukidenshi.com/catalog/g/g131147/) | ¥5 | ¥15 |  |
| C38 C39 | MLCC 2012 2.2µF 25V | (秋月 114788) | 2 | 秋月 | [114788](https://akizukidenshi.com/catalog/g/g114788/) | ¥10 | ¥20 |  |
| C2 C28 C53 | MLCC 2012 1µF 50V | C2012X7R1H105KT000N | 3 | 秋月 | [115331](https://akizukidenshi.com/catalog/g/g115331/) | ¥10 | ¥30 |  |
| C4 C6 C29 C31-C36 C40 C43 C55 C56 C58-C60 C71-C73 C101 C103 C105 C107 C201 C203 C205 C207 | MLCC 2012 0.1µF 50V X7R | CL21B104KBCNNNC | 27 | Digi-Key | [1276-1003-1-ND](https://www.digikey.jp/ja/products/result?keywords=CL21B104KBCNNNC) | ¥4 (要確認) | ¥108 |  |
| C102 C108 C202 C208 | MLCC 2012 10nF 50V | CL21B103KBANNNC | 4 | Digi-Key | [1276-1015-1-ND](https://www.digikey.jp/ja/products/result?keywords=CL21B103KBANNNC) | ¥5 (要確認) | ¥20 |  |
| C41 C42 C51 C52 | MLCC 2012 18pF C0G | GRM2165C1H180JA01D | 4 | Digi-Key | [490-1575-1-ND](https://www.digikey.jp/ja/products/result?keywords=GRM2165C1H180JA01D) | ¥8 (要確認) | ¥32 |  |
| C54 | MLCC 2012 470pF C0G | GRM2165C1H471JA01D | 1 | Digi-Key | [490-1601-1-ND](https://www.digikey.jp/ja/products/result?keywords=GRM2165C1H471JA01D) | ¥8 (要確認) | ¥8 |  |
| R31 R32 R64 R65 R66 R74 | チップ抵抗 2012 10kΩ | (秋月 111797) | 6 | 秋月 | [111797](https://akizukidenshi.com/catalog/g/g111797/) | ¥20 | ¥120 |  |
| R3 | チップ抵抗 2012 100kΩ | (秋月 111798) | 1 | 秋月 | [111798](https://akizukidenshi.com/catalog/g/g111798/) | ¥20 | ¥20 |  |
| R73 | チップ抵抗 2012 1MΩ | (秋月 111799) | 1 | 秋月 | [111799](https://akizukidenshi.com/catalog/g/g111799/) | ¥20 | ¥20 |  |
| R101 R201 | チップ抵抗 2012 1kΩ | (秋月 111796) | 2 | 秋月 | [111796](https://akizukidenshi.com/catalog/g/g111796/) | ¥20 | ¥40 |  |
| R1 R2 | チップ抵抗 2012 1% 5.1kΩ (CC) | RC0805FR-075K1L | 2 | Digi-Key | [311-5.10KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-075K1L) | ¥10 (要確認) | ¥20 |  |
| R29 R33 R34 | チップ抵抗 2012 680Ω | RC0805FR-07680RL | 3 | Digi-Key | [311-680CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-07680RL) | ¥10 (要確認) | ¥30 |  |
| R37 R38 | チップ抵抗 2012 4.7kΩ | RC0805FR-074K7L | 2 | Digi-Key | [311-4.70KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-074K7L) | ¥10 (要確認) | ¥20 |  |
| R61 | チップ抵抗 2012 1% 12.1kΩ | RC0805FR-0712K1L | 1 | Digi-Key | [311-12.1KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0712K1L) | ¥10 (要確認) | ¥10 |  |
| R62 | チップ抵抗 2012 33Ω | RC0805FR-0733RL | 1 | Digi-Key | [311-33.0CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0733RL) | ¥10 (要確認) | ¥10 |  |
| R63 | チップ抵抗 2012 1.5kΩ | RC0805FR-071K5L | 1 | Digi-Key | [311-1.50KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-071K5L) | ¥10 (要確認) | ¥10 |  |
| R67 R68 | チップ抵抗 2012 470Ω | RC0805FR-07470RL | 2 | Digi-Key | [311-470CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-07470RL) | ¥10 (要確認) | ¥20 |  |
| R69-R72 | チップ抵抗 2012 1% 49.9Ω | RC0805FR-0749R9L | 4 | Digi-Key | [311-49.9CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0749R9L) | ¥10 (要確認) | ¥40 |  |

## 合計

| | 金額 |
|---|---|
| 1 枚の部品代（2 ポート実装） | **¥10,220**（うち要確認 ¥6,058） |
| ポート 2 を後付けにした場合（ADM2587E・XLR・XH・SM712・1nF・周辺 C/FB/LED を除く） | 約 ¥7,672 |
| 基板（JLCPCB 4 層 100×84mm、5 枚） | 約 ¥3,000〜5,000（送料別、要確認） |

部品点数: 45 行、119 個。ADM2587E（1 個 ¥1,800）、STM32F407（¥2,400）、RJ45（¥900）で部品代の 7 割近く。
