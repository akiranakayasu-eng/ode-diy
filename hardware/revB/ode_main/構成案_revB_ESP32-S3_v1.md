# ode_main rev B 構成案 v1（ESP32-S3 Wi-Fi 一体版、2026-11-19）

自作 ODE（Art-Net／sACN → DMX）rev B を、ESP32-S3 ＋ W5500 の Wi-Fi 一体版として作る。STM32 版 rev B（v0、構成案_revB.md）は作らない。ケースの決定（底板・本体・天板を M3 スペーサーで重ね、側板 4 枚を挟み込む、天板に LED 4 つとロック解除ボタン、JST で天板とつなぐ）は v0 のまま使う。

- 印: 【確】データシートで確かめた（出典は末尾）、【プ】このプロジェクトの資料・実機、【未】確かめていない
- この構成案は作ったスレッドでの検討。別スレッドでのチェックはまだ。
- 部品の購入と基板の発注は延期中（年末か来年度）。

## 決まったこと（作者）

| 項目 | 決定 |
|---|---|
| 無線 | Wi-Fi を一体にする。有線 LAN も残して併用（11/19） |
| Wi-Fi で使うもの | Art-Net／sACN に加え、miseru の画面・WebSocket・/setup も（11/19） |
| マイコン | ESP32-S3-WROOM-1-N16R8（秋月 117256、技適 201-220052）単独。STM32 は外す（11/19） |
| 有線 LAN | W5500（SPI）＋ RJ45（11/19） |
| DMX 出力 | 1 系統（11/11） |
| 給電・書き込み | USB-C 5V のまま（11/11）。書き込みは ESP32-S3 の USB から直接 |
| ケース・天板・取り付け穴・シルク | v0 のとおり（11/11） |

## ブロック

```
USB-C ─ USBLC6 ─┬─ D+/D− → ESP32-S3 IO20/IO19（書き込み・ログ）
                └─ 5V ─ PTC ─ 突入制限 ─┬─ LDO 3.3V 1A → ESP32-S3、W5500、LED
                                         └─ ADM2587E（絶縁 RS-485）→ XLR3 ＋ XH3
ESP32-S3 ─ SPI ─ W5500 ─ RJ45（トランス内蔵）
ESP32-S3 ─ UART1 TX ─ 74AHCT1G125 ─ ADM2587E
ESP32-S3 ─ JST 8 ピン ─ 天板（LED・ロック解除・リセット）
```

## rev A から変わる所

| 部分 | rev A | rev B（ESP32-S3 版） |
|---|---|---|
| マイコン | U1 STM32F407VGT6 | ESP32-S3-WROOM-1-N16R8（18 × 25.5mm、アンテナ部 6mm）【確】 |
| 有線 LAN | U3 LAN8742A ＋ Y2 25MHz ＋ RJMG1BD3B8K1ANR | W5500（LQFP-48）＋ 25MHz（負荷 18pF ×2）＋ EXRES1 12.4kΩ 1% ＋ 1V2O に 10nF【確】。RJ45 は下の「要確認」 |
| MAC アドレス | U4 24AA02E48 | 外す。ESP32-S3 の eFuse の MAC を使い、ESP-IDF の esp_eth_ioctl(ETH_CMD_S_MAC_ADDR) で W5500 に渡す【確: ESP-IDF Ethernet API】 |
| 書き込み | SWD（J3）、USB DFU（JP1） | USB-C から直接（USB Serial/JTAG）。BOOT ボタン（IO0 を GND へ）と EN のリセット。J3・JP1 は外す |
| DMX | PE0 を DMA で出す、DE は PD7 | UART1 TX（IO17）で出す。ブレークは UART で作る。DE は IO21（10k プルダウン、rev A と同じ考え） |
| EN（リセット） | NRST | EN に RC（10kΩ・1µF）【確: データシートの推奨】、SW と天板の NRST 線をここへ |

電源・USB-C・ADM2587E・74AHCT1G125・XLR3／XH3・SM712 は rev A と同じ回路を使う【プ】。

## ピン割り当て案（ESP32-S3-WROOM-1-N16R8）

使わないピン【確】: IO35・IO36・IO37（8MB の Octal PSRAM につながる）。起動を決めるピン【確】: IO0（BOOT）、IO46（何もつながない、内部プルダウン）、IO45（何もつながない、内部プルダウン = 3.3V のフラッシュ）、IO3（JTAG の切り替え、何もつながない）。

