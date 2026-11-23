#!/usr/bin/env python3
"""ode_top rev B (ode_main rev B の天板) の基板を生成する (KiCad 10 の python で実行、2026-11-23 PCB 1 版)。

  python3 scripts/gen_pcb.py

天板はケースの上の板そのもの (89.2 x 112.7、FR-4 1.6mm、2 層)。ケースの寸法は ../ode_main/case/case_model.py (v5)。
座標: 上から見た図で、前 (コネクタの面) が画面の下 (y = 112.7)。x はケースの x と同じ (前から見て右へ)。
本体 PCB (KiCad、前の辺が上) の点 (xm, ym) は、天板では (82.6 - xm, 108.6 - ym) (上から見たまま 180 度回る)。
  82.6 = 側板の外の張り出し 2.0 + 板 1.6 + すき間 3.0 + 本体の幅 76、108.6 = 天板の奥行き 112.7 - (2.0 + 1.6 + 0.5)
表 (F) に LED 4 つと抵抗、ボタン 2 つ。裏 (B) は J1 (JST PH 8P、本体 J6 の真上) だけ。
J1 は裏で、本体 J6 の n 番の真上に J1 の n 番 (並び・ネットとも J6 と同じ、n 番どうしのケーブル)。
  J1 は J6 を並びの軸のまわりに裏返した向き (裏に置いて 0 度)。ロックの側 (本体の広い側) は J6 と逆の前を向く。
配線は手で引く (ネット 6 本)。表と裏は GND ベタ。
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
import pcbnew  # noqa: E402

NAME = os.path.basename(PROJ)
FPDIR = os.environ.get("KICAD_FPDIR", "/usr/share/kicad/footprints/")
OUT = os.path.join(PROJ, NAME + ".kicad_pcb")

# ---- ケースの寸法 (case_model.py v5 と同じ値)
T = 1.6
MB_W, MB_D = 76.0, 84.0
GAP_F, GAP_S, GAP_B, OVH = 0.5, 3.0, 21.0, 2.0
W = MB_W + 2 * (GAP_S + T + OVH)                      # 89.2
H = MB_D + GAP_F + GAP_B + 2 * (T + OVH)              # 112.7
X0 = OVH + T + GAP_S                                  # 6.6
Y0 = OVH + T + GAP_F                                  # 4.1
TAB_W, TAB_N, SLOT_CLR = 10.0, 2, 0.2
CORNER_R = 2.0                                        # 板の角の丸み
MAIN_HOLES = [(3.5, 59.5), (72.5, 58.0), (72.5, 80.5), (49.5, 80.5)]   # 本体 PCB 4 版の M3 穴
MAIN_J6_PAD1 = (31.5, 71.0)                           # 本体 J6 の 1 番 (PCB 4 版)

W_SIG = 0.3
CLR, EDGE_CLR = 0.2, 0.5
VIA_D, VIA_DRILL = 0.6, 0.3
SHEET_CENTER = (148.5 - W / 2, 105.0 - H / 2)


def from_main(x, y):
    """本体 PCB の座標 → 天板の座標"""
    return (round(X0 + MB_W - x, 4), round(H - (Y0 + y), 4))


def case_to_top(x, y):
    """case_model.py の座標 (x 右・y 奥) → 天板の座標"""
    return (round(x, 4), round(H - y, 4))


HOLES = [from_main(x, y) for x, y in MAIN_HOLES]
J6_1 = from_main(*MAIN_J6_PAD1)                       # (51.1, 37.6)
J1_AT = J6_1                                          # J1 の 1 番 (原点) を J6 の 1 番の真上に


def tab_positions(a, b):
    L = b - a
    return [a + L * (i + 1) / (TAB_N + 1) for i in range(TAB_N)]


def slots():
    """側板のつめの穴 (中心 x, y, 向き 'x' = 横長 / 'y' = 縦長)。case_model.slots_for_plate と同じ位置"""
    WX0 = X0 - GAP_S - T
    WX1 = X0 + MB_W + GAP_S
    WY0 = Y0 - GAP_F - T
    WY1 = Y0 + MB_D + GAP_B
    out = []
    for cx in tab_positions(WX0 + T, WX1):
        out.append((*case_to_top(cx, WY0 + T / 2), "x"))
        out.append((*case_to_top(cx, WY1 + T / 2), "x"))
    for cy in tab_positions(WY0, WY1 + T):
        out.append((*case_to_top(WX0 + T / 2, cy), "y"))
        out.append((*case_to_top(WX1 + T / 2, cy), "y"))
    return out


SLOT_L, SLOT_W = TAB_W + SLOT_CLR, T + SLOT_CLR       # 10.2 x 1.8 の長方形が入る長円 (端は半径 0.9、全長 12.0)

# ---- 部品の配置 (x, y, rot, side)。2 端子部品: rot 270 = 1 番が上、90 = 1 番が下
LED_Y, R_Y, LBL_Y = 97.5, 93.0, 101.6
COLS = {"D3": 18.0, "D2": 30.0, "D4": 42.0, "D1": 80.0}      # 前から見て左から DMX / LAN / LOCK / … / PWR
RES = {"D1": "R1", "D2": "R2", "D3": "R3", "D4": "R4"}
SW_AT = {"SW1": (54.0, LED_Y), "SW2": (68.0, LED_Y)}


def placement():
    P = {"J1": (J1_AT[0], J1_AT[1], 0, "B")}
    for d, x in COLS.items():
        P[d] = (x, LED_Y, 90, "F")
        P[RES[d]] = (x, R_Y, 270, "F")
    for s, (x, y) in SW_AT.items():
        P[s] = (x, y, 0, "F")
    return P


PLACE = placement()


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
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i + 1:j])
            i = j + 1
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


def load_fp(lib, name):
    fp = pcbnew.FootprintLoad(FPDIR + lib + ".pretty", name)
    if fp is None:
        raise SystemExit("footprint not found: %s:%s" % (lib, name))
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def P(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def edge_line(b, a, c):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)


def edge_arc(b, a, m, c):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*m), P(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)


def outline(b):
    r = CORNER_R
    k = r * (1 - math.sqrt(0.5))
    edge_line(b, (r, 0), (W - r, 0))
    edge_line(b, (W, r), (W, H - r))
    edge_line(b, (W - r, H), (r, H))
    edge_line(b, (0, H - r), (0, r))
    edge_arc(b, (W - r, 0), (W - k, k), (W, r))
    edge_arc(b, (W, H - r), (W - k, H - k), (W - r, H))
    edge_arc(b, (r, H), (k, H - k), (0, H - r))
    edge_arc(b, (0, r), (k, k), (r, 0))
    for cx, cy, d in slots():
        hl, rr = SLOT_L / 2, SLOT_W / 2            # 円の中心は ±5.1、半径 0.9
        if d == "x":
            edge_line(b, (cx - hl, cy - rr), (cx + hl, cy - rr))
            edge_line(b, (cx + hl, cy + rr), (cx - hl, cy + rr))
            edge_arc(b, (cx + hl, cy - rr), (cx + hl + rr, cy), (cx + hl, cy + rr))
            edge_arc(b, (cx - hl, cy + rr), (cx - hl - rr, cy), (cx - hl, cy - rr))
        else:
            edge_line(b, (cx + rr, cy - hl), (cx + rr, cy + hl))
            edge_line(b, (cx - rr, cy + hl), (cx - rr, cy - hl))
            edge_arc(b, (cx + rr, cy + hl), (cx, cy + hl + rr), (cx - rr, cy + hl))
            edge_arc(b, (cx - rr, cy - hl), (cx, cy - hl - rr), (cx + rr, cy - hl))


def build():
    assert set(COMPS) - set(PLACE) <= {"H1", "H2", "H3", "H4"}, sorted(set(COMPS) - set(PLACE))
    b = pcbnew.CreateEmptyBoard()
    b.GetDesignSettings().SetCopperLayerCount(2)
    for n in sorted({n for n in NET.values() if n}):
        b.Add(pcbnew.NETINFO_ITEM(b, n))
    nets = b.GetNetInfo().NetsByName()
    for ref in sorted(PLACE):
        x, y, rot, side = PLACE[ref]
        value, fpid = COMPS[ref]
        lib, name = fpid.split(":")
        fp = load_fp(lib, name)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(P(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            nm = NET.get((ref, pad.GetNumber()))
            if nm:
                pad.SetNet(nets[nm])
        b.Add(fp)
        if side == "B":
            fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for k, (x, y) in enumerate(HOLES):
        fp = load_fp("MountingHole", "MountingHole_3.2mm_M3")
        fp.SetReference("H%d" % (k + 1))
        fp.SetValue("M3")
        fp.SetPosition(P(x, y))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        b.Add(fp)
    outline(b)
    return b, nets


def pad_xy(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return (round(pcbnew.ToMM(p.GetPosition().x), 4), round(pcbnew.ToMM(p.GetPosition().y), 4))
    raise KeyError((ref, num))


def routes(b):
    """(net, 点の列, 層)、ビア (net, 点)。裏の線は J1 から下 (前) へ下ろし、横へ振って部品の手前でビアで表へ"""
    j = lambda n: pad_xy(b, "J1", str(n))          # noqa: E731
    R, V = [], []

    def via_to(net, xy_j, turn_y, dest, via_y):
        x, y = xy_j
        R.append((net, [(x, y), (x, turn_y), (dest[0], turn_y), (dest[0], via_y)], "B"))
        V.append((net, (dest[0], via_y)))
        R.append((net, [(dest[0], via_y), dest], "F"))

    via_to("LED_DMX", j(6), 80.0, pad_xy(b, "R3", "1"), 89.5)
    via_to("LED_LAN", j(5), 84.0, pad_xy(b, "R2", "1"), 89.5)
    via_to("+3V3", j(1), 80.0, pad_xy(b, "R1", "1"), 89.5)
    via_to("EN_PANEL", j(3), 84.0, pad_xy(b, "SW2", "1"), 92.6)
    via_to("BTN_LOCK", j(4), 88.0, pad_xy(b, "SW1", "1"), 92.6)
    # LED_LOCK は表だけで (裏の DMX・LAN の線をまたぐため)
    x, y = j(7)
    r4 = pad_xy(b, "R4", "1")
    R.append(("LED_LOCK", [(x, y), (x, 90.0), (r4[0], 90.0), r4], "F"))
    # 抵抗 → LED のアノード
    for d, r in RES.items():
        R.append((NET[(r, "2")], [pad_xy(b, r, "2"), pad_xy(b, d, "2")], "F"))
    # ボタンの GND (2 番) は表のベタ。1 番の左右 2 つはパッドどうしをつなぐ
    for s in SW_AT:
        R.append((NET[(s, "1")], [pad_xy_all(b, s, "1")[0], pad_xy_all(b, s, "1")[1]], "F"))
    return R, V


def pad_xy_all(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    return sorted((round(pcbnew.ToMM(p.GetPosition().x), 4), round(pcbnew.ToMM(p.GetPosition().y), 4))
                  for p in fp.Pads() if p.GetNumber() == num)


def N(nets, net):
    return nets[net] if net in nets else nets["/" + net]


def add_track(b, nets, a, c, w, layer, net):
    tr = pcbnew.PCB_TRACK(b)
    tr.SetStart(P(*a))
    tr.SetEnd(P(*c))
    tr.SetWidth(pcbnew.FromMM(w))
    tr.SetLayer(layer)
    tr.SetNet(N(nets, net))
    b.Add(tr)


def add_via(b, nets, p, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(*p))
    v.SetWidth(pcbnew.FromMM(VIA_D))
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetNet(N(nets, net))
    b.Add(v)


def zone(b, layer, net):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(net)
    o = z.Outline()
    o.NewOutline()
    for x, y in [(0, 0), (W, 0), (W, H), (0, H)]:
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetLocalClearance(pcbnew.FromMM(CLR))
    z.SetMinThickness(pcbnew.FromMM(0.5))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)


def seg_dist(p, a, c):
    ax, ay = a
    cx_, cy_ = c
    px, py = p
    dx, dy = cx_ - ax, cy_ - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def stitch_points(b, R, V, pitch=10.0):
    """表裏の GND ベタをつなぐビア。線・パッド・穴・つめの穴・板の端から離れた格子点だけ"""
    segs = [(a, c) for _, path, _ in R for a, c in zip(path, path[1:])]
    pads = []
    for fp in b.Footprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                         pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
        if fp.GetReference().startswith(("SW", "J")):     # ボタン・コネクタの外形の下には打たない
            for it in fp.GraphicalItems():
                if it.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                    bb = it.GetBoundingBox()
                    pads.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                                 pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
    out = []
    y = 4.0
    while y < H - 3.0:
        x = 4.0
        while x < W - 3.0:
            ok = all(seg_dist((x, y), a, c) >= W_SIG / 2 + CLR + VIA_D / 2 + 0.3 for a, c in segs)
            ok = ok and all(math.hypot(x - vx, y - vy) >= 2.0 for _, (vx, vy) in V)
            ok = ok and all(not (x0 - 1.0 < x < x1 + 1.0 and y0 - 1.0 < y < y1 + 1.0) for x0, y0, x1, y1 in pads)
            ok = ok and all(math.hypot(x - hx, y - hy) >= 4.5 for hx, hy in HOLES)
            for cx, cy, d in slots():
                lx, ly = (SLOT_L / 2 + 0.9, 0.9) if d == "x" else (0.9, SLOT_L / 2 + 0.9)
                ok = ok and not (abs(x - cx) < lx + 1.5 and abs(y - cy) < ly + 1.5)
            ok = ok and LBL_Y + 1.6 < y or y < LBL_Y - 6.5 if ok else False
            if ok:
                out.append((round(x, 3), round(y, 3)))
            x += pitch
        y += pitch
    return out


def silk(b, s, x, y, size=1.0, layer=pcbnew.F_SilkS, ang=0, bold=False):
    tx = pcbnew.PCB_TEXT(b)
    tx.SetText(s)
    tx.SetLayer(layer)
    tx.SetTextSize(P(size, size))
    tx.SetTextThickness(pcbnew.FromMM(size * (0.2 if bold else 0.15)))
    tx.SetTextAngleDegrees(ang)
    if layer == pcbnew.B_SilkS:
        tx.SetMirrored(True)
    tx.SetPosition(P(x, y))
    b.Add(tx)


def labels(b):
    names = {"D1": "PWR", "D2": "LAN", "D3": "DMX", "D4": "LOCK"}
    for d, x in COLS.items():
        silk(b, names[d], x, LBL_Y, 1.2, bold=True)
    silk(b, "LOCK", SW_AT["SW1"][0], LBL_Y + 1.7, 1.2, bold=True)
    silk(b, "RESET", SW_AT["SW2"][0], LBL_Y + 1.7, 1.2, bold=True)
    silk(b, "ODE-DIY", W / 2, 66.0, 3.0, bold=True)
    silk(b, "Art-Net / sACN to DMX", W / 2, 70.5, 1.5)
    silk(b, "ode_top rev B  2026-11", W / 2, 20.0, 1.0)
    # 参照記号は部品の右 (表)
    for d, x in COLS.items():
        silk(b, d, x + 2.5, LED_Y, 0.8)
        silk(b, RES[d], x + 2.5, R_Y, 0.8)
    for s, (x, y) in SW_AT.items():
        silk(b, s, x + 5.2, y, 0.8, ang=90)
    # 裏: J1 の説明 (裏から見て読める向き)
    silk(b, "J1 to main J6 (pin n to pin n, J1.1 = +3V3)", J1_AT[0] - 7.0, J1_AT[1] + 5.2, 0.9, layer=pcbnew.B_SilkS)
    silk(b, "PH 8P cable, pin 1 to pin 1", J1_AT[0] - 7.0, J1_AT[1] + 6.6, 0.9, layer=pcbnew.B_SilkS)
    silk(b, "FRONT edge (connector side)", W / 2, H - 6.0, 0.9, layer=pcbnew.B_SilkS)


def write_pro():
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


def main():
    pro = json.load(open(os.path.join(PROJ, NAME + ".kicad_pro")))
    b, nets = build()
    R, V = routes(b)
    for net, path, layer in R:
        for a, c in zip(path, path[1:]):
            add_track(b, nets, a, c, W_SIG, pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu, net)
    for net, p in V:
        add_via(b, nets, p, net)
    st = stitch_points(b, R, V)
    for p in st:
        add_via(b, nets, p, "GND")
    labels(b)
    zone(b, pcbnew.F_Cu, nets["GND"])
    zone(b, pcbnew.B_Cu, nets["GND"])
    off = P(*SHEET_CENTER)
    for it in list(b.GetFootprints()) + list(b.GetTracks()) + list(b.Drawings()) + list(b.Zones()):
        it.Move(off)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(OUT)
    json.dump(pro, open(os.path.join(PROJ, NAME + ".kicad_pro"), "w"), indent=2)
    write_pro()
    print("-> %s  線 %d 本 / ビア %d + GND %d / J1 の 1 番 %s / 穴 %s" % (OUT, sum(len(p) - 1 for _, p, _ in R), len(V), len(st), J1_AT, HOLES))


if __name__ == "__main__":
    main()
