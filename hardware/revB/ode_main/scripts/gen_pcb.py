#!/usr/bin/env python3
"""ode_main rev B (ESP32-S3 + W5500) の基板を生成する (KiCad の python で実行。rev A の gen_pcb.py を元にした)。

  python3 scripts/gen_pcb.py --geom     配置と外形を docs/geom.json に出す (ルータ用)
  python3 scripts/route.py              0.25mm グリッドの A* 迷路ルータ (表裏 2 層だけ使う)
  python3 scripts/gen_pcb.py            docs/routes.json を流し込んで基板を保存

76 x 84mm 4 層 FR-4 1.6mm。上辺 (箱の前面) に左から USB-C J1、RJ45 J5、XLR3 J11 を並べる (rev A の左 76mm と同じ位置)。
下辺 (後ろ) に ESP32-S3-WROOM-1 (U1) を 180 度回して置き、アンテナ部 (6mm) を基板の外へ出す
(ESP32-S3 ハードウェア設計ガイド: アンテナは基板の外へ、給電点を端に寄せる)。
  F.Cu / B.Cu が信号、In1.Cu が GND ベタ、In2.Cu が +3V3 ベタ。+3V3A (W5500 のアナログ) は太い線。
右上はポート 1 の絶縁側の島 (rev A と同じ寸法・位置)。島の左右と下は 4 層ともトラック・ビア・ベタ禁止。
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
import pcbnew  # noqa: E402

NAME = os.path.basename(PROJ)
FPDIR = os.environ.get("KICAD_FPDIR", "/usr/share/kicad/footprints/")
GEOM = os.path.join(PROJ, "docs", "geom.json")
ROUTES = os.path.join(PROJ, "docs", "routes.json")
OUT = os.path.join(PROJ, NAME + ".kicad_pcb")

W, H = 76.0, 84.0
W_SIG, W_PWR = 0.2, 0.5
CLR, EDGE_CLR = 0.15, 0.5
VIA_D, VIA_DRILL = 0.5, 0.3
NPORT = 1
GND = "GND"
V33, V33A = "+3V3", "/+3V3A"
SHEET_CENTER = (148.5 - W / 2, 105.0 - H / 2)   # A4 横の中央へ

# ---- ポートの格子 (sacn_node_out8 と同じ寸法)
PITCH = 27.0
XK0 = 46.0                              # ポート 1 の列の左端
GAP = 7.5                               # 一次側 <-> 絶縁側、ポート間の銅の最短 (カスタム DRC ルール)
BAND = 7.75
YS = 47.0                               # Uk1 の中心 y = 帯の中心
BY0, BY1 = YS - BAND / 2, YS + BAND / 2   # 43.125 / 50.875
GX0 = XK0 - BAND / 2                    # 左の列 (一次側) の右端 = 縦の帯の左端 42.125
HOLES = [(3.5, 59.5), (W - 3.5, 58.0), (W - 3.5, H - 3.5), (49.5, H - 3.5)]   # 2 版: 左後ろ (アンテナ側) には置かない
U1_XY = (10.5, H - 6.75)                 # 2 版: 左後ろの角。モジュールの左端 x 0.75、180 度でアンテナの付け根 = 下辺


def col(k):
    return XK0 + PITCH * (k - 1)


def cx(k):
    return col(k) + 13.5


def island(k):
    return col(k) + BAND / 2, col(k) + PITCH - BAND / 2


def notch(k):
    return (cx(k) - 9.4, BY0, cx(k) - 6.6, BY1)


C09X = lambda k: cx(k) - 8.0    # noqa: E731


def iso_nets(k):
    return {"/%s_%d" % (b, k) for b in ("GND_ISO", "GND2_PWR", "VISO_OUT", "VISO_IN", "DMX_P", "DMX_N", "LEDA")}


GISO = {k: "/GND_ISO_%d" % k for k in range(1, NPORT + 1)}
G2 = {k: "/GND2_PWR_%d" % k for k in range(1, NPORT + 1)}
PLANES = (GND, V33) + tuple(GISO.values())
PWR_NETS = ["/VBUS", "/VBUS_F", "+5V", V33A] + ["/VISO_OUT_%d" % k for k in range(1, NPORT + 1)] \
    + ["/VISO_IN_%d" % k for k in range(1, NPORT + 1)] + list(G2.values())
NO_STITCH = {"C%d09" % k for k in range(1, NPORT + 1)}


# ---------------------------------------------------------------- ネットリスト
def sexp(text, i=0):
    out = []
    while i < len(text):
        c = text[i]
        if c == "(":
            sub, i = sexp(text, i + 1)
            out.append(sub)
        elif c == ")":
            return out, i + 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i + 1:j])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(text) and not text[j].isspace() and text[j] not in "()":
                j += 1
            out.append(text[i:j])
            i = j
    return out, i


def load_netlist():
    txt = open(os.path.join(PROJ, "netlist.net")).read()
    root, _ = sexp(txt, txt.index("(") + 1)

    def f(n, k):
        return [x for x in n if isinstance(x, list) and x and x[0] == k]

    def v(n, k):
        r = f(n, k)
        return r[0][1] if r and len(r[0]) > 1 else None

    comps = {}
    for c in f(f(root, "components")[0], "comp"):
        comps[v(c, "ref")] = (v(c, "value"), v(c, "footprint"))
    nets = {}
    for net in f(f(root, "nets")[0], "net"):
        name = v(net, "name")
        for nd in f(net, "node"):
            nets[(v(nd, "ref"), v(nd, "pin"))] = name
    return comps, nets


COMPS, NET = load_netlist()
DOMAIN = {}
for _k in range(1, NPORT + 1):
    for _n in iso_nets(_k):
        DOMAIN[_n] = _k


def domain(net):
    """'P' = 一次側 / 1, 2 = ポート k の絶縁側 / None = 未接続・NPTH"""
    if not net:
        return None
    return DOMAIN.get(net, "P")


# ---------------------------------------------------------------- 配置
# (x, y, rot[, side])。IC は中心、コネクタはパッド 1、2 端子部品は中心。side "B" は裏面。
# 2 端子部品の向き (表): rot 0 = 1 番が左、90 = 1 番が下、180 = 1 番が右、270 = 1 番が上

# (x, y, rot[, side])。IC は中心、コネクタは原点、2 端子部品は中心。side "B" は裏面。
# 2 端子部品の向き (表): rot 0 = 1 番が左、90 = 1 番が下、180 = 1 番が右、270 = 1 番が上
U3_AT = (29.0, 33.0)            # W5500。rot 270 で 1-12 番 (TX/RX) が上 (RJ45 側)、25-36 番 (水晶・SPI) が下 (U1 側)


def placement():
    P = {}
    # --- USB-C と電源 (左の列、上から下。rev A と同じ位置)
    P["J1"] = (8.5, 4.0, 180)
    P["U5"] = (6.5, 12.5, 0)            # USBLC6-2SC6
    P["R1"] = (3.5, 16.5, 90)           # CC1 5.1k
    P["R2"] = (9.5, 16.5, 90)           # CC2 5.1k
    P["F1"] = (6.0, 21.0, 0)            # PTC。U6 (発熱) から 35mm 離す
    P["C1"] = (6.0, 24.2, 180)          # 2 版: 1 番 (VBUS_F) を右 = F1.2 の真下
    P["Q1"] = (6.0, 27.8, 270)          # AO3401A
    P["C2"] = (3.0, 31.5, 90)
    P["R3"] = (9.0, 31.5, 90)
    P["C3"] = (6.0, 35.5, 0)            # 22u (+5V) 1210
    P["C4"] = (5.2, 41.5, 0)            # LDO 入力 (+5V ゾーンの中)
    P["U6"] = (7.0, 47.0, 0)            # MCP1826 SOT-223 (タブ = GND、F.Cu の GND ゾーンで放熱)
    P["C5"] = (3.2, 53.1, 270)          # 10u (+3V3) 1210、1 番 = 上 (+3V3 ゾーン)
    P["C6"] = (8.0, 55.0, 0)
    P["R29"] = (23.0, 55.0, 0)          # PWR LED
    P["D4"] = (27.0, 55.0, 180)
    # --- RJ45 と W5500 (rev A の RJ45 と同じ位置)
    P["J5"] = (32.5, 17.73, 180)
    P["R67"] = (15.5, 10.0, 270)        # LINK LED
    P["R68"] = (12.5, 12.0, 270)        # ACT LED
    P["R73"] = (15.0, 14.5, 270)        # CHASSIS - GND
    P["C61"] = (15.0, 19.0, 270)        # 1n/2kV
    ux, uy = U3_AT
    P["U3"] = (ux, uy, 270)
    # 受信・送信の終端 (U3 の上辺と RJ45 の間 y = 24-27)
    P["R69"] = (31.5, 24.8, 90)         # TXP 49.9 -> +3V3A
    P["R70"] = (33.7, 24.8, 90)         # TXN
    P["R75"] = (36.0, 24.8, 90)         # TCT 10R
    P["C62"] = (38.3, 24.8, 90)         # TCT 22n
    P["R71"] = (24.3, 24.8, 90)         # RXP 49.9 -> RCT
    P["R72"] = (26.5, 24.8, 90)         # RXN
    P["C63"] = (21.0, 26.0, 0)          # RXP -> RDP 6.8n
    P["C64"] = (21.0, 28.3, 0)          # RXN -> RDN
    P["C65"] = (17.5, 26.5, 90)         # RCT 10n
    P["R61"] = (28.8, 25.6, 90, "B")    # EXRES1 12.4k (10 番の裏)
    # アナログ電源と 1V2O / TOCAP (左辺 = 元の 13-24 番)
    P["FB2"] = (17.5, 37.0, 90)         # +3V3 -> +3V3A
    P["C66"] = (17.5, 32.0, 90)         # +3V3A 4.7u? (bulk)
    P["C55"] = (21.8, 30.5, 0)
    P["C56"] = (21.8, 32.7, 0)
    P["C57"] = (21.8, 34.9, 0)
    P["C53"] = (23.0, 35.6, 90, "B")    # 1V2O 10n (22 番の裏)
    P["C54"] = (25.2, 33.8, 90, "B")    # TOCAP 4.7u (20 番の裏)
    P["C58"] = (29.0, 30.6, 0, "B")
    P["C59"] = (29.0, 33.0, 0, "B")
    P["C60"] = (29.0, 35.4, 0, "B")
    # 水晶 (下辺の 30 / 31 番)
    P["Y2"] = (28.4, 44.5, 270)         # 1 番 (XI) = 左上、3 番 (XO 側) = 右下
    P["C51"] = (25.2, 43.6, 90)         # X25_IN 18p
    P["C52"] = (29.4, 48.6, 0)         # X25_OUT 18p
    P["R60"] = (29.9, 41.0, 0)          # 1M XI-XO
    P["R62"] = (31.6, 44.0, 90)         # XO 0R (31 番の下。32-36 番の引き出しは右に空ける)
    P["C67"] = (25.0, 39.4, 0)          # +3V3 (28 番)
    P["C68"] = (17.5, 46.5, 90)
    # SPI のプルアップと SCLK の直列 (下辺の右)
    P["R76"] = (32.5, 49.0, 90)         # SCLK 0R
    P["C69"] = (34.8, 49.0, 90)         # SCLK DNP
    P["R64"] = (37.5, 36.5, 90)         # RST pull-up
    P["R65"] = (40.0, 36.5, 90)         # INT pull-up
    P["R66"] = (37.1, 49.0, 90)         # CS pull-up
    # --- ポート 1 (rev A と同じ)
    c = cx(1)
    P["J11"] = (c - 4.0, 12.65, 90)
    P["J12"] = (c + 4.0, 24.0, 180)
    P["D11"] = (c + 1.0, 30.0, 0)
    P["FB102"] = (c + 6.5, 33.5, 180)
    P["R101"] = (c - 3.0, 35.5, 0)
    P["D12"] = (c + 1.0, 35.5, 180)
    P["FB101"] = (c + 5.0, 35.5, 180)
    P["C107"] = (c - 5.0, 39.0, 90)
    P["C108"] = (c - 7.2, 39.0, 90)
    P["C105"] = (c + 5.0, 39.0, 90)
    P["C106"] = (c + 7.4, 39.0, 90)
    P["C109"] = (C09X(1), YS, 270)
    P["U11"] = (c, YS, 90)
    P["C101"] = (c - 4.6, 55.0, 270)
    P["C102"] = (c - 7.0, 55.0, 270)
    P["C103"] = (c + 4.0, 55.0, 270)
    P["C104"] = (c + 6.4, 55.0, 270)
    # 3.3V -> 5V バッファ (U11 の一次側ピン列の下)
    P["R82"] = (50.5, 60.5, 90)         # TX 0R
    P["U7"] = (54.5, 60.5, 0)
    P["C71"] = (58.0, 60.5, 270)
    P["U9"] = (61.5, 60.5, 0)
    P["C73"] = (65.0, 60.5, 270)
    P["R78"] = (54.5, 64.0, 0)          # TX_M pull-up
    P["R74"] = (61.5, 64.0, 0)          # DE_M pull-down
    # --- ESP32-S3 (2 版: 左後ろの角。右辺 x 19.25 = 2-14 番、下辺 y 64.75 = 15-26 番、左辺 x 1.75 = 27-40 番)
    P["U1"] = (U1_XY[0], U1_XY[1], 180)
    P["C31"] = (23.5, 80.8, 180, "B")   # 22u 1210 (2 番 3V3 の近く、裏。1 番 = 左)
    P["C32"] = (23.0, 82.6, 0)
    P["C33"] = (23.0, 80.0, 0)          # EN 1u (3 番の横)
    P["R31"] = (27.0, 80.0, 0)          # EN 10k
    P["R79"] = (31.0, 80.0, 0)          # EN -> EN_PANEL 1k
    P["SW1"] = (41.5, 80.0, 0)          # RESET
    # USB (13 / 14 番の横)
    P["R4"] = (23.0, 66.0, 180)         # D+ 0R (2 = U1 側)
    P["R5"] = (23.0, 68.2, 180)         # D- 0R
    P["C76"] = (27.0, 66.0, 0)          # DNP
    P["C77"] = (27.0, 68.2, 0)
    P["R34"] = (23.0, 70.8, 0)          # STAT LED (11 番の横)
    P["D6"] = (27.0, 70.8, 180)
    # 天板 (4-7 番の横)
    P["J6"] = (31.5, 71.0, 0)           # JST PH 8P
    for k, ref in enumerate(("R83", "R84", "R85", "R86", "R87")):
        P[ref] = (21.3 + 3.2 * k, 76.5, 90)
    P["C78"] = (22.9, 76.5, 90, "B")    # BTN_LOCK_M 100n (R83 と R84 の間の裏)
    # BOOT (27 番 = 左辺) はモジュールの上、UART はモジュールの右
    P["SW3"] = (35.5, 57.0, 0)          # BOOT (モジュールの上は 15-26 番の引き出しに空ける)
    P["R32"] = (4.0, 69.0, 90, "B")     # BOOT pull-up (27 番の横、裏)
    P["J4"] = (22.0, 60.0, 90)          # UART 1x03
    P["R77"] = (25.0, 63.0, 0)          # UART TX 499R
    # CC の分圧はモジュールの下 (裏、38 / 39 番の横)
    P["R80"] = (8.0, 80.0, 0, "B")      # CC1 22k
    P["C74"] = (4.0, 80.0, 180, "B")      # CC1_ADC 100n
    P["R81"] = (8.0, 82.4, 0, "B")      # CC2 22k
    P["C75"] = (4.0, 82.4, 180, "B")      # CC2_ADC 100n
    return P


PLACE = placement()


# ---------------------------------------------------------------- 基板を組む
def load_fp(lib, name):
    d = os.path.join(PROJ, lib + ".pretty") if lib == NAME else FPDIR + lib + ".pretty"
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise SystemExit("footprint not found: %s:%s" % (lib, name))
    fp.SetFPID(pcbnew.LIB_ID(lib, name))   # FootprintLoad は名前だけになるので付け直す
    return fp


def thermal_vias_03(fp):
    """EP のサーマルビアが 0.2mm 穴だと JLCPCB で追加料金になる。その場で 0.3mm 穴 / φ0.5 にする (U1 の EP)。"""
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and abs(pcbnew.ToMM(p.GetDrillSize().x) - 0.2) < 1e-3:
            p.SetDrillSize(pcbnew.VECTOR2I_MM(0.3, 0.3))
            p.SetSize(pcbnew.VECTOR2I_MM(0.5, 0.5))


def build():
    missing = set(COMPS) - set(PLACE)
    extra = set(PLACE) - set(COMPS)
    assert not missing, ("配置の無い部品", sorted(missing))
    assert not extra, ("ネットリストに無い部品", sorted(extra))
    b = pcbnew.CreateEmptyBoard()
    b.GetDesignSettings().SetCopperLayerCount(4)
    for n in sorted({n for n in NET.values() if n}):
        b.Add(pcbnew.NETINFO_ITEM(b, n))
    nets = b.GetNetInfo().NetsByName()
    for ref in sorted(PLACE):
        x, y, rot = PLACE[ref][:3]
        side = PLACE[ref][3] if len(PLACE[ref]) > 3 else "F"
        value, fpid = COMPS[ref]
        lib, name = fpid.split(":")
        fp = load_fp(lib, name)
        fp.SetReference(ref)
        fp.SetValue(value)
        thermal_vias_03(fp)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            nm = NET.get((ref, pad.GetNumber()))
            if nm:
                pad.SetNet(nets[nm])
            # 内層ベタへの接続は直結 (スルーホールとビア付きの EP)
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and nm in PLANES:
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            # IC のピン列の GND_ISO / GND2_PWR は両隣に挟まれてスポークが 1 本しか立たない (starved_thermal)
            if ref.startswith("U") and nm in tuple(GISO.values()) + tuple(G2.values()) + (GND,):
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        b.Add(fp)
        if side == "B":                       # Flip は基板に入れてから (前だと落ちる)
            fp.Flip(pcbnew.VECTOR2I_MM(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for k, (x, y) in enumerate(HOLES):
        fp = load_fp("MountingHole", "MountingHole_3.2mm_M3")
        fp.SetReference("H%d" % (k + 1))
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM
                         | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        b.Add(fp)
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for p, q in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I_MM(*p))
        s.SetEnd(pcbnew.VECTOR2I_MM(*q))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        b.Add(s)
    return b, nets, pts


def pad_xy(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    raise KeyError((ref, num))


def c09_links(b):
    """Ck09 の両端を帯の外まで引いてビアで内層のベタへ落とす。(net, パッド中心, ビア中心)"""
    out = []
    for k in range(1, NPORT + 1):
        for num, net, vy in (("1", GISO[k], BY0 - 0.9), ("2", GND, BY1 + 0.9)):
            px, py = pad_xy(b, "C%d09" % k, num)
            out.append((net, (px, py), (px, vy)))
    return out


G2_VY = 40.75     # GND2_PWR の 14 番 -> 11 番側へ渡る B.Cu の線の y (sacn_node_out8 と同じ)


def g2_routes(k):
    """GND2_PWR_k は手で引く (sacn_node_out8 と同じ)。戻り値 [(net, [点], 層, 幅)], [(net, ビア)]"""
    c, n = cx(k), G2[k]
    p14, p11 = (c + 1.905, YS - 4.65), (c + 5.715, YS - 4.65)
    v1, v2 = (c + 1.905, G2_VY), (c + 8.8, G2_VY)
    yc = 39.0 - 1.038
    fb = (c + 6.5 + 1.15, 33.5)
    segs = [(n, [p14, v1], pcbnew.F_Cu, W_PWR),
            (n, [v1, v2], pcbnew.B_Cu, W_PWR),
            (n, [v2, (v2[0], yc), (c + 5.0, yc)], pcbnew.F_Cu, W_PWR),
            (n, [(v2[0], yc), (v2[0], fb[1]), fb], pcbnew.F_Cu, W_PWR),
            (n, [p11, (v2[0], p11[1]), v2], pcbnew.F_Cu, W_PWR)]
    return segs, [(n, v1), (n, v2)]


# 2 版: 5V の主経路は手で太く引く (PCB 1 版チェック 中 2)。[(net, [点], 幅)] すべて F.Cu
PWR_ROUTES = [
    ("/VBUS", [(6.05, 8.05), (6.05, 10.2)], 0.5),
    ("/VBUS", [(6.05, 10.2), (2.2, 10.2), (2.2, 21.0), (4.97, 21.0)], 0.8),
    ("/VBUS_F", [(7.03, 21.0), (7.04, 24.2)], 0.8),
    ("/VBUS_F", [(7.04, 24.2), (7.04, 25.55), (5.05, 25.55), (5.05, 26.86)], 0.6),
    ("+5V", [(6.0, 28.74), (6.0, 33.0)], 0.6),
    ("+5V", [(6.0, 33.0), (4.44, 33.0), (4.44, 35.5)], 0.8),
]
# LDO まわりの F.Cu ゾーン (PCB 1 版チェック 中 3 / 中 4)。(net, 矩形, 優先度)
F_ZONES = [
    ("+5V", (0.6, 34.0, 5.6, 45.7), 3),
    (V33, (0.6, 48.3, 5.6, 53.4), 3),
]
GND_LDO = [(0.6, 45.95), (6.2, 45.95), (6.2, 42.6), (16.0, 42.6), (16.0, 53.0), (6.2, 53.0),
           (6.2, 48.1), (0.6, 48.1)]
GND_LDO_RECTS = [(0.6, 45.95, 6.2, 48.1), (6.2, 42.6, 16.0, 53.0)]
V33_LDO_VIAS = [(1.25, 48.9), (1.25, 52.4), (5.25, 51.0), (5.25, 52.4), (3.2, 53.1)]
GND_LDO_VIAS = [(1.5, 47.0)] + [(x, 43.6 + 1.4 * j) for x in (12.3, 13.5, 14.7) for j in range(7)]


# 3 版: 1V2O を短く (PCB 2 版チェック 低 2)。22 番 -> 本体の内側のビア -> 裏の C53.1
V12_ROUTES = [("/1V2O", [(25.4, 34.75), (26.1, 34.75), (26.1, 35.9)], pcbnew.F_Cu, W_SIG),
              ("/1V2O", [(26.1, 35.9), (26.1, 36.64), (23.0, 36.64)], pcbnew.B_Cu, W_SIG)]
V12_VIAS = [("/1V2O", (26.1, 35.9))]
# 3 版: モジュールの下の裏の C74・C75 の GND (ベタの最小幅 0.5mm で裏のベタが届かなくなった)
CC_GND_ROUTES = [(GND, [(5.0375, 80.0), (5.0375, 82.4)], pcbnew.B_Cu, 0.4)]
CC_GND_VIAS = [(GND, (5.0375, 81.2))]


def zone_rects():
    """F.Cu ゾーンを配線器とスティッチから見た障害 (net, x0, y0, x1, y1)"""
    return [(n, *r) for n, r, _ in F_ZONES] + [(GND, *r) for r in GND_LDO_RECTS]


def hand_routes(b):
    out = []
    for k in range(1, NPORT + 1):
        out += g2_routes(k)[0]
    out += [(n, path, pcbnew.F_Cu, w) for n, path, w in PWR_ROUTES]
    out += V12_ROUTES + CC_GND_ROUTES
    return out


def hand_vias(b):
    out = []
    for k in range(1, NPORT + 1):
        out += g2_routes(k)[1]
    out += [(V33, p) for p in V33_LDO_VIAS] + [(GND, p) for p in GND_LDO_VIAS]
    out += V12_VIAS + CC_GND_VIAS
    return out


def primary_ok(x, y, r, m=0.3):
    """一次側 (L 字) の中か"""
    return x + r <= GX0 - m or y - r >= BY1 + m


def region_ok(net, x, y, r):
    """ビア (半径 r) を置いてよい所か: 一次側は L 字の中、絶縁側は自分の島の中"""
    d = domain(net)
    if d == "P":
        return primary_ok(x, y, r)
    x0, x1 = island(d)
    return x0 + 0.3 <= x - r and x + r <= x1 - 0.3 and y + r <= BY0 - 0.3


def rect_from_seg(a, b, w):
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 + w, y1 - y0 + w)


def fb_body(b, ref):
    fp = b.FindFootprintByReference(ref)
    bbs = [p.GetBoundingBox() for p in fp.Pads()]
    xs = sorted(pcbnew.ToMM(v) for bb in bbs for v in (bb.GetLeft(), bb.GetRight()))
    ys = sorted(pcbnew.ToMM(v) for bb in bbs for v in (bb.GetTop(), bb.GetBottom()))
    return xs[0], ys[0], xs[-1], ys[-1]


def stitches(b):
    """ベタのネット (GND / +3V3 / +3V3_ETH / GND_ISO_k) の SMD パッドからビアを出す (--geom と build で同じ結果)。
    戻り値 [(vx, vy, px, py, ref, num, net, 層)]。"""
    pads = []
    for fp in b.Footprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads.append((pad.GetNetname(), pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                         pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
    for net, path, _, w in hand_routes(b):
        for p, q in zip(path, path[1:]):
            cx_, cy_, ww, hh = rect_from_seg(p, q, w)
            pads.append((net, cx_ - ww / 2, cy_ - hh / 2, cx_ + ww / 2, cy_ + hh / 2))
    pads += zone_rects()
    for net, p, v in c09_links(b):
        r = VIA_D / 2
        pads.append((net, v[0] - r, v[1] - r, v[0] + r, v[1] + r))
        cx_, cy_, ww, hh = rect_from_seg(p, v, W_PWR)
        pads.append((net, cx_ - ww / 2, cy_ - hh / 2, cx_ + ww / 2, cy_ + hh / 2))
    out = [(vx, vy, vx, vy, "HAND", "via", net, "F") for net, (vx, vy) in hand_vias(b)]
    notches = [notch(k) for k in range(1, NPORT + 1)]
    bodies = [fb_body(b, "FB%d0%d" % (k, j)) for k in range(1, NPORT + 1) for j in (1, 2)]

    def ok(x, y, net, spacing=0.7):
        r = VIA_D / 2
        if not (EDGE_CLR + r <= x <= W - EDGE_CLR - r and EDGE_CLR + r <= y <= H - EDGE_CLR - r):
            return False
        if not region_ok(net, x, y, r):
            return False
        for hx, hy in HOLES:
            if math.hypot(x - hx, y - hy) < 3.6 + r:
                return False
        for nx0, ny0, nx1, ny1 in notches + bodies:
            if nx0 - r - 0.3 < x < nx1 + r + 0.3 and ny0 - r - 0.3 < y < ny1 + r + 0.3:
                return False
        for pn, x0, y0, x1, y1 in pads:
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
            d = math.hypot(dx, dy)
            if pn != net and d < r + CLR + 0.1:
                return False
            if pn == net and d < 0.05:
                return False
        return all(math.hypot(x - vx, y - vy) >= spacing for vx, vy, *_ in out)

    for fp in sorted(b.Footprints(), key=lambda f: f.GetReference()):
        if fp.GetReference() in NO_STITCH:
            continue
        c = fp.GetPosition()
        pth = {p.GetNumber() for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH}
        for pad in fp.Pads():
            net = pad.GetNetname()
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or net not in PLANES:
                continue
            if pad.GetNumber() in pth:
                continue                       # EP (サーマルビア付き) はそのビアで落ちる
            layer = "F" if pad.IsOnLayer(pcbnew.F_Cu) else "B"
            bb = pad.GetBoundingBox()
            hx, hy = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
            px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            ccx, ccy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            if any(o[2:4] == (px, py) and o[6] == net for o in out):
                continue                       # 同じ位置の同じネットのパッド (USB-C の A1 / B12 など) は 1 個で足りる
            if hy >= hx:
                dirs = [(0.0, 1.0 if py >= ccy else -1.0), (1.0, 0.0), (-1.0, 0.0),
                        (0.0, -1.0 if py >= ccy else 1.0)]
            else:
                dirs = [(1.0 if px >= ccx else -1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
                        (-1.0 if px >= ccx else 1.0, 0.0)]
            got = None
            for extra in (0.05, 0.4, 0.8, 1.2):
                for d in dirs:
                    ext = hy if d[1] else hx
                    off = ext + CLR + VIA_D / 2 + extra
                    x, y = round(px + d[0] * off, 4), round(py + d[1] * off, 4)
                    if ok(x, y, net):
                        got = (x, y)
                        break
                if got:
                    break
            if got:
                out.append((got[0], got[1], px, py, fp.GetReference(), pad.GetNumber(), net, layer))
            else:
                print("!! stitch なし", fp.GetReference(), pad.GetNumber(), net)

    # 島の格子スティッチ (4 層の GND_ISO をつなぐ)
    for k in range(1, NPORT + 1):
        x0, x1 = island(k)
        y = 2.0
        while y <= BY0 - 1.0:
            x = x0 + 1.0
            while x <= x1 - 1.0:
                if ok(x, y, GISO[k], 1.0):
                    out.append((x, y, x, y, "GRID", "g", GISO[k], "F"))
                x += 4.0
            y += 4.0
    return out


def band_rects():
    """横の帯 (切り欠きを除く)。左の列 (x < GX0) には帯が無い"""
    out, x = [], GX0
    for k in range(1, NPORT + 1):
        nx0, _, nx1, _ = notch(k)
        out.append([x, BY0, nx0, BY1])
        x = nx1
    out.append([x, BY0, W + 1.0, BY1])
    return out


def gap_rects():
    """縦の帯 (左の列と島 1 の間、島の間、島 2 の右)"""
    out, x = [], GX0
    for k in range(1, NPORT + 1):
        x0, x1 = island(k)
        out.append([x, -1.0, x0, BY0])
        x = x1
    out.append([x, -1.0, W + 1.0, BY0])
    return out


def keepouts():
    return band_rects() + gap_rects()


def soft_keepouts():
    """Uk1 の一次側ピン列の下は F.Cu の横断を嫌う (sacn_node_out8 と同じ)"""
    return [[cx(k) - 7.0, BY1, cx(k) + 7.0, 53.0, "F", 45] for k in range(1, NPORT + 1)]


def dump_geom(b, pts):
    pads = []
    for fp in b.Footprints():
        ref = fp.GetReference()
        seen = {}
        for pad in fp.Pads():
            num = pad.GetNumber()
            k = seen.get(num, 0)
            seen[num] = k + 1
            sz = pad.GetSize()
            pos = pad.GetPosition()
            thru = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            lay = ["F", "B"] if thru else (["F"] if pad.IsOnLayer(pcbnew.F_Cu) else ["B"])
            grow = 0.2 if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else 0.0
            rot = round(pad.GetOrientationDegrees(), 1)
            w, h = pcbnew.ToMM(sz.x) + grow, pcbnew.ToMM(sz.y) + grow
            if abs(rot % 180 - 90) < 1:
                w, h = h, w
                rot = 0.0
            pads.append(dict(ref=ref, pad="%s#%d" % (num, k), net=pad.GetNetname() or "",
                             x=round(pcbnew.ToMM(pos.x), 4), y=round(pcbnew.ToMM(pos.y), 4),
                             w=round(w, 4), h=round(h, 4), rot=rot, thru=bool(thru), layers=lay))
    for gi, (vx, vy, px, py, ref, num, net, layer) in enumerate(stitches(b)):
        pads.append(dict(ref=ref, pad="stitch%s#%d" % (num, gi), net=net, x=vx, y=vy, w=VIA_D, h=VIA_D,
                         rot=0.0, thru=True, layers=["F", "B"]))
        if (px, py) != (vx, vy):
            cx_, cy_, w, h = rect_from_seg((px, py), (vx, vy), W_SIG)
            pads.append(dict(ref=ref, pad="stitchtrk%s#%d" % (num, gi), net=net, x=cx_, y=cy_, w=w, h=h,
                             rot=0.0, thru=False, layers=[layer]))
    for k, (net, p, v) in enumerate(c09_links(b)):
        pads.append(dict(ref="C09", pad="link%d" % k, net=net, x=v[0], y=v[1], w=VIA_D, h=VIA_D,
                         rot=0.0, thru=True, layers=["F", "B"]))
        cx_, cy_, w, h = rect_from_seg(p, v, W_PWR)
        pads.append(dict(ref="C09", pad="linktrk%d" % k, net=net, x=cx_, y=cy_, w=w, h=h,
                         rot=0.0, thru=False, layers=["F"]))
    for j, (net, path, layer, w) in enumerate(hand_routes(b)):
        for k, (p, q) in enumerate(zip(path, path[1:])):
            cx_, cy_, ww, hh = rect_from_seg(p, q, w)
            pads.append(dict(ref="HAND", pad="%s%d_%d" % (net, j, k), net=net, x=cx_, y=cy_, w=ww, h=hh,
                             rot=0.0, thru=False, layers=["F" if layer == pcbnew.F_Cu else "B"]))
    for k, (net, x0, y0, x1, y1) in enumerate(zone_rects()):
        pads.append(dict(ref="ZONE", pad="z%d" % k, net=net, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                         w=x1 - x0, h=y1 - y0, rot=0.0, thru=False, layers=["F"]))
    for k, (net, (vx, vy)) in enumerate(hand_vias(b)):
        pads.append(dict(ref="HAND", pad="via%d" % k, net=net, x=vx, y=vy, w=VIA_D, h=VIA_D,
                         rot=0.0, thru=True, layers=["F", "B"]))
    g = dict(pads=pads, outline=[list(p) for p in pts], wide_nets=PWR_NETS, w_wide=W_PWR,
             w_sig=W_SIG, keepouts=keepouts(), soft_keepouts=soft_keepouts(),
             pour_nets=list(PLANES), skip_nets=[], route_groups=[], fixed_nets=list(G2.values()) + ["/1V2O"])
    os.makedirs(os.path.dirname(GEOM), exist_ok=True)
    json.dump(g, open(GEOM, "w"), indent=1)
    nn = {p["net"] for p in pads if p["net"] and p["net"] not in PLANES
          and not p["net"].startswith("unconnected-")}
    print("-> %s  パッド %d / 配線対象ネット %d" % (GEOM, len(pads), len(nn)))


def add_track(b, nets, a, c, w, layer, net):
    tr = pcbnew.PCB_TRACK(b)
    tr.SetStart(pcbnew.VECTOR2I_MM(*a))
    tr.SetEnd(pcbnew.VECTOR2I_MM(*c))
    tr.SetWidth(pcbnew.FromMM(w))
    tr.SetLayer(layer)
    tr.SetNet(nets[net])
    b.Add(tr)


def add_via(b, nets, p, net):
    via = pcbnew.PCB_VIA(b)
    via.SetPosition(pcbnew.VECTOR2I_MM(*p))
    via.SetWidth(pcbnew.FromMM(VIA_D))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL))
    via.SetNet(nets[net])
    b.Add(via)


def add_routes(b, nets):
    if not os.path.exists(ROUTES):
        return 0, 0
    r = json.load(open(ROUTES))
    lay = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    # 手で引いた線・ゾーンの中で閉じた配線器の切れ端 (両端とも同じネットの手の線の中) は捨てる
    own = [("F" if L == pcbnew.F_Cu else "B", n, *rect_from_seg(p, q, w)) for n, path, L, w in hand_routes(b)
           for p, q in zip(path, path[1:])]
    own += [("F", n, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0) for n, x0, y0, x1, y1 in zone_rects()]

    def inside(layer, net, x, y):
        return any(L == layer and n == net and abs(x - cx_) <= ww / 2 + 1e-3 and abs(y - cy_) <= hh / 2 + 1e-3
                   for L, n, cx_, cy_, ww, hh in own)
    for x1, y1, x2, y2, w, layer, net in r["tracks"]:
        if inside(layer, net, x1, y1) and inside(layer, net, x2, y2):
            continue
        add_track(b, nets, (x1, y1), (x2, y2), w, lay[layer], net)
    for x, y, d, drill, net in r["vias"]:
        add_via(b, nets, (x, y), net)
    return len(r["tracks"]), len(r["vias"])


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _zone(b, layer, poly, net=None, prio=0):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    if net is not None:
        z.SetNet(net)
    o = z.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetAssignedPriority(prio)
    b.Add(z)
    return z


def _zone_style(z):
    z.SetLocalClearance(pcbnew.FromMM(CLR))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    z.SetIsFilled(False)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)


CU4 = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)


def _rule_area(b, name, poly, tracks, vias, pour):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for layer in CU4:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(not tracks)
    z.SetDoNotAllowVias(not vias)
    z.SetDoNotAllowZoneFills(not pour)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    b.Add(z)


def g2_rect(k):
    c = cx(k)
    return (c + 4.0, 36.6, c + 9.3, BY0)


def add_zones(b, nets):
    m = EDGE_CLR
    prim = [(m, m), (GX0, m), (GX0, BY1), (W - m, BY1), (W - m, H - m), (m, H - m)]
    _zone_style(_zone(b, pcbnew.In1_Cu, prim, nets[GND], 0))
    _zone_style(_zone(b, pcbnew.In2_Cu, prim, nets[V33], 0))
    # 2 版: 外層の GND ベタ (PCB 1 版チェック 低 4) と LDO まわりのゾーン
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = _zone(b, layer, prim, nets[GND], 0)
        _zone_style(z)
        z.SetMinThickness(pcbnew.FromMM(0.5))   # 3 版チェック 低 1: 幅 0.3mm の細い帯 (ビアが打てない) を塗らない
    for n, r, prio in F_ZONES:
        z = _zone(b, pcbnew.F_Cu, _rect(*r), nets[n], prio)
        _zone_style(z)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z = _zone(b, pcbnew.F_Cu, GND_LDO, nets[GND], 2)
    _zone_style(z)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    for k in range(1, NPORT + 1):
        ix0, ix1 = island(k)
        for layer in CU4:
            _zone_style(_zone(b, layer, _rect(ix0, m, min(ix1, W - m), BY0), nets[GISO[k]], 0))
        _zone_style(_zone(b, pcbnew.F_Cu, _rect(*g2_rect(k)), nets[G2[k]], 2))
    for i, r in enumerate(band_rects()):
        _rule_area(b, "ISO_BAND_%d" % i, _rect(max(r[0], 0), r[1], min(r[2], W), r[3]), False, False, False)
    for i, r in enumerate(gap_rects()):
        _rule_area(b, "ISO_GAP_%d" % i, _rect(max(r[0], 0), 0, min(r[2], W), r[3]), False, False, False)
    for k in range(1, NPORT + 1):
        _rule_area(b, "NOTCH_%d" % k, _rect(*notch(k)), True, False, False)
        for ref in ("FB%d01" % k, "FB%d02" % k):
            fx0, fy0, fx1, fy1 = fb_body(b, ref)
            _rule_area(b, "NOPOUR_" + ref, _rect(fx0 - 0.3, fy0 - 0.3, fx1 + 0.3, fy1 + 0.3), True, True, False)


# ---------------------------------------------------------------- 参照記号 (artic8 と同じ方式)
REF_SIZE, REF_THICK, REF_CLR = 0.8, 0.15, 0.12
REF_OFFSETS = (0.12, 0.25, 0.4, 0.6, 0.85, 1.15, 1.5, 2.0, 2.6, 3.3)
REF_SHIFTS = (0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0, 2.6, -2.6)


def _box(bb, m=0.0):
    return (pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m,
            pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m)


def _hit(a, obs):
    return any(a[0] < o[2] and o[0] < a[2] and a[1] < o[3] and o[1] < a[3] for o in obs)


def place_refs(b, texts):
    lim = (0.4, 0.4, W - 0.4, H - 0.4)
    obs_side = {"F": list(texts), "B": []}        # 表裏で別々に (裏の部品の参照記号は裏のシルク)
    for fp in b.Footprints():
        side = "B" if fp.IsFlipped() else "F"
        for pad in fp.Pads():
            for L in ("F", "B"):
                if pad.IsOnLayer(pcbnew.F_Cu if L == "F" else pcbnew.B_Cu):
                    obs_side[L].append(_box(pad.GetBoundingBox(), REF_CLR + 0.05))
        for it in fp.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and hasattr(it, "GetShape"):
                obs_side[side].append(_box(it.GetBoundingBox(), REF_CLR))
    placed_side = {"F": [], "B": []}
    failed = []

    def area(f):
        q = _box(f.GetBoundingBox())
        return (q[2] - q[0]) * (q[3] - q[1])

    for fp in sorted(b.Footprints(), key=area):
        if fp.GetReference().startswith("H"):
            continue
        obs, placed = obs_side["B" if fp.IsFlipped() else "F"], placed_side["B" if fp.IsFlipped() else "F"]
        ref = fp.Reference()
        ref.SetVisible(True)
        ref.SetLayer(pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS)
        ref.SetTextSize(pcbnew.VECTOR2I_MM(REF_SIZE, REF_SIZE))
        ref.SetTextThickness(pcbnew.FromMM(REF_THICK))
        ref.SetKeepUpright(False)
        px0 = min(_box(p.GetBoundingBox())[0] for p in fp.Pads())
        py0 = min(_box(p.GetBoundingBox())[1] for p in fp.Pads())
        px1 = max(_box(p.GetBoundingBox())[2] for p in fp.Pads())
        py1 = max(_box(p.GetBoundingBox())[3] for p in fp.Pads())
        ccx, ccy = (px0 + px1) / 2, (py0 + py1) / 2
        best = None
        for d in REF_OFFSETS:
            for sh in REF_SHIFTS:
                tw = 0.7 * len(fp.GetReference()) / 2 + 0.1
                for ang, tx, ty in ((0, ccx + sh, py0 - d - 0.5), (0, ccx + sh, py1 + d + 0.5),
                                    (90, px0 - d - 0.5, ccy + sh), (90, px1 + d + 0.5, ccy + sh),
                                    (0, px1 + d + tw, ccy + sh), (0, px0 - d - tw, ccy + sh)):
                    ref.SetTextAngleDegrees(ang)
                    ref.SetPosition(pcbnew.VECTOR2I_MM(round(tx, 4), round(ty, 4)))
                    bb = _box(ref.GetBoundingBox())
                    if bb[0] < lim[0] or bb[1] < lim[1] or bb[2] > lim[2] or bb[3] > lim[3]:
                        continue
                    if _hit(bb, obs) or _hit(bb, placed):
                        continue
                    dist = math.hypot(tx - ccx, ty - ccy)
                    if best is None or dist < best[0]:
                        best = (dist, ang, tx, ty, bb)
            if best is not None:
                break
        if best is None:
            ref.SetVisible(False)
            failed.append(fp.GetReference())
            continue
        _, ang, tx, ty, bb = best
        ref.SetTextAngleDegrees(ang)
        ref.SetPosition(pcbnew.VECTOR2I_MM(round(tx, 4), round(ty, 4)))
        placed.append((bb[0] - REF_CLR, bb[1] - REF_CLR, bb[2] + REF_CLR, bb[3] + REF_CLR))
    return len(placed_side["F"]) + len(placed_side["B"]), failed


# ---------------------------------------------------------------- シルクの文字
def silk(b, s, x, y, size=0.8, ang=0, just=None, layer=pcbnew.F_SilkS):
    tx = pcbnew.PCB_TEXT(b)
    tx.SetText(s)
    tx.SetLayer(layer)
    tx.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    tx.SetTextThickness(pcbnew.FromMM(0.15))
    tx.SetTextAngleDegrees(ang)
    if layer == pcbnew.B_SilkS:
        tx.SetMirrored(True)
    if just is not None:
        tx.SetHorizJustify(just)
    tx.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    b.Add(tx)
    return _box(tx.GetBoundingBox(), REF_CLR)


def labels(b):
    out = []
    L = pcbnew.GR_TEXT_H_ALIGN_LEFT
    c = cx(1)
    out.append(silk(b, "DMX", c, 22.0, 1.0))
    for j, s in enumerate(("G", "D-", "D+")):
        out.append(silk(b, s, c + 4.0 - 2.5 * j, 27.6, 0.8))
    out.append(silk(b, "ISO", c + 1.0, 33.6, 0.8))
    out.append(silk(b, "ISO", 71.3, YS, 0.8, 90))
    out.append(silk(b, "USB-C 5V", 1.2, 14.0, 0.8, 90))
    out.append(silk(b, "ETH", 40.5, 12.0, 1.0, 90))
    out.append(silk(b, "PWR", 27.0, 53.4, 0.8))
    out.append(silk(b, "G T R", 24.54, 57.5, 0.8))
    out.append(silk(b, "BOOT", 35.5, 53.2, 0.8))
    out.append(silk(b, "RESET", 41.5, 75.6, 0.8))
    out.append(silk(b, "STAT", 27.0, 72.7, 0.8))
    out.append(silk(b, "ode_main B", 50.0, 70.0, 1.0, 0, L))
    out.append(silk(b, "DMX512 node", 50.0, 72.0, 0.8, 0, L))
    out.append(silk(b, "ANTENNA: back edge", 10.5, 63.1, 0.8))
    return out


def gnd_stitch(b, nets, off, pitch=1.5, spacing=5.0):
    """3 版 (PCB 2 版チェック 低 3): 塗ったあとで、F.Cu と B.Cu の両方の GND ベタの中に GND ビアを打つ。
    外層の細い切れ端が 1 本のビアだけでつながるのを防ぐ。"""
    zs = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == GND
          and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu)]
    polys = {L: [z.GetFilledPolysList(L) for z in zs if z.GetLayer() == L] for L in (pcbnew.F_Cu, pcbnew.B_Cu)}
    r = VIA_D / 2 + CLR + 0.05
    ring = [(r * math.cos(a * math.pi / 4), r * math.sin(a * math.pi / 4)) for a in range(8)] + [(0, 0)]
    ox, oy = off.x, off.y
    have = [(pcbnew.ToMM(v.GetPosition().x - ox), pcbnew.ToMM(v.GetPosition().y - oy))
            for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]
    gvias = [p for p, v in zip(have, [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T])
             if v.GetNetname() == GND]
    pads = []
    for fp in b.Footprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append((pcbnew.ToMM(bb.GetLeft() - ox), pcbnew.ToMM(bb.GetTop() - oy),
                         pcbnew.ToMM(bb.GetRight() - ox), pcbnew.ToMM(bb.GetBottom() - oy)))

    def filled(L, x, y):
        return any(ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x + dx) + ox, pcbnew.FromMM(y + dy) + oy))
                   for dx, dy in ring for ps in polys[L]) and all(
            any(ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x + dx) + ox, pcbnew.FromMM(y + dy) + oy))
                for ps in polys[L]) for dx, dy in ring)
    n = 0
    y = 1.5
    while y < H - 1.0:
        x = 1.5
        while x < W - 1.0:
            ok = (primary_ok(x, y, VIA_D / 2)
                  and all(math.hypot(x - hx, y - hy) >= 3.6 + r for hx, hy in HOLES)
                  and all(math.hypot(x - vx, y - vy) >= 0.9 for vx, vy in have)
                  and all(math.hypot(x - vx, y - vy) >= spacing for vx, vy in gvias)
                  and not any(x0 - r < x < x1 + r and y0 - r < y < y1 + r for x0, y0, x1, y1 in pads)
                  and filled(pcbnew.F_Cu, x, y) and filled(pcbnew.B_Cu, x, y))
            if ok:
                add_via(b, nets, (x + pcbnew.ToMM(ox), y + pcbnew.ToMM(oy)), GND)
                have.append((x, y))
                gvias.append((x, y))
                n += 1
            x += pitch
        y += pitch
    # 2 回目: ビアが 1 本以下の切れ端、長い (10mm 超) のにビアが 2 本以下の切れ端に細かい格子で足す
    segs = {L: [] for L in (pcbnew.F_Cu, pcbnew.B_Cu)}
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() in segs and t.GetNetname() != GND:
            segs[t.GetLayer()].append((pcbnew.ToMM(t.GetStart().x - ox), pcbnew.ToMM(t.GetStart().y - oy),
                                       pcbnew.ToMM(t.GetEnd().x - ox), pcbnew.ToMM(t.GetEnd().y - oy),
                                       pcbnew.ToMM(t.GetWidth()) / 2))

    def seg_d(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        u = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy or 1e-9)))
        return math.hypot(px - x1 - u * dx, py - y1 - u * dy)

    def clear_of_tracks(L, x, y):
        return all(seg_d(x, y, *sg[:4]) >= sg[4] + VIA_D / 2 + CLR for sg in segs[L])
    gp = []
    for f in b.Footprints():
        for p in f.Pads():
            if p.GetNetname() == GND:
                gp.append(p)
    n2 = 0
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        other = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
        for ps in polys[L]:
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                vs = [(x, y) for x, y in gvias
                      if o.PointInside(pcbnew.VECTOR2I(pcbnew.FromMM(x) + ox, pcbnew.FromMM(y) + oy))]
                npd = sum(1 for p in gp if p.IsOnLayer(L) and o.PointInside(p.GetPosition()))
                bb = o.BBox()
                span = max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
                need = max(2, int(span / 6.0) + 1)     # 長い切れ端は 6mm に 1 本以上
                if len(vs) + npd > 1 and not (span > 10 and len(vs) < need):
                    continue
                x0, y0 = pcbnew.ToMM(bb.GetX() - ox), pcbnew.ToMM(bb.GetY() - oy)
                x1, y1 = x0 + pcbnew.ToMM(bb.GetWidth()), y0 + pcbnew.ToMM(bb.GetHeight())
                y = y0
                while y <= y1:
                    x = x0
                    while x <= x1:
                        inside = all(o.PointInside(pcbnew.VECTOR2I(pcbnew.FromMM(x + dx) + ox,
                                                                   pcbnew.FromMM(y + dy) + oy)) for dx, dy in ring)
                        if (inside and primary_ok(x, y, VIA_D / 2)
                                and all(math.hypot(x - hx, y - hy) >= 3.6 + r for hx, hy in HOLES)
                                and all(math.hypot(x - vx, y - vy) >= 0.9 for vx, vy in have)
                                and all(math.hypot(x - vx, y - vy) >= 4.0 for vx, vy in vs)
                                and not any(a0 - r < x < a1 + r and b0 - r < y < b1 + r for a0, b0, a1, b1 in pads)
                                and (filled(other, x, y) or clear_of_tracks(other, x, y))):
                            add_via(b, nets, (x + pcbnew.ToMM(ox), y + pcbnew.ToMM(oy)), GND)
                            have.append((x, y))
                            vs.append((x, y))
                            gvias.append((x, y))
                            n2 += 1
                        x += 0.25
                    y += 0.25
    print("GND のつなぎビア", n, "+ 切れ端", n2)
    return n + n2


def write_pro():
    """b.Save() は .kicad_pro を既定値で上書きするので、設計ルールを後から書き戻す。"""
    p = os.path.join(PROJ, NAME + ".kicad_pro")
    d = json.load(open(p))
    for c in d["net_settings"]["classes"]:
        c["clearance"] = CLR
        c["track_width"] = W_SIG
        c["via_diameter"], c["via_drill"] = VIA_D, VIA_DRILL
    d["meta"]["filename"] = NAME + ".kicad_pro"
    rules = d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
    rules.update(min_clearance=CLR, min_track_width=0.15, min_via_diameter=0.45,
                 min_through_hole_diameter=0.3, min_copper_edge_clearance=EDGE_CLR)
    json.dump(d, open(p, "w"), indent=2)


def write_dru():
    """絶縁帯のカスタム DRC ルール (sacn_node_out8 と同じ): ポート k の絶縁側の銅と、それ以外の銅は 7.5mm 以上離す。
    例外は Uk1 と Ck09 と切り欠きの中の引き出し線だけ。"""
    rules = []
    for k in range(1, NPORT + 1):
        def iso(x):
            return "(" + " || ".join("%s.NetName == '%s'" % (x, n) for n in sorted(iso_nets(k))) + ")"
        cond = ("%s && !%s && B.NetName != '' "
                "&& !A.memberOfFootprint('U%d1') && !B.memberOfFootprint('U%d1') "
                "&& !A.memberOfFootprint('C%d09') && !B.memberOfFootprint('C%d09') "
                "&& !(A.Type == 'Track' && A.intersectsArea('NOTCH_%d')) "
                "&& !(B.Type == 'Track' && B.intersectsArea('NOTCH_%d'))"
                % (iso("A"), iso("B"), k, k, k, k, k, k))
        rules.append('(rule "isolation_gap_%d"\n\t(constraint clearance (min %.2fmm))\n\t(condition "%s"))\n'
                     % (k, GAP - 0.01, cond))
    txt = ('(version 1)\n\n'
           '# 絶縁帯: ポート k の絶縁側 (GND_ISO_k / DMX_k ...) と、それ以外の銅の間隔。gen_pcb.py が書く\n'
           + "\n".join(rules))
    open(os.path.join(PROJ, NAME + ".kicad_dru"), "w").write(txt)


def main():
    b, nets, pts = build()
    ds = b.GetDesignSettings()
    ds.m_TentViasFront = True
    ds.m_TentViasBack = True
    if "--geom" in sys.argv:
        dump_geom(b, pts)
        return
    nt, nv = add_routes(b, nets)
    ns = 0
    for vx, vy, px, py, ref, num, net, layer in stitches(b):
        if (px, py) != (vx, vy):
            add_track(b, nets, (px, py), (vx, vy), W_SIG, pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu, net)
        add_via(b, nets, (vx, vy), net)
        ns += 1
    for net, p, v in c09_links(b):
        add_track(b, nets, p, v, W_PWR, pcbnew.F_Cu, net)
        add_via(b, nets, v, net)
    for net, path, layer, w in hand_routes(b):
        for p, q in zip(path, path[1:]):
            add_track(b, nets, p, q, w, layer, net)
    # hand_vias は stitches() の戻り値に入っている (ここで足すと二重になる)
    texts = labels(b)
    n_ref, bad = place_refs(b, texts)
    add_zones(b, nets)
    off = pcbnew.VECTOR2I_MM(*SHEET_CENTER)
    for it in list(b.GetFootprints()) + list(b.GetTracks()) + list(b.Drawings()) + list(b.Zones()):
        it.Move(off)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    nst = gnd_stitch(b, nets, off)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(OUT)
    write_pro()
    write_dru()
    print("-> %s  トラック %d / ビア %d / スティッチ %d / 参照記号 %d%s"
          % (OUT, nt, nv, ns, n_ref, (" / 置けない %s" % bad) if bad else ""))


if __name__ == "__main__":
    main()