| 機能 | ピン | メモ |
|---|---|---|
| USB D− / D+ | IO19 / IO20 | 書き込み・ログ【確】 |
| UART0 TX / RX（ログ用 J4） | IO43 / IO44 | 予備のログ口【確】 |
| W5500 SCSn / MOSI / SCLK / MISO | IO10 / IO11 / IO12 / IO13 | SPI2（FSPI）の IO_MUX のピン【確: ピン一覧の FSPICS0・FSPID・FSPICLK・FSPIQ】。W5500 の SPI はモード 0／3、最大 80MHz【確】 |
| W5500 INTn / RSTn | IO14 / IO9 | RSTn は 500µs 以上 Low【確】 |
| DMX TX / DE | IO17 / IO21 | IO17 は U1TXD【確】。DE は起動時のグリッチが無い IO21 にした（11/19 チェック低 1。IO18 は約 60µs のグリッチあり）。TX は R78 10k でプルアップ。IO17 と TX_M の間に R82（0Ω、ハードウェア設計ガイド UART の直列抵抗、3 版） |
| 天板 LED_LAN / LED_DMX / LED_LOCK | IO4 / IO5 / IO6 | |
| 天板 LOCK ボタン | IO7 | 内部プルアップで読む。R83 1k＋C78 100n を通す（5 版）。LED 線も R84〜R86 100Ω を通す |
| 本体 STAT LED | IO18 | |
| USB-C CC1 / CC2 の電圧（電源の強さを知る） | IO1 / IO2（ADC1_CH0 / CH1） | 11/19 チェック低 8。コネクタのピンを直結しないよう、R80・R81 22k を通し、ESP32 側に C74・C75 100nF（2 版チェック中 1 で直した、3 版。4 版で 10nF から 100nF） |
| BOOT ボタン | IO0 | 押して EN を離すと書き込みモード【確: Download Boot は IO0=0・IO46=0】 |
| 予備 | IO8, IO15, IO16, IO38〜IO42, IO47, IO48 | |

天板との JST 8 ピン（v0 の案のまま）: +3V3、GND、EN（リセット。R79 1kΩ を通して EN から切り離す、11/19 チェック中 4）、LOCK ボタン、LED_LAN、LED_DMX、LED_LOCK、予備。

## 電源

- ESP32-S3 モジュールは外部電源から 0.5A 以上が要る【確】。Wi-Fi 送信のピークは 355mA（802.11b）【確】。W5500 は 100M リンクで約 128mA【未: データシートの要約経由】。
- 3.3V の LDO は rev A の MCP1826（1A）のままで足りる見込み【未: ADM2587E の分を含めた合計は回路図で計算する】。
- USB-C は CC 5.1k（5V シンク）のまま。PC の USB では電流が足りない場合があるので、運用は 1.5A 以上の USB 充電器を前提にする【未】。
- N16R8 の使用温度は −40〜65℃【確】。ケース内の温度に注意（消費電力は約 1.5〜2W の見込み【未】）。

## アンテナとケース

- アンテナ部はモジュールの上端 18 × 6mm（推奨ランド図 Figure 10）【確】。Espressif の設計ガイドは、アンテナ部を基板の外へ出し、給電点を基板の端に寄せるのを強く勧めている。出せないときはアンテナの両脇と下の基板を切り欠く。基板の真ん中に置いて四方をくり抜くのは不可。アンテナ近くの基板には GND のベタとビアを密に置く【確: ESP32-S3 ハードウェア設計ガイド PCB レイアウト】。
- **ケースに効く点**: 同じガイドは、ケースの中でアンテナの周り全方向に 15mm 以上の空きを勧めている【確】。v0 のケース（外形の目安 84 × 88 × 45mm、本体とケースの隙間は数 mm）ではこれが取れないので、後ろ側の空きを 15mm 以上に広げる（外形が奥に 10mm 余り伸びる見込み）か、アンテナ部を後ろの側板の切り欠きから少し出すなどの工夫が要る。ケースの寸法はこの点で見直す。
- **2026-11-19 作者の決定**: アンテナのある後ろ側だけケースを 10〜15mm 奥に伸ばし、アンテナの周りに 15mm 以上の空きを取る（アンテナ部は基板の後ろの辺から外へ出す）。天板・側板の組み方は v0 のまま。
- コネクタ（USB-C・RJ45・XLR）は前の辺、アンテナは後ろの辺にして離す。
- 後ろの側板と天板のアンテナ付近はベタの銅を入れない。金属のねじ・スペーサーをアンテナから離す。

## ファーム

- ESP-IDF に移す。今の app/（box_core・artnet・http/WebSocket・画面の差し替え）を使い、port/ に esp32s3 を足す。
- W5500 は ESP-IDF の Ethernet ドライバで扱える【確】。v5.x までは本体に esp_eth_mac_new_w5500() があり、v6.0 で esp-eth-drivers（ESP Component Registry）へ移った（移行ガイドの「Removed APIs」）。ESP32-S3 は内蔵 MAC が無く、SPI-Ethernet で使う【確: ESP32-S3 版の Ethernet ページ】。
- Wi-Fi は子機（会場の Wi-Fi）と親機（ODE が AP）を /setup で切り替える案。有線と Wi-Fi の両方で同じ画面・WebSocket を出す。
- DMX は UART1 で 250kbps、ブレークとマーク・アフター・ブレークを UART で作る。
- 基板ができる前に、ESP32-S3 の開発ボードと W5500 の評価ボードで試せる（購入は延期中なので、手元にあれば）。

