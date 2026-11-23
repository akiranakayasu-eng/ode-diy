# ode_main ファームウェア v0.3.0（Art-Net・sACN 受信 → DMX 出力）

自作 ODE（ode_main rev A、STM32F407VGT6 + LAN8742A + ADM2587E）のファーム。[WebSocket とロックの仕様](../docs/websocket-spec.md)どおりに動く。

- **書き込むファイル: `make` で作る `build/ode_main.hex`**（または `build/ode_main.bin` を 0x08000000 に）。ビルド済みのファイルはリポジトリに入れていない（`apt-get install gcc-arm-none-eabi` などで arm-none-eabi-gcc を入れて `make`）
- 状態（2026-11-23）: **v0.3.0 は試験版（Linux）だけで確かめた。実機は未確認。** 箱の実機は v0.2.0（11/20 の控え）。
- v0.3.0 の変更（2026-11-23）:
  - 画面の差し替えの置き場を 128KB → **384KB**（セクタ 8〜10、0x08080000〜0x080DFFFF、中身の上限 393,200 バイト）。ファームは 512KB まで（セクタ 0〜7）。消去は書き込みに合わせて 1 セクタずつ。
  - **/setup は PIN の変更だけ**。ネットワーク・Art-Net・sACN・名前・許可リストの欄は外した（値はそのまま。`POST /api/settings` では今も変えられる）。IP を変える方法はボタンでの初期化（192.168.1.223 と PIN 1234 に戻す）だけ（2026-11-23 作者の決定）。PIN だけを変えたときは再起動しない。保存の文は青字。
  - **画面の差し替え・内蔵の画面に戻す・ファーム更新モードは、本体ボタン（SW2）を 3 秒押し続けてから 10 分の間だけ**受ける（LED 2 つが 3 回点滅）。長押しでは照明は消えない。短押しのロック解除と全消灯は離した瞬間に起きる（2026-11-23 作者の決定）。**現地の人への一言: 照明を消したいときはボタンを短く押してすぐ離す。押し続けている間は消えない。**差し替えと戻すは PIN が要らない。ファーム更新モードは PIN も要る。窓が閉じているときは `403 {"ok":false,"error":"button"}`。
  - `GET /api/settings` に `ui_open`（窓の残り秒、閉じていれば 0）を足した。`POST /api/ui` は `?pin=` が無くても受ける（付いていても見ない）。
  - v0.2.x から書き換えた直後は、置き場の場所が変わるので内蔵の画面で動く。差し替えた画面は 1 回アップロードし直す。設定と PIN はそのまま。
- 前の版の状態（2026-11-10）:
  - v0.1.0 は実機で確認済み（Ethernet、画面、WebSocket のロック、DMX 出力、Art-Net、box:check 12 件）。
  - v0.2.0 で画面の差し替え・sACN・許可リストを足した。実機で確認済み（2026-11-10 23:10）: 画面の差し替え、sACN マルチキャスト（`tools/sacn_test.py`）、許可リスト、設定のフラッシュ保存（再起動後も残る）、EEPROM の MAC。

## できること

