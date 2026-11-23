# ODE-DIY の WebSocket とロックの仕様 v1.1（miseru ↔ 箱）

ブラウザ（miseru）と箱のあいだの取り決め。ファームの `firmware/app/box_core.c`・`http.c` はこれに従う。

> **ファーム v0.3.6 との違い**: (1) `/setup` にネットワーク・sACN・許可リストの欄は無い（`POST /api/settings` では変えられる）。DHCP への切り替えも `POST /api/settings`（`dhcp=1`）で行う。ボタンでの初期化で IP は 192.168.1.223 に戻る。(2) PIN の変更と画面の差し替えは LOCK ボタン（SW2）を 3 秒押してから 10 分の間だけ受け、画面の上限は約 384KB。くわしくは [firmware/README.md](../firmware/README.md)。

## 結論

- ブラウザは **512 バイトの DMX フレームをバイナリで送るだけ**。照明の計算（色、明るさ、タイムライン）はすべてブラウザ側の miseru が行う。
- 箱は **ロックを持つ 1 つの送り手** の値だけを DMX に出す。送り手は WebSocket の接続（クライアント ID 単位）か、Art-Net の送信元 IP。
- 制御のやり取りは短い JSON テキスト。

## 接続

- HTTP: `http://<箱の IP>/` で miseru の画面を返す。中身は miseru の `npm run build:box` で作る `dist/box`（index.html、`assets/index-<ハッシュ>.js`（gzip 53.4kB）、`.css`（2.2kB）。参照は相対パス `./assets/…`、合計 gzip で約 56kB）。
- **知らないパスには index.html を返す**（SPA の fallback）。先生用の画面は同じページの中にあるので `/admin` は要らない。
- js は `application/javascript`、css は `text/css` の Content-Type を付ける。gzip 済みのまま `Content-Encoding: gzip` で返してよい。
- **`GET /api/dmx`**（読み取り専用）: いま出している値を JSON で返す。`{"name":"ODE-DIY","holder":{"kind":"ws"}|{"kind":"artnet","ip":"…"}|{"kind":"sacn","ip":"…"}|null,"show_mode":false,"max_clients":30,"output":[512 個の数]}`（`max_clients` は v1、`name` と `sacn` は v1.1 で追加）。受け入れ試験と故障調べに使う。
- WebSocket: `ws://<箱の IP>/ws`。同時接続は **30** まで（2026-11-10 の実機の box:check で確定）。上限 + 1 本目は close code 1013 で断る。上限は `status` と `GET /api/dmx` の `max_clients` で知らせる。miseru 側では接続数を制限しない。
- IP アドレスの初期値は `192.168.1.223`（固定）。DHCP は管理画面で選べる。押しボタンを押したまま電源を入れると、IP と PIN を初期値に戻す。
- 管理画面（/setup）から dist/box を選んで画面を差し替えられる（ファーム v0.2.0）。gzip 後で合計 120kB まで。miseru の新しい版を入れるのにファームの書き込みは要らない。
- **`GET /api/settings`**: PIN 以外の設定の JSON。`name`（箱の名前）を含む。v0.2.0 で `ui`（`"builtin"` / `"uploaded"`）、`ui_size`、`ui_max` が増えた。miseru は箱の名前を `status` から読むので、ここは管理用。
- 認証は無し（LAN 内）。先生の操作だけ PIN を要る。

## ブラウザ → 箱

### バイナリ（DMX フレーム）

| バイト | 中身 |
|---|---|
| 0 | 種類。`0x01` = DMX フレーム |
| 1 | ポート番号（0 始まり。v0 は 0 のみ） |
| 2〜513 | スロット 1〜512 の値。512 未満で切れていたら残りは 0 |

- ロックを持つ接続のフレームだけを使う。ほかは黙って捨てる。
- miseru は値が変わらなくても **少なくとも 1 秒に 1 回** 送り直す（変化中は 30〜40fps）。

### テキスト（JSON）

| メッセージ | 意味 |
|---|---|
| `{"t":"hello","id":"<ランダム 16 文字>","app":"miseru","v":0}` | 接続直後に必ず送る。`id` はタブごとに作り sessionStorage に保存。再接続で同じ `id` なら同じ送り手として扱う |
| `{"t":"claim"}` | ロックを求める。空いていれば取れる |
| `{"t":"release"}` | 「おしまい」。待たずに全消灯してロックを外す（ロック中の本人のみ有効） |
| `{"t":"pin","pin":"1234"}` | 先生として認証。成功すればこの接続は先生扱い |
| `{"t":"force_release"}` | 先生のみ。いまのロックを外して全消灯 |
| `{"t":"show_mode","on":true}` | 先生のみ。公演モードの入り切り |
| `{"t":"ping"}` | 生存確認。フレームを送っていない間の保険 |

## 箱 → ブラウザ（JSON）

| メッセージ | いつ |
|---|---|
| `{"t":"status","name":"ODE-DIY","holder":{"kind":"ws","you":true}\|{"kind":"artnet","ip":"192.168.1.31"}\|{"kind":"sacn","ip":"192.168.1.31"}\|null,"show_mode":false,"teacher":false,"max_clients":30}` | 接続直後、変化したとき、1 秒ごと |
| `{"t":"denied","reason":"busy"}` | claim が通らなかったとき。理由は下の表 |
| `{"t":"pin","ok":true}` | pin の結果 |