## RJ45 まわり（W5500 の参考回路を画像で確かめた、2026-11-19）

WIZnet の参考回路（W5500-Ref-RJ45WithMag、J1B1211CCD）【確: 図を画像で照合】:
- 送信: TXP → TD+、TXN → TD−（ダンピング抵抗 0Ω の場所あり、EMI 対策で 33Ω が良かったとの注記）。TXP・TXN それぞれ 49.9Ω 1% で 3V3A へ。TCT は 10Ω 1% で 3V3A から、22nF で GND。
- 受信: RXP・RXN（W5500 側）を 49.9Ω 1% × 2 でつなぎ、その中点を RCT へ、中点は 10nF で GND。そのあと 6.8nF で RD+・RD− へ（交流結合）。RX の終端は 3.3V につながない。（2026-11-19 訂正: 最初は終端をトランス側と書いていた。別スレッドのチェック中 2 で図と違うと分かり直した）
- 3V3D と 3V3A はフェライトビーズ（120Ω 級、HH-1M1608-121JT）で分ける。AVDD に 0.1µF × 6 ＋ 10µF。1V2O に 10nF、TOCAP に 4.7µF。水晶 25MHz に 18pF × 2 と 1MΩ。EXRES1 は 12.4kΩ 1%。LED は LINKLED・ACTLED に 330Ω。
- RJ45 の GHs_GND（75Ω 終端の共通点）と外殻は CGND、1nF 2kV で GND と結ぶ。

rev A の RJMG1BD3B8K1ANR も TCT（R4）と RCT（R5）が別のピンで、75Ω × 4 の共通点（R8）がある【プ: rev A のネットリストと sACN ノードの回路図レビュー】。ピンの並びは参考回路の J1B1211CCD と同じ考えなので、**RJMG のまま上の結線で使える見込み**。ただし RJMG のトランスの巻数比（1CT:1CT）とインダクタンス（W5500 は 1:1・350µH と案内【未: 要約経由】）は、Amphenol の図面が作業環境から読めず未確認（cdn.amphenol-cs.com が許可にない）。

## 要確認（回路図の前に）

1. RJMG1BD3B8K1ANR のトランスの仕様（巻数比・インダクタンス）。Amphenol の図面を読む。
2. 3.3V の合計電流と LDO の発熱（ADM2587E の分を含めて回路図で計算）。
3. ~~ケースの寸法~~ → 後ろを 10〜15mm 伸ばすに決定（11/19）。

## 部品（新しく要るもの、入手）

| 部品 | 候補 | 入手 |
|---|---|---|
| ESP32-S3-WROOM-1-N16R8 | 秋月 117256 ¥800 | 在庫あり（11/19） |
| W5500 | LCSC C32843 | 在庫 29,164、$2.57（11/19）。秋月なし、マルツ・Digi-Key は未確認 |
| 25MHz 水晶（18pF） | rev A の Y2 と同じ型が使えるか確かめる | 未 |
| 12.4kΩ 1% | rev A は 12.1k（LAN8742A 用）なので別に要る | 未 |
| RJ45 | rev A と同じ RJMG1BD3B8K1ANR を使う見込み（トランスの仕様は要確認） | rev A で Digi-Key から購入済みの型 |

外すもの: STM32F407VGT6、LAN8742A、24AA02E48、J3（SWD）、JP1、Y1（STM32 の水晶）。

## 次の工程

1. 要確認の 1〜3 を確かめる
2. 回路図（docker の kicad、rev A の生成スクリプトを流用）、ERC
3. 別スレッドで回路図のチェック
4. 配置（アンテナを後ろの辺）・配線・DRC → 別スレッドで PCB のチェック
5. ファームの移植（開発ボードで先に始められる）

## 出典

- ESP32-S3-WROOM-1 & WROOM-1U データシート v1.2（秋月の商品ページから）: https://akizukidenshi.com/goodsaffix/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf （表 3 ピン定義と注 b、表 4・6 起動ピン、表 10 0.5A、表 12 ピーク電流、図 7 周辺回路と EN の RC、型番表の温度）
- W5500 データシート v1.0.5: https://www.mouser.com/datasheet/2/443/Wiznet_W5500_DS_1%200%205-1212109.pdf （ピン表、SPI モード 0／3・80MHz、1V2O 10nF、EXRES1 12.4k、RSTn 500µs）
- WIZnet W5500 参考回路: https://docs.wiznet.io/Product/Chip/Ethernet/W5500/ref-schematic と https://docs.wiznet.io/img/products/w5500/w5500_sch_v110_use_mag_.pdf （2026-11-19 に図を画像で照合）
- ESP-IDF Ethernet（ESP32-S3）: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_eth.html 、v6.0 移行ガイド（networking）
- ESP32-S3 ハードウェア設計ガイド PCB レイアウト: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html
- rev A: hardware/revA/ode_main/README.md、部品リスト_revA.md