| 機能 | 内容 |
|---|---|
| Art-Net 4 | ArtDmx の Port-Address 0（Net 0 / Sub-Net 0 / Universe 0）を DMX ポート 1 へ。ArtPoll に ArtPollReply（名前 ODE-DIY）を返す。宛先 IP を問わず UDP 6454 を受ける（2.x / 10.x のブロードキャストも可） |
| sACN（E1.31） | v0.2.0。ユニバース 1（/setup で 1〜63999）を DMX ポート 1 へ。UDP 5568 のユニキャストとマルチキャスト（239.255.0.1 などに IGMP で参加）。プレビューは無視、Stream_Terminated でロック解除（公演モード中は残す）。/setup で切ることもできる。ロックの持ち主は `kind:"sacn"` |
| 許可リスト | v0.2.0。/setup で IP を 8 個まで。入れると、そこに無い機器は Art-Net・sACN を無視し、画面からのロックも `{"t":"denied","reason":"not_allowed"}` で断る（画面を開くことと見ることはできる）。初期は切 |
| 画面の差し替え | /setup で miseru の dist/box フォルダを選んでアップロード（ブラウザで gzip にして送る、合計 384KB まで、フラッシュのセクタ 8〜10）。v0.3.0 から本体ボタンを 3 秒押してから 10 分の間だけ、PIN なし。「内蔵の画面に戻す」で元に戻る。壊れた書き込みは使わずに内蔵の画面で動く |
| DMX 出力 | PE0 → U7 → U11 ADM2587E。BREAK 176µs、MAB 16µs、512 スロット、約 44 フレーム/秒、連続送出。PE1（ポート 2、未実装）にも同じ値を出す |
| 画面 | `http://192.168.1.223/` で miseru の画面（`npm run build:box` の dist/box を gzip で内蔵、56KB）。知らないパスは index.html |
| WebSocket | `/ws`。仕様 v1 のとおり（hello / claim / release / pin / force_release / show_mode / ping、status は接続直後・変化時・1 秒ごと）。同時接続の上限 30、31 本目は close 1013 |
| 送信元ロック | 規則 1〜6（miseru の core.ts を C に写した）。5 秒で時間切れ、公演モード、先生の PIN |
| `GET /api/dmx` | `{"holder":…,"show_mode":…,"max_clients":30,"output":[512 個]}` |
| `GET /api/settings` | 設定（IP など、sACN、許可リスト、`ui`（`builtin` か `uploaded`）、`ui_size`、`ui_max`、`ui_open`（v0.3.0、差し替えの窓の残り秒））。PIN は返さない |
| `POST /api/ui` / `POST /api/ui/reset` | 画面の書き込み（/setup が使う形式）と内蔵の画面に戻す。v0.3.0 から PIN なし、差し替えの窓の間だけ |
| 設定の画面 | `http://<IP>/setup`。v0.3.0 から PIN の変更だけ（いまの PIN が要る。再起動しない）。ほかに画面の差し替えとファーム更新モード。ほかの設定は `POST /api/settings`（pin と変える項目、保存すると再起動）でだけ変えられる |
| ファームの更新（v0.2.1） | /setup の「ファーム更新モードにする」で USB DFU（STM32 の ROM のブートローダ）に入る。v0.3.0 から本体ボタンを 3 秒押してから 10 分の間だけ、PIN も要る。ケースを開けずに J1 の USB-C から書き込める。LAN と DMX は止まり、電源を入れ直すと元に戻る。`POST /api/dfu?pin=` |
| 押しボタン（SW2 LOCK） | 短く押すとロック解除と全消灯（公演モード中でも。v0.3.0 から**離した瞬間**に起きる）。**3 秒押し続けると**（v0.3.0）画面の差し替えとファーム更新モードを 10 分受ける（LED 2 つが 3 回点滅、照明は消さない）。**押したまま電源を入れて 1.5 秒** で IP と PIN を初期値に戻す（LED 2 つが 5 回点滅） |
| LED | D5 LOCK = ロック中に点灯。D6 STAT = LAN リンクありで 1 秒ごとに点滅、リンクなしで速い点滅 |
| 番犬 | IWDG 約 4 秒 |
| 保存 | 設定と公演モードはフラッシュのセクタ 11（0x080E0000）に残る。v0.1.0 の設定は v0.2.0 で読み替えて引き継ぐ。差し替えた画面はセクタ 8〜10（0x08080000、v0.2.x はセクタ 10） |
| ログ | J4（1 GND、2 TX、3 RX）に 115200bps 8N1（3.3V）。起動時に版・MAC・PHY・IP・リンクを出す |

初期値: IP `192.168.1.223`、マスク `255.255.255.0`、ゲートウェイなし、固定 IP、PIN `1234`、Port-Address 0。MAC は U4 24AA02E48 の EUI-48（読めなければチップ ID から 02:0d:e0:… を作る）。

## 書き込み（STLINK-V3SET + STM32CubeProgrammer）

0. v0.1.0 から上書きしてよい（設定はそのまま引き継ぐ）。v0.1.0 は書き込み中に番犬が動いて失敗することがある。失敗したら Disconnect → Connect でもう一度（v0.2.0 からは書き込み中は番犬が止まる）。
1. 基板を USB-C で給電する（JP1 は開放）。STLINK-V3SET の CN1 → ARM10 ケーブル → J3（赤線を 1 番側）。立ち上げのときと同じつなぎ方。
2. STM32CubeProgrammer で ST-LINK、Connect。
3. 左の「Erasing & Programming」で File path に `ode_main.hex` を選ぶ。**「Full chip erase」はしない**（設定が消える。消えても初期値で起動するだけ）。「Verify programming」と「Run after programming」に印を付けて Start Programming。
4. 書き込みが終わると動き出す。D6 STAT が点滅すれば動いている。

## ケースを開けずに書き込む（v0.2.1 から、USB-C）

v0.2.1 を一度 ST-LINK で書き込んだあとは、次の手順で更新できる。

1. 箱の USB-C（J1）を Mac につなぐ（給電もこのケーブルで）。LAN もつないでおく。
2. （v0.3.0 から）本体ボタンを 3 秒押し続ける（LED 2 つが 3 回点滅）。10 分以内に `http://192.168.1.223/setup` の「ファームの更新」で PIN を入れ、「ファーム更新モードにする」→ 確認で OK。LAN の画面は使えなくなる（D6 も止まる）。
3. STM32CubeProgrammer の右上で接続方法を **ST-LINK から USB に変える**。Port の横の更新ボタンを押すと `USB1` が出るので Connect。
4. 「Erasing & Programming」で `ode_main.hex` を選び、「Verify programming」と「Run after programming」に印を付けて Start Programming。Full chip erase はしない。
5. 終わったら Disconnect し、USB-C を抜き差しして電源を入れ直す（Run after programming で動き出していればそのままでよい）。

