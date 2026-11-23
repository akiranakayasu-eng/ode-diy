#!/usr/bin/env python3
"""sacn_node_out8 の自動配線 (dmx_usb_pro/scripts/route.py を流用)。

変更点: 配線しないネット (ベタの GND / GND_ISO_k と、母線から route_groups で繋ぐ +5V) を geom.json の
pour_nets / skip_nets から読む。基板が 232 x 88 と大きいので格子は 0.125 のまま、他は同じ。

元の説明 (dmx_usb_pro): clearance 0.2 / 信号 0.3 / 電源 0.5。GND と GND_ISO はベタ (配線しない)。
geom.json の keepouts は **トラックもビアも通さない** (絶縁帯)。mini_uno 版はビアだけ見ていた。

元の説明:
artic8 の自動配線。素の python3 で動く (pcbnew も numpy も不要)。ga4act の route.py がベース。

  $KIPY scripts/gen_pcb.py --geom      (KiCad の python で)
  python3 scripts/route.py             (素の python3 で)
  $KIPY scripts/gen_pcb.py             (KiCad の python で)

0.25mm グリッドの A* 迷路ルータ。
geom.json のパッド矩形と外形を読み、ネットごとに全域木を張って 1 接続ずつ通す。

8 ユニットがそれぞれ「兼用ランド 5 極 <-> 制御ソケット <-> インジケータ 4ch」を
繋ぐ構造で、ユニット間は D+/D- のバスだけ。層規約は F=横 / B=縦。
"""
import heapq
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
GEOM = os.path.join(PROJ, "docs", "geom.json")
OUT = os.path.join(PROJ, "docs", "routes.json")

G = 0.25                  # グリッド [mm]。この基板の最細ピッチは SOT-23 の 0.95 / SOIC の 1.27 なので 0.25 で足りる (dmx_usb_pro は SSOP のため 0.125)
CLR = 0.15                # 設計クリアランス (.kicad_pro の Default と合わせる)
PAD_INSET = 0.1           # 接続点はパッド矩形を少し内側に縮めて取る
OBST_MARGIN = 0.0         # 障害物側にだけ足す格子丸めの逃げ
EDGE_CLR = 0.5            # copper_edge_clearance
VIA_D, VIA_DRILL = 0.5, 0.3

# 層規約を **コストで** 効かせる
# (禁止にすると解けない。短いジョグだけが例外として通る)。F=横 / B=縦。
COST = {("F", "h"): 10, ("F", "v"): 34, ("B", "h"): 34, ("B", "v"): 10}
VIA_COST = 160           # 0.25 格子 (= 4mm 相当)

# +5V と GND はベタで配るのでトラックを引かない (gen_pcb.py の POUR_NETS と対応)。
SKIP_NETS = set()           # main() で geom.json から読む
POUR_ONLY = set()

# ソフト・キープアウト 1 マスあたりの追加コスト。artic8 の通路は幅 3.0mm = 12 マスしか
# 無いので、ga4act の 40 では **F.Cu をそのまま横断する方が安くなってしまう**
# (12x(10+40)=600 < ビア 2 個 320 + 裏の横移動 12x34=408 = 728)。
# 100 にすると横断 12x110=1320 > 728 となり、ルータが自分で裏へ逃げてベタを繋いだまま残す。
# 通路の中にはパッドが 1 つも無いので、高くしても届かなくなるものは無い。
# 領域ごとに 6 番目の要素でコストを変えられる（IC まわりのガードは 45 を使う。
# 素通りの横断 32 マス = 1440 は追い出せるが、ピンから 7 マス出る = 315 は払える）。
SOFT_COST = 100