- `name` は箱の名前（/setup の「名前」、初期値 `ODE-DIY`、ArtPollReply の短い名前と同じ）。miseru は画面に箱の名前と IP を出すのに使う。名前が無い古い箱では IP だけを出す。
- `denied` の理由:

| reason | いつ | miseru の表示（案） |
|---|---|---|
| `no_hello` | hello の前に claim した | （ふつうは起きない） |
| `busy` | ほかの送り手がロックを持っている | いま ほかの人が つかっています |
| `not_allowed` | 許可リストが入っていて、この機器の IP が無い（v0.2.0） | この機器は 箱に 許可されていません |

## ロックの規則

1. ロックが空いているとき、最初に `claim` した接続か、最初に ArtDmx を送ってきた IP がロックを取る。
2. ロック中の送り手から **5 秒** フレームも ping も届かなければ、全スロット 0 を出してロックを外す。WebSocket が切れた場合も、すぐ外さず 5 秒待つ（同じ `id` で再接続すれば続けられる）。
3. `release`、先生の `force_release`、**箱の押しボタン** は、待たずに全スロット 0 → ロック解除。
4. **公演モード**中は 2 の時間切れでは外さない（最後の値を出し続ける）。外せるのは `force_release` とボタンだけ。
5. ロックが外れたあと、次の送り手が来るまでは全スロット 0 を出し続ける。
6. 公演モードの状態と PIN はフラッシュに保存し、電源を入れ直しても残す。起動直後はロック無し・全消灯から始める。

## 許可リスト（ファーム v0.2.0）

- /setup で IP を 8 個まで入れられる。初期は切（空なら誰でも使える）。
- 入れると、リストに無い機器の `claim` に `{"t":"denied","reason":"not_allowed"}` を返し、その機器からの Art-Net・sACN も無視する。画面を開いて状態を見ることはできる。

## Art-Net

- ArtDmx の Net 0 / Sub-Net 0 / Universe 0 をポート 1 に出す（今の ODE Mk2 の設定に合わせる。現地で確認して必要なら直す）。
- ArtPoll に ArtPollReply を返す（Luminair や QLC+ が箱を見つけられるように）。
- 送信元 IP ごとにロックの規則 1〜5 を当てる。Art-Net の送り手には「使用中」を知らせる手段がないので、捨てるだけ。

## sACN（E1.31、ファーム v0.2.0）

- ユニバース 1（/setup で変えられる）を受ける。ロックの規則は Art-Net と同じ（送信元 IP ごと、5 秒で時間切れ）。持ち主は `{"kind":"sacn","ip":"…"}`。
- Stream_Terminated（options の 0x40）が届いたら、その送り手のロックを待たずに外して全消灯する。
- miseru は `kind` が `artnet` でも `sacn` でも「別の機材が 動かしています」と同じ扱いにする。

## miseru 側の実装（2026-10-25 済み）

miseru でこの仕様の送り手と偽の箱を作った。ファームの受け入れ試験の手本に使える。

- `src/box/protocol.ts`: フレーム（514 バイト）と JSON の形。
- `src/box/core.ts`: ロックの規則 1〜6 を時計に依存しない形で書いたもの（テスト 18 件）。ファームのロジックはこれを写すのが早い。
- `src/box/sim.ts`: 偽の箱。`npm run box:sim -- --port 8081 --pin 1234 --dir dist/box --artnet-in`。v1.1 で `--name`、`--allow`、`--sacn-in` を足した。出している値は `GET /api/dmx` で見られる。上限を超えた接続は close code 1013 で断る（箱も同じにしてほしい）。上限は `--max-clients`（既定 8）。
- 偽の箱は ArtPollReply を返さないが、**箱では必要**（Luminair と QLC+ のため）。
- 画面の振る舞い（参考）: 接続したら自動で claim。denied や外された場合は自動で取り直さず、利用者が「つかう」ボタンで claim する。ロック中は画面スリープを止める。初期状態でも 512 スロット全部を送る。

## 受け入れ試験

miseru に `npm run box:check -- --host <箱の IP> --pin <PIN>` を作った。HTTP 配信、ロックの規則 1〜4、接続数の上限の 12 項目を、ネットワークの外から確かめる（約 30 秒）。偽の箱では 12 項目すべて通る。ファームができたら、まずこれを当てて結果を返してほしい。

v1.1で 2 項目を足して 14 項目にした。「箱の名前を status と GET /api/dmx で知らせる」と「sACN でロックを取り、Stream_Terminated で全消灯」。sACN はユニキャストで箱の 5568 番に送る（`--sacn-port`、`--sacn-universe` で変えられる）。**名前の項目は、ファームが `name` を返すまで通らない。**

## 後回し（v1 以降）

- 公演データを箱に入れて箱が再生する機能（miseru のタイムラインを箱へ送る形式は別に決める）。
- （許可リストと sACN の受信はファーム v0.2.0 で入ったので、上に移した）