更新モードに入れたが書き込みをやめたいときも、電源を入れ直せば元のファームで起動する。

## 動作の確かめ方（Mac から）

Mac の有線 LAN を 192.168.1.x（例 192.168.1.10、マスク 255.255.255.0）にして箱とつなぐ。

> 家の LAN やほかの機器が 192.168.1.x を使っているときは、箱を PC と LAN ケーブルで直結し、Wi-Fi を切るか、ほかの機器と番号が重ならないか確かめる。箱の IP はボタンでの初期化で 192.168.1.223 に戻る。

1. ブラウザで `http://192.168.1.223/` を開く → miseru の画面が出て、「照明を うごかしています」になる。D5 LOCK が点く。
2. DMX の出力: XLR（J11）に照明か DMX テスタをつなぎ、画面で明るさを変える。`http://192.168.1.223/api/dmx` で出している値も見られる。
3. 受け入れ試験: miseru のフォルダで `npm run box:check -- --host 192.168.1.223 --pin 1234`。12 件すべて通れば仕様どおり。仕様 v1.1 の box:check（14 項目）では、箱の名前（status と /api/dmx の `name`）の項目が通らない（v0.3.0 は `name` を `/api/settings` でだけ返す）。
4. Art-Net: QLC+ か Luminair の出力先を 192.168.1.223、Universe 0 にする。ArtPoll で ODE-DIY が見つかる。
5. sACN: QLC+ などで E1.31、ユニバース 1 をマルチキャストかユニキャスト（192.168.1.223）で出す。
6. 画面の差し替え: 本体ボタンを 3 秒押し続け（LED 2 つが 3 回点滅）、10 分以内に `http://192.168.1.223/setup` の「画面の差し替え」で miseru の dist/box フォルダを選んでアップロード。画面を開き直すと新しい画面になる。
7. 許可リスト（v0.3.0 から /setup に欄が無い）: `curl -X POST -d "pin=<PIN>&allow_on=1&allow=192.168.1.10" http://192.168.1.223/api/settings` で Mac の IP だけを入れて保存 → 別の機器から Art-Net を送っても出力が変わらないことを確かめる。
8. うまく動かないときは、USB シリアル変換（3.3V）を J4 につないで 115200bps でログを見る。

## ソースの構成

| 場所 | 中身 |
|---|---|
| `app/` | 機種に依らない部分。`box_core.c` ロック、`artnet.c`、`sacn.c`、`http.c` HTTP と WebSocket、`setup_page.h` 設定の画面、`ui.c` 差し替えた画面、`minijson.c`、`sha1.c`、`settings.c`、`assets_gen.c`（内蔵の miseru の画面） |
| `port/stm32/` | `main.c`、`board.c`（168MHz、GPIO、IWDG、UART）、`eth.c`（MAC と PHY、HAL なし）、`dmx.c`（TIM8 + DMA2 で GPIO へ）、`flash_settings.c`、`mac_eeprom.c`、リンカスクリプト |
| `port/host/` | Linux の TAP で動かす試験用（Linux で box:check を当てるため） |
| `port/common/lwipopts.h` | lwIP の設定（両方共通） |
| `vendor/` | lwIP（master 2026-11-08、版 2.2.2 系）、CMSIS、STM32F4 のヘッダ |

## ビルド

```
make                 # arm-none-eabi-gcc（Ubuntu の gcc-arm-none-eabi 13.2 で確認）→ build/ode_main.hex
make host            # Linux 用の試験版 build/ode_host
python3 tools/mkassets.py <miseru の dist/box> app/assets_gen.c   # 画面を入れ替えるとき
```

試験版の動かし方（root 権限の Linux）:

その PC の LAN が 192.168.1.0/24 のときは、tap0 と箱の IP を別の番号に替えて試す（`app/settings.c` の初期値）。

```
ip tuntap add dev tap0 mode tap && ip addr add 192.168.1.1/24 dev tap0 && ip link set tap0 up
./build/ode_host tap0      # 標準入力に b = ボタンを短く押す、l = 3 秒の長押し（差し替えの窓を開く）
npm run box:check -- --host 192.168.1.223 --pin 1234     # miseru で
```

## まだ無いもの

- DMX ポート 2（rev A は U8・U21 未実装。PE1 には同じ値を出している）
- 同時接続の上限 30 は v0.1.0 の実機で確認済み