def main():
    g = json.load(open(GEOM))
    SKIP_NETS.update(g.get("pour_nets", []))
    SKIP_NETS.update(g.get("skip_nets", []))
    pads = g["pads"]
    outline = [tuple(p) for p in g["outline"]]
    wide = set(g["wide_nets"])
    w_wide, w_sig = g["w_wide"], g["w_sig"]
    keepouts = [tuple(k) for k in g.get("keepouts", [])]
    soft = g.get("soft_keepouts", [])

    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0 = -math.ceil((abs(min(xs)) + 1) / G) * G
    y0 = -math.ceil((abs(min(ys)) + 1) / G) * G

    # artic8 はパッド格子 (2.0mm ランド原) に原点を合わせたが、ここは TQFP (0.5mm) と
    # 1608 の座標が 0.25 の倍数なので、原点も 0.25 の倍数のまま使う。
    NX = int(math.ceil((max(xs) + 1 - x0) / G)) + 1
    NY = int(math.ceil((max(ys) + 1 - y0) / G)) + 1

    def cell(x, y):
        return (int(round((x - x0) / G)), int(round((y - y0) / G)))

    def pos(i, j):
        return (x0 + i * G, y0 + j * G)

    # ------------------------------------------------ 基板内マスク
    inb_by_w = {}
    WIDTHS = sorted({w_sig, w_wide})
    for w in set(WIDTHS) | {VIA_D}:
        m = bytearray(NX * NY)
        for j in range(NY):
            for i in range(NX):
                if _inside(pos(i, j), outline, EDGE_CLR + w / 2):
                    m[j * NX + i] = 1
        # 絶縁帯などのハード・キープアウト: トラックの縁が入らないようにする
        for kx0, ky0, kx1, ky1 in [tuple(k) for k in g.get("keepouts", [])]:
            mm_ = w / 2 + 0.05
            for j in range(*_rng(ky0 - mm_, ky1 + mm_, y0, NY)):
                for i in range(*_rng(kx0 - mm_, kx1 + mm_, x0, NX)):
                    m[j * NX + i] = 0
        inb_by_w[w] = m

    # ------------------------------------------------ パッドの占有
    bref = {}
    for p in pads:
        bref.setdefault(p["ref"], []).append(p)
    fine, ctr = set(), {}
    for ref, ps in bref.items():
        ctr[ref] = (sum(q["x"] for q in ps) / len(ps), sum(q["y"] for q in ps) / len(ps))
        if len(ps) < 4:
            continue
        dmin = min(math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                   for i, a in enumerate(ps) for b in ps[i + 1:])
        if dmin < 0.8:
            fine.add(ref)

    pad_cells = {}
    for p in pads:
        if not p["net"]:
            continue                       # NPTH は接続対象ではない (障害物としては残す)
        halfw, halfh = p["w"] / 2, p["h"] / 2
        if abs((p["rot"] % 180) - 90) < 1:
            halfw, halfh = halfh, halfw
        lay = ["F", "B"] if p["thru"] else p["layers"]
        iw = max(halfw - PAD_INSET, halfw * 0.3)
        ih = max(halfh - PAD_INSET, halfh * 0.3)
        cells = {}
        for L in lay:
            s = set()
            for j in range(*_rng(p["y"] - ih, p["y"] + ih, y0, NY)):
                for i in range(*_rng(p["x"] - iw, p["x"] + iw, x0, NX)):
                    s.add((i, j))
            if p["ref"] in fine and s:
                cx, cy = ctr[p["ref"]]
                if iw > ih:
                    sgn = 1 if p["x"] > cx else -1
                    lim = p["x"] + sgn * iw * 0.2
                    s = {c for c in s if (pos(*c)[0] - lim) * sgn >= -1e-9}
                else:
                    sgn = 1 if p["y"] > cy else -1
                    lim = p["y"] + sgn * ih * 0.2
                    s = {c for c in s if (pos(*c)[1] - lim) * sgn >= -1e-9}
            if p["thru"] and s:
                # **THT パッドは丸い。** 矩形のまま接続セルを取ると角にトラック端が落ち、
                # パッドの外になって KiCad 上で未接続になる (J1-J3 で 6 本出た)
                s = {c for c in s
                     if ((pos(*c)[0] - p["x"]) / iw) ** 2 + ((pos(*c)[1] - p["y"]) / ih) ** 2 <= 1.0}
            if not s:
                s.add(cell(p["x"], p["y"]))
            cells[L] = s
        pad_cells[(p["ref"], p["pad"])] = cells

    # ビアを置いてはいけないセル: スルーホールの穴まわり + 配線禁止領域
    novia = set()
    for kx0, ky0, kx1, ky1 in keepouts:
        m = CLR + VIA_D / 2
        for j in range(*_rng(ky0 - m, ky1 + m, y0, NY)):
            for i in range(*_rng(kx0 - m, kx1 + m, x0, NX)):
                novia.add((i, j))
    for p in pads:
        m = CLR + VIA_D / 2
        if p["thru"] or not p["net"]:      # THT パッドと NPTH のまわり
            mx = my = max(p["w"], p["h"]) / 2 + m
        else:
            # **SMD パッドの中にもビアを落とさない。** 手はんだのとき半田が穴へ吸われる。
            # エナメル線を寝かせて付ける端子のはんだパッドでは特に致命的で、
            # 実際にルータが 5 極すべてのパッドの中にビアを置いていた (2026-08-30)
            hw, hh = p["w"] / 2, p["h"] / 2
            if abs((p["rot"] % 180) - 90) < 1:
                hw, hh = hh, hw
            mx, my = hw + m, hh + m
        for j in range(*_rng(p["y"] - my, p["y"] + my, y0, NY)):
            for i in range(*_rng(p["x"] - mx, p["x"] + mx, x0, NX)):
                novia.add((i, j))

    # ソフト・キープアウトのセル -> 追加コスト (レイヤ別)。重なったら高い方を採る
    pen = {"F": {}, "B": {}}
    for k in soft:
        kx0, ky0, kx1, ky1, klay = k[:5]
        kc = k[5] if len(k) > 5 else SOFT_COST
        for L in ("F", "B") if klay == "FB" else (klay,):
            for j in range(*_rng(ky0, ky1, y0, NY)):
                for i in range(*_rng(kx0, kx1, x0, NX)):
                    if kc > pen[L].get((i, j), 0):
                        pen[L][(i, j)] = kc

    # ------------------------------------------------ 占有マップ（所有ネット付き）
    # ネットごとに障害物集合を作り直すと 123 ネット x 84 万セルで現実的な時間に
    # 収まらない。**「そのセルを持っているネット」を一度だけ辞書に作り**、
    # astar 側で「自分以外が持っていたら通れない」と判定する。
    BLOCK = "\x00"                       # 誰も通れない（NPTH / 別ネットの重なり）

    def stamp(d, cells, net):
        for c in cells:
            cur = d.get(c)
            d[c] = net if cur is None or cur == net else BLOCK

    def build_pad_own(halfw):
        own = {"F": {}, "B": {}}
        for p in pads:
            lay = ["F", "B"] if (p["thru"] or not p["net"]) else p["layers"]
            hw, hh = p["w"] / 2, p["h"] / 2
            if abs((p["rot"] % 180) - 90) < 1:
                hw, hh = hh, hw
            m = CLR + OBST_MARGIN + halfw - 1e-6   # ちょうど CLR は通す (0.5 ピッチの隣のビア)
            net = p["net"] or BLOCK
            jr = _rng(p["y"] - hh - m, p["y"] + hh + m, y0, NY)
            ir = _rng(p["x"] - hw - m, p["x"] + hw + m, x0, NX)
            cells = [(i, j) for j in range(*jr) for i in range(*ir)]
            for L in lay:
                stamp(own[L], cells, net)
        return own

    # 問い合わせ側の線幅ごとに作る (0.5mm の電源線と 0.3mm の信号線で必要な離れが違う)
    PAD_OWN = {q: build_pad_own(q / 2) for q in WIDTHS}   # トラック通過用
    PAD_OWN_V = build_pad_own(VIA_D / 2)        # ビア設置用

    def disc(r):
        rad = int(r / G)
        return [(di, dj) for dj in range(-rad, rad + 1) for di in range(-rad, rad + 1)
                if (di*di + dj*dj) * G * G < r*r - 1e-6]  # ちょうど r (= clearance ちょうど) は許す

    # D_TRK[(敷いた線幅, 問い合わせ線幅)]、D_TRK_V[敷いた線幅] (ビア設置用)、D_VIA[問い合わせ線幅]
    D_TRK = {(wl, q): disc(wl / 2 + CLR + q / 2) for wl in WIDTHS for q in WIDTHS}
    D_TRK_V = {wl: disc(wl / 2 + CLR + VIA_D / 2) for wl in WIDTHS}
    D_VIA = {q: disc(VIA_D / 2 + CLR + q / 2) for q in WIDTHS}
    D_VIA_V = disc(VIA_D / 2 + CLR + VIA_D / 2) # 0.90mm

    # ------------------------------------------------ ネットごとに全域木
    bynet = {}
    for p in pads:
        if not p["net"] or p["net"] in SKIP_NETS:
            continue
        if p["net"].startswith("unconnected-") or p["net"] in g.get("fixed_nets", []):
            continue                       # fixed_nets は gen_pcb.py が手で引く (USB D+/D-)
        if (p["ref"], p["pad"]) in POUR_ONLY:
            continue
        bynet.setdefault(p["net"], []).append(p)

    # ベタのネットでも、ベタが届かないパッドだけは小さなグループとして配線する
    for k, grp in enumerate(g.get("route_groups", [])):
        want = {tuple(x) for x in grp["pads"]}
        terms = [p for p in pads if (p["ref"], p["pad"]) in want]
        assert len(terms) == len(want), grp
        bynet["%s#%d" % (grp["net"], k)] = terms

    def order_key(bias):
        def k(n):
            terms = bynet[n]
            # 端子数の多いネット (D+ / D- のバス) を先に通す。後回しにすると
            # セル間の帯が埋まって board を横断できなくなる。
            return (bias.get(n, 0), -len(terms), n)
        return k

    def route_all(bias):
        tracks, vias, fails = [], [], []
        laid = {q: {"F": {}, "B": {}} for q in WIDTHS}   # トラック通過の障害 (問い合わせ線幅別)
        laid_v = {"F": {}, "B": {}}        # ビア設置の障害
        order = sorted(bynet, key=order_key(bias))
        for kk, net in enumerate(order):
            if kk % 20 == 0:
                print("    %3d/%d %s" % (kk, len(order), net), flush=True)
            terms = bynet[net]
            if len(terms) < 2:
                continue
            key = net
            net = net.split("#")[0]
            width0 = w_wide if net in wide else w_sig
            done = {"F": set(), "B": set()}
            by_w = {q: {"F": set(), "B": set()} for q in WIDTHS}
            via_cells = set()
            for a_, b_ in _mst(terms):
                src = _cells_of(pad_cells, a_, done)
                dst = _cells_of(pad_cells, b_, {"F": set(), "B": set()})
                path = None
                # 電源線は 0.5mm で通らなければ (細ピッチ IC のピンなど) 0.3mm で引く
                widths = sorted({width0, w_sig}, reverse=True)
                if min(a_["w"], a_["h"], b_["w"], b_["h"]) < width0 + 2 * CLR:
                    widths = [w_sig]            # 細いパッド (LQFP) の中に太い線の端を置かない
                for width in widths:
                    path = astar(src, dst, net, PAD_OWN[width], laid[width], PAD_OWN_V, laid_v,
                                 inb_by_w[width], NX, NY, novia, pen, BLOCK, inb_by_w[VIA_D])
                    if path is not None:
                        break
                if path is None:
                    fails.append((key, a_["ref"] + "." + a_["pad"],
                                  b_["ref"] + "." + b_["pad"]))
                    continue
                tmp = {"F": set(), "B": set()}
                _emit(path, pos, width, net, tracks, vias, tmp, via_cells)
                for L in ("F", "B"):
                    done[L] |= tmp[L]
                    by_w[width][L] |= tmp[L]
            for L in ("F", "B"):
                for wl in WIDTHS:
                    for q in WIDTHS:
                        cs = [(c[0] + d[0], c[1] + d[1]) for c in by_w[wl][L] for d in D_TRK[(wl, q)]]
                        stamp(laid[q][L], cs, net)
                    cs = [(c[0] + d[0], c[1] + d[1]) for c in by_w[wl][L] for d in D_TRK_V[wl]]
                    stamp(laid_v[L], cs, net)
            for L in ("F", "B"):
                for q in WIDTHS:
                    cs = [(c[0] + d[0], c[1] + d[1]) for c in via_cells for d in D_VIA[q]]
                    stamp(laid[q][L], cs, net)
                cs = [(c[0] + d[0], c[1] + d[1]) for c in via_cells for d in D_VIA_V]
                stamp(laid_v[L], cs, net)
        return tracks, vias, fails

    # 落ちたネットの優先度を **累積** で上げていく（artic8 は毎回置き換えていたので、
    # 2 組の失敗ネットの間を行ったり来たりして収束しなかった）
    bias, best = {}, None
    for attempt in range(int(os.environ.get("ROUTE_TRIES", "30"))):
        tracks, vias, fails = route_all(bias)
        if best is None or len(fails) < len(best[2]):
            best = (tracks, vias, fails)
        if not fails:
            break
        for f in fails:
            bias[f[0]] = bias.get(f[0], 0) - 1
        print("  retry %d: %d 本失敗 -> %s"
              % (attempt + 1, len(fails), ",".join(sorted({f[0] for f in fails}))))
        for f in fails:
            print("    FAIL %s : %s - %s" % f, flush=True)
    tracks, vias, fails = best

    json.dump({"tracks": tracks, "vias": vias}, open(OUT, "w"), indent=1)
    print("nets %d  tracks %d  vias %d  failed %d"
          % (len(bynet), len(tracks), len(vias), len(fails)))
    for f in fails:
        print("  FAIL %s : %s - %s" % f)
    return len(fails)


