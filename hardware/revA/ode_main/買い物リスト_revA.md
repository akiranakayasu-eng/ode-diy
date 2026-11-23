---
title: ode_main rev A 買い物リスト（店ごと）
updated: 2026-10-25
---

# ode_main rev A 買い物リスト（2026-10-25）


買う店は **秋月と Digi-Key の 2 か所だけ**にまとめた。
「1 ポート版」はいまのスタジオ用（DMX 出力 1 つ）、「2 ポート版」は 2 つとも載せる場合。参照の ( ) 内が 2 ポート目の部品。
手持ち（秋月の購入履歴）に使えるものは無かった（手持ちはリード部品が中心）。カートには入れていない。

## 合計

| | 1 ポート版 | 2 ポート版 |
|---|---|---|
| 秋月（20 品目） | ¥4,165 | ¥5,975 |
| Digi-Key（25 品目、単価は概算） | 約 ¥5,212 | 約 ¥5,918 |
| **部品代の合計** | **約 ¥9,377** | **約 ¥11,893** |

- 秋月はパック売りの分（抵抗 5 個入、コンデンサ 10〜20 個入など）を含めた支払額。余りは次の基板で使える。
- 秋月の送料は 1 回分（数百円）。Digi-Key は合計 ¥8,000 以上（税込）なら送料無料のはずで、この量なら越える。
- 基板代は別（JLCPCB 4 層 5 枚で約 ¥3,000〜5,000）。

## 1. 秋月で買うもの