# ---------------------------------------------------------------- helpers
def _rng(lo, hi, base, n):
    """[lo,hi] に「セル中心が入る」インデックス範囲 (矩形に掛かるセルではない)。"""
    return (max(0, int(math.ceil((lo - base) / G - 1e-9))),
            min(n, int(math.floor((hi - base) / G + 1e-9)) + 1))


def _inside(p, poly, margin):
    x, y = p
    c = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            c = not c
    if not c:
        return False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if _segdist(p, a, b) < margin:
            return False
    return True


def _segdist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _mst(terms):
    n = len(terms)
    used, edges = [0], []
    rest = list(range(1, n))
    while rest:
        best = None
        for u in used:
            for v in rest:
                d = math.hypot(terms[u]["x"] - terms[v]["x"], terms[u]["y"] - terms[v]["y"])
                if best is None or d < best[0]:
                    best = (d, u, v)
        _, u, v = best
        edges.append((terms[u], terms[v]))
        used.append(v)
        rest.remove(v)
    return edges


def _cells_of(pad_cells, pad, already):
    out = {}
    for L in ("F", "B"):
        s = set(pad_cells[(pad["ref"], pad["pad"])].get(L, ()))
        s |= already[L]
        out[L] = s
    return out


def astar(src, dst, net, pad_own, laid, pad_own_v, laid_v,
          inb, NX, NY, novia, pen=None, BLOCK="\x00", inb_via=None):
    LAYERS = ("F", "B")
    pen = pen or {"F": {}, "B": {}}
    start = [(0, (i, j, L)) for L in LAYERS for (i, j) in src[L] if inb[j * NX + i]]
    if not start:
        return None
    goal = {(i, j, L) for L in LAYERS for (i, j) in dst[L]}
    if not goal:
        return None
    gx = sum(c[0] for c in goal) / len(goal)
    gy = sum(c[1] for c in goal) / len(goal)

    def h(i, j):
        return int((abs(i - gx) + abs(j - gy)) * 10)

    best, pq, came = {}, [], {}
    for _, s in start:
        best[s] = 0
        heapq.heappush(pq, (h(s[0], s[1]), 0, s, None))
    while pq:
        _, cost, cur, prev = heapq.heappop(pq)
        if cur in came:
            continue
        came[cur] = prev
        if cur in goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        i, j, L = cur
        for di, dj, d in ((1, 0, "h"), (-1, 0, "h"), (0, 1, "v"), (0, -1, "v")):
            ni, nj = i + di, j + dj
            if not (0 <= ni < NX and 0 <= nj < NY):
                continue
            if not inb[nj * NX + ni]:
                continue
            if (ni, nj, L) not in goal:
                o = pad_own[L].get((ni, nj))
                if o is not None and o != net:
                    continue
                o = laid[L].get((ni, nj))
                if o is not None and o != net:
                    continue
            nc = cost + COST[(L, d)] + pen[L].get((ni, nj), 0)
            k = (ni, nj, L)
            if k not in came and (k not in best or nc < best[k]):
                best[k] = nc
                heapq.heappush(pq, (nc + h(ni, nj), nc, k, cur))
        M = "B" if L == "F" else "F"
        # **ビアは φ0.6 なのでトラック用の基板内マスクでは足りない。**
        # track の 0.2 で作ったマスクで判定すると、基板端から 0.45mm の所に
        # ビアが落ちて copper_edge_clearance になる（実際に IN_D- で出た）。
        if inb_via is not None and not inb_via[j * NX + i]:
            continue
        if (i, j) in novia:
            continue
        blocked = False
        for LL in (L, M):
            o = pad_own_v[LL].get((i, j))
            if o is not None and o != net:
                blocked = True; break
            o = laid_v[LL].get((i, j))
            if o is not None and o != net:
                blocked = True; break
        if blocked:
            continue
        nc = cost + VIA_COST
        k = (i, j, M)
        if k not in came and (k not in best or nc < best[k]):
            best[k] = nc
            heapq.heappush(pq, (nc + h(i, j), nc, k, cur))
    return None