| 部品 | 型番 | 参照 | 1 ポート版 | 2 ポート版 | コード | 価格 | 備考 |
|---|---|---|---|---|---|---|---|
| 絶縁 RS-485 トランシーバー SOIC-20W | ADM2587EBRWZ | U11 / U21 | 1 個 | 2 個 | [113300](https://akizukidenshi.com/catalog/g/g113300/) | ¥1,800 / 1 個 | 在庫あり |
| JST XH 3P ベース 縦型 | B3B-XH-A | J12 / J22 | 1 個 | 2 個 | [112248](https://akizukidenshi.com/catalog/g/g112248/) | ¥10 / 1 個 |  |
| ピンヘッダ 1.27mm 2×5（SWD） | PH11-2x5SAG | J3 | 1 個 | 1 個 | [113800](https://akizukidenshi.com/catalog/g/g113800/) | ¥25 / 1 個 |  |
| ピンヘッダ 2.54mm 1×3（UART、BOOT0 は 1 本折って 2P に） | PH-1X3SG | J4 / JP1 | 2 個 → 1 点 | 2 個 → 1 点 | [103949](https://akizukidenshi.com/catalog/g/g103949/) | ¥40 / 10 個入 | 10 個入。JP1 のジャンパーピンは手持ちを使う |
| 水晶 3225 8MHz | 8M10PB | Y1 | 1 個 → 1 点 | 1 個 → 1 点 | [130238](https://akizukidenshi.com/catalog/g/g130238/) | ¥250 / 4 個入 | 4 個入 |
| 水晶 3225 25MHz | FA-238 25.0000MB-K | Y2 | 1 個 → 1 点 | 1 個 → 1 点 | [102459](https://akizukidenshi.com/catalog/g/g102459/) | ¥200 / 4 個入 | 4 個入 |
| PTC 1.1A / 6V 面実装 | PICOSMDC110S-2 | F1 | 1 個 | 1 個 | [113955](https://akizukidenshi.com/catalog/g/g113955/) | ¥40 / 1 個 | 1206 サイズか商品ページで確認 |
| フェライトビーズ 2012 | BLM21PG331SN1D | FB1 FB2 FB101 FB102 (FB201 FB202) | 4 個 → 1 点 | 6 個 → 1 点 | [104053](https://akizukidenshi.com/catalog/g/g104053/) | ¥100 / 25 個入 | 25 個入 |
| チップ LED 2012 緑（PWR、ISO） | OSG50805C1C | D4 D12 (D22) | 2 個 → 1 点 | 3 個 → 1 点 | [106423](https://akizukidenshi.com/catalog/g/g106423/) | ¥200 / 10 個入 | 10 個入 |
| チップ LED 2012 黄（LOCK、STAT） | OSY50805C1C | D5 D6 | 2 個 → 1 点 | 2 個 → 1 点 | [106420](https://akizukidenshi.com/catalog/g/g106420/) | ¥100 / 10 個入 | 10 個入 |
| MLCC 3225 22µF 25V X7R | GRM32ER71E226KE15 | C3 | 1 個 → 1 点 | 1 個 → 1 点 | [106047](https://akizukidenshi.com/catalog/g/g106047/) | ¥250 / 5 個入 | 5 個入 |
| MLCC 3225 10µF 50V X7R | GRM32ER71H106KA12 | C5 | 1 個 → 1 点 | 1 個 → 1 点 | [116113](https://akizukidenshi.com/catalog/g/g116113/) | ¥200 / 5 個入 | 5 個入 |
| MLCC 2012 10µF 25V | GRM21BB31E106KA73 | C104 C106 (C204 C206) | 2 個 → 1 点 | 4 個 → 1 点 | [113388](https://akizukidenshi.com/catalog/g/g113388/) | ¥100 / 20 個入 | 20 個入 |
| MLCC 2012 4.7µF 16V X7R | GRM21BR71C475KE51 | C1 C37 C57 | 3 個 → 1 点 | 3 個 → 1 点 | [131147](https://akizukidenshi.com/catalog/g/g131147/) | ¥100 / 20 個入 | 20 個入 |
| MLCC 2012 2.2µF 25V X7R | （秋月 114788） | C38 C39 | 2 個 → 1 点 | 2 個 → 1 点 | [114788](https://akizukidenshi.com/catalog/g/g114788/) | ¥100 / 10 個入 | 10 個入 |
| MLCC 2012 1µF 10V X7R | CL21B105KPFNNNE | C2 C28 C53 | 3 個 → 1 点 | 3 個 → 1 点 | [107549](https://akizukidenshi.com/catalog/g/g107549/) | ¥150 / 40 個入 | 40 個入。115331（50V）は販売終了のため変更。使う所は 5V 以下 |
| チップ抵抗 2012 10kΩ（0.1%） | （秋月 111797） | R31 R32 R64 R65 R66 R74 | 6 個 → 2 点 | 6 個 → 2 点 | [111797](https://akizukidenshi.com/catalog/g/g111797/) | ¥100 / 5 個入 | 5 個入 |
| チップ抵抗 2012 1kΩ（0.1%） | （秋月 111796） | R101 (R201) | 1 個 → 1 点 | 2 個 → 1 点 | [111796](https://akizukidenshi.com/catalog/g/g111796/) | ¥100 / 5 個入 | 5 個入 |
| チップ抵抗 2012 100kΩ（0.1%） | （秋月 111798） | R3 | 1 個 → 1 点 | 1 個 → 1 点 | [111798](https://akizukidenshi.com/catalog/g/g111798/) | ¥100 / 5 個入 | 5 個入 |
| チップ抵抗 2012 1MΩ（0.1%） | （秋月 111799） | R73 | 1 個 → 1 点 | 1 個 → 1 点 | [111799](https://akizukidenshi.com/catalog/g/g111799/) | ¥100 / 5 個入 | 5 個入 |

## 2. Digi-Key で買うもの

秋月では扱いが無かったもの（IC、コネクタ、1% 抵抗、0.1µF・18pF の 2012 など）。Digi-Key の円建て単価は直接取れていないので概算。カートに入れると確定する。

| 部品 | 型番 | 参照 | 1 ポート版 | 2 ポート版 | コード | 価格 | 備考 |
|---|---|---|---|---|---|---|---|
| MCU LQFP-100 | STM32F407VGT6 | U1 | 1 個 | 1 個 | [497-11605-ND](https://www.digikey.jp/ja/products/result?keywords=STM32F407VGT6) | 約 ¥2,400 / 個 |  |
| Ethernet PHY VQFN-24 | LAN8742A-CZ-TR | U3 | 1 個 | 1 個 | [LAN8742A-CZ-CT-ND](https://www.digikey.jp/ja/products/result?keywords=LAN8742A-CZ-TR) | 約 ¥300 / 個 |  |
| RJ45 トランス・LED 内蔵 | RJMG1BD3B8K1ANR | J5 | 1 個 | 1 個 | [RJMG1BD3B8K1ANR-ND](https://www.digikey.jp/ja/products/result?keywords=RJMG1BD3B8K1ANR) | 約 ¥900 / 個 |  |
| XLR3 メス 基板用 水平 | NC3FAH | J11 (J21) | 1 個 | 2 個 | [6473-NC3FAH-ND](https://www.digikey.jp/ja/products/result?keywords=NC3FAH) | 約 ¥480 / 個 |  |
| USB-C レセプタクル 16P | TYPE-C-31-M-12 | J1 | 1 個 | 1 個 | [TYPE-C-31-M-12](https://www.digikey.jp/ja/products/result?keywords=TYPE-C-31-M-12) | 約 ¥80 / 個 | Digi-Key に無ければ LCSC C165948 |
| EUI-48 EEPROM SOT-23-5 | 24AA02E48T-I/OT | U4 | 1 個 | 1 個 | [24AA02E48T-I/OTCT-ND](https://www.digikey.jp/ja/products/result?keywords=24AA02E48T-I/OT) | 約 ¥70 / 個 | 秋月 131330 は 6 ピン品で足が合わない |
| LDO 3.3V 1A SOT-223 | AP7361C-33E-13 | U6 | 1 個 | 1 個 | [AP7361C-33EDICT-ND](https://www.digikey.jp/ja/products/result?keywords=AP7361C-33E-13) | 約 ¥90 / 個 | ピン順は公式データシートで確認済み（E = SOT223、1 IN / 2 GND / 3 OUT）。ER（逆並び）を選ばない |
| USB ESD 保護 SOT-23-6 | USBLC6-2SC6 | U5 | 1 個 | 1 個 | [497-5235-1-ND](https://www.digikey.jp/ja/products/result?keywords=USBLC6-2SC6) | 約 ¥60 / 個 |  |
| P-ch MOSFET SOT-23 | AO3401A | Q1 | 1 個 | 1 個 | [785-1001-1-ND](https://www.digikey.jp/ja/products/result?keywords=AO3401A) | 約 ¥40 / 個 |  |
| バッファ 3.3→5V SOT-23-5 | SN74AHCT1G125DBVR | U7 U9 (U8) | 2 個 | 3 個 | [296-1010-1-ND](https://www.digikey.jp/ja/products/result?keywords=SN74AHCT1G125DBVR) | 約 ¥50 / 個 |  |
| TVS RS-485 用 SOT-23 | SM712 | D11 (D21) | 1 個 | 2 個 | [SM712](https://www.digikey.jp/ja/products/result?keywords=SM712) | 約 ¥90 / 個 |  |
| タクト SW 面実装 6mm | TL3342F160QG/TR | SW1 SW2 | 2 個 | 2 個 | [EG2531CT-ND](https://www.digikey.jp/ja/products/result?keywords=TL3342F160QG/TR) | 約 ¥90 / 個 |  |
| MLCC 3216 1nF 2kV | C1206C102KGRACTU | C61 C109 (C209) | 2 個 | 3 個 | [399-C1206C102KGRACTUCT-ND](https://www.digikey.jp/ja/products/result?keywords=C1206C102KGRACTU) | 約 ¥60 / 個 |  |
| MLCC 2012 0.1µF 50V X7R | CL21B104KBCNNNC | C4 C6 C29 C31-C36 C40 C43 C55 C56 C58-C60 C71-C73 C101 C103 C105 C107 (C201 C203 C205 C207) | 23 個 | 27 個 | [1276-1003-1-ND](https://www.digikey.jp/ja/products/result?keywords=CL21B104KBCNNNC) | 約 ¥4 / 個 | 30 個買っておくと楽 |
| MLCC 2012 10nF 50V X7R | CL21B103KBANNNC | C102 C108 (C202 C208) | 2 個 | 4 個 | [1276-1015-1-ND](https://www.digikey.jp/ja/products/result?keywords=CL21B103KBANNNC) | 約 ¥5 / 個 |  |
| MLCC 2012 18pF C0G | GRM2165C1H180JA01D | C41 C42 C51 C52 | 4 個 | 4 個 | [490-1575-1-ND](https://www.digikey.jp/ja/products/result?keywords=GRM2165C1H180JA01D) | 約 ¥8 / 個 |  |
| MLCC 2012 470pF C0G | GRM2165C1H471JA01D | C54 | 1 個 | 1 個 | [490-1601-1-ND](https://www.digikey.jp/ja/products/result?keywords=GRM2165C1H471JA01D) | 約 ¥8 / 個 |  |
| チップ抵抗 2012 5.1kΩ | RC0805FR-075K1L | R1 R2 | 2 個 | 2 個 | [311-5.10KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-075K1L) | 約 ¥10 / 個 | USB-C の CC |
| チップ抵抗 2012 680Ω | RC0805FR-07680RL | R29 R33 R34 | 3 個 | 3 個 | [311-680CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-07680RL) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 4.7kΩ | RC0805FR-074K7L | R37 R38 | 2 個 | 2 個 | [311-4.70KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-074K7L) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 12.1kΩ 1% | RC0805FR-0712K1L | R61 | 1 個 | 1 個 | [311-12.1KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0712K1L) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 33Ω | RC0805FR-0733RL | R62 | 1 個 | 1 個 | [311-33.0CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0733RL) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 1.5kΩ | RC0805FR-071K5L | R63 | 1 個 | 1 個 | [311-1.50KCRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-071K5L) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 470Ω | RC0805FR-07470RL | R67 R68 | 2 個 | 2 個 | [311-470CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-07470RL) | 約 ¥10 / 個 |  |
| チップ抵抗 2012 49.9Ω 1% | RC0805FR-0749R9L | R69-R72 | 4 個 | 4 個 | [311-49.9CRCT-ND](https://www.digikey.jp/ja/products/result?keywords=RC0805FR-0749R9L) | 約 ¥10 / 個 |  |

## メモ

- **電源 IC（U6 AP7361C-33E-13）**: 2026-10-25 に公式データシートで確認済み。E = SOT223 で 1 = IN、2 = GND（タブ）、3 = OUT、基板どおり。ER（逆並び）を選ばない。
- 秋月には 3.3V の LDO（AZ1117CH-3.3、116155、¥30）があるが、ピン順が 1 = GND、2 = OUT、3 = IN で違うため、そのままでは載らない。使うなら基板を直す（rev A のままなら AP7361C を Digi-Key で買う）。
- 秋月の 24AA025E48（131330）は 6 ピン品で、この基板の 5 ピンのフットプリントには載らない。
- 2 ポート版にするときに Digi-Key で追加で要るもの: NC3FAH、SM712、1nF 2kV、74AHCT1G125、0.1µF・10nF 少々。秋月で追加: ADM2587E、XH、LED、1kΩ、10µF。