def _emit(path, pos, width, net, tracks, vias, routed, via_cells):
    run = [path[0]]
    for cur in path[1:]:
        p = run[-1]
        if cur[2] != p[2]:                      # レイヤ変更 = ビア
            _flush(run, pos, width, net, tracks, routed)
            x, y = pos(p[0], p[1])
            vias.append([round(x, 4), round(y, 4), VIA_D, VIA_DRILL, net])
            via_cells.add((p[0], p[1]))
            run = [cur]
            continue
        run.append(cur)
    _flush(run, pos, width, net, tracks, routed)


def _flush(run, pos, width, net, tracks, routed):
    if len(run) < 2:
        if run:
            routed[run[0][2]].add((run[0][0], run[0][1]))
        return
    L = run[0][2]
    seg = [run[0]]
    for k in range(1, len(run)):
        routed[L].add((run[k][0], run[k][1]))
        if k + 1 < len(run):
            d1 = (run[k][0] - run[k - 1][0], run[k][1] - run[k - 1][1])
            d2 = (run[k + 1][0] - run[k][0], run[k + 1][1] - run[k][1])
            if d1 == d2:
                continue
        a, b = seg[-1], run[k]
        ax, ay = pos(a[0], a[1])
        bx, by = pos(b[0], b[1])
        tracks.append([round(ax, 4), round(ay, 4), round(bx, 4), round(by, 4),
                       width, L, net])
        seg.append(run[k])
    routed[L].add((run[0][0], run[0][1]))


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
