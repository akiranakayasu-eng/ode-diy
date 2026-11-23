#!/usr/bin/env python3
"""sACN ノード回路図生成の共通部 (dmx_usb_pro/scripts/sch_core.py を流用)。

NAME はプロジェクトのフォルダ名。part() で全ピンのネットを明示し、EXPECT に設計意図を貯める。

座標系: シンボルは Y 上向き、シートは Y 下向き。
"""
import hashlib
import math
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = os.path.basename(PROJ)
LIB = os.path.join(PROJ, NAME + ".kicad_sym")
OUT = os.path.join(PROJ, NAME + ".kicad_sch")
SHEET_UUID = None  # uid() で NAME から作る (下で設定)
G = 1.27


# ------------------------------------------------------------------ ライブラリ
def load_lib():
    text = open(LIB).read()
    idx = [(m.start(), m.group(1)) for m in re.finditer(r'\n\t\(symbol "([^"]+)"\n', text)]
    syms = {}
    for k, (s, n) in enumerate(idx):
        e = idx[k + 1][0] if k + 1 < len(idx) else text.rfind(")")
        blk = text[s:e].strip("\n")
        units = defaultdict(dict)
        subs = [(m.start(), int(m.group(1))) for m in
                re.finditer(r'\(symbol "%s_(\d+)_\d+"' % re.escape(n), blk)]
        for i, (ss, u) in enumerate(subs):
            se = subs[i + 1][0] if i + 1 < len(subs) else len(blk)
            for m in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)'
                                 r'[\s\S]*?\(number "([^"]*)"', blk[ss:se]):
                units[u][m.group(5)] = (float(m.group(2)), float(m.group(3)))
        syms[n] = {"block": blk, "units": units}
    return syms


LIBSYMS = load_lib() if os.path.exists(LIB) else {}


def uid(*parts):
    h = hashlib.md5((NAME + "|".join(str(p) for p in parts)).encode()).hexdigest()
    return "%s-%s-%s-%s-%s" % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


SHEET_UUID = uid("sheet")


def pt(p):
    return (round(p[0], 4), round(p[1], 4))


def f(v):
    s = ("%.4f" % round(v, 4)).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def P(x, y):
    return pt((x, y))


def ongrid(v):
    assert abs(v / G - round(v / G)) < 1e-6, ("off grid", v)


DIRS = {"L": (-1, 0, 180), "R": (1, 0, 0), "U": (0, -1, 90), "D": (0, 1, 270)}


# ------------------------------------------------------------------ シート
class Sheet:
    def __init__(self):
        self.items = []
        self.wires = []
        self.pinpts = []
        self.used = set()
        self.counts = defaultdict(int)

    def place(self, ref, lib, value, x, y, rot=0, mirror=False, unit=1,
              ref_off=(2.54, -2.54), val_off=(2.54, 2.54), hide_value=False, hide_ref=False, fp=None):
        sym = LIBSYMS[lib]
        self.used.add(lib)
        th = math.radians(rot)
        cos, sin = round(math.cos(th)), round(math.sin(th))
        pins = dict(sym["units"].get(0, {}))
        pins.update(sym["units"].get(unit, {}))
        pos = {}
        for num, (px, py) in pins.items():
            if mirror:
                px = -px
            qx = px * cos - py * sin
            qy = px * sin + py * cos
            pos[num] = (round(x + qx, 4), round(y - qy, 4))
            ongrid(pos[num][0])
            ongrid(pos[num][1])
        m = re.search(r'\(property "Footprint" "([^"]*)"', sym["block"])
        fp = fp or (m.group(1) if m else "")
        props = [("Reference", ref, hide_ref, ref_off),
                 ("Value", value, hide_value, val_off),
                 ("Footprint", fp, True, (0, 0)),
                 ("Datasheet", "", True, (0, 0)),
                 ("Description", "", True, (0, 0))]
        s = ['\t(symbol\n\t\t(lib_id "%s:%s")\n\t\t(at %s %s %d)\n' % (NAME, lib, f(x), f(y), rot)]
        if mirror:
            s.append("\t\t(mirror y)\n")
        in_bom = "no" if lib in ("MountingHole", "SolderJumper_2_Open") else "yes"
        s.append('\t\t(unit %d)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom %s)\n'
                 '\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n' % (unit, in_bom))
        s.append('\t\t(uuid "%s")\n' % uid("sym", ref, unit))
        pang = 0 if rot in (0, 180) else (360 - rot) % 360
        for key, val, hide, off in props:
            s.append('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %d)\n\t\t\t(show_name no)\n'
                     '\t\t\t(do_not_autoplace no)\n%s'
                     '\t\t\t(effects\n\t\t\t\t(font (size 1.27 1.27))\n\t\t\t\t(justify left)\n\t\t\t)\n\t\t)\n'
                     % (key, val, f(x + off[0]), f(y + off[1]), pang,
                        "\t\t\t(hide yes)\n" if hide else ""))
        for num in pins:
            s.append('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (num, uid("pin", ref, num)))
        s.append('\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n'
                 '\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit %d)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
                 % (NAME, SHEET_UUID, ref, unit))
        self.items.append("".join(s))
        self.pinpts.extend(pos.values())
        return pos

    def wire(self, a, b):
        a, b = pt(a), pt(b)
        if a == b:
            return
        assert abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6, ("斜め配線", a, b)
        for v in a + b:
            ongrid(v)
        self.wires.append((a, b))

    def path(self, *pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def label(self, at, text, rot=0):
        at = pt(at)
        self.pinpts.append(at)            # ワイヤ途中のラベルでも分割して確実に接続させる
        just = "right" if rot in (180, 270) else "left"
        self.items.append('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n'
                          '\t\t\t(font (size 1.27 1.27))\n\t\t\t(justify %s bottom)\n\t\t)\n'
                          '\t\t(uuid "%s")\n\t)\n'
                          % (text, f(at[0]), f(at[1]), rot, just, uid("lbl", text, at)))

    def text(self, at, text, size=1.5):
        at = pt(at)
        self.items.append('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n'
                          '\t\t(effects\n\t\t\t(font (size %s %s))\n\t\t\t(justify left bottom)\n\t\t)\n'
                          '\t\t(uuid "%s")\n\t)\n'
                          % (text.replace('"', '\\"'), f(at[0]), f(at[1]), f(size), f(size),
                             uid("txt", text, at)))

    def power(self, kind, at):
        at = pt(at)
        lib = {"+5V": "+5V", "+3V3": "+3V3", "GND": "GND", "FLAG": "PWR_FLAG"}[kind]
        self.counts[kind] += 1
        ref = "#%s%03d" % ({"+5V": "PWR", "+3V3": "PWR3", "GND": "GND", "FLAG": "FLG"}[kind], self.counts[kind])
        got = self.place(ref, lib, "PWR_FLAG" if kind == "FLAG" else kind, at[0], at[1],
                         ref_off=(0, 0), val_off=(0, -3.81 if kind != "GND" else 3.81),
                         hide_value=(kind == "FLAG"), hide_ref=True)
        assert list(got.values())[0] == at
        return at

    def stub(self, p, d, net, n=2):
        """ピン p から方向 d へ n マス (2.54mm 単位) 出してラベル/電源記号で終える。"""
        dx, dy, rot = DIRS[d]
        e = (p[0] + dx * 2.54 * n, p[1] + dy * 2.54 * n)
        self.wire(p, e)
        if net in ("+5V", "+3V3", "GND"):
            self.power(net, e)
        else:
            self.label(e, net, rot)
        return e

    def nc(self, at):
        at = pt(at)
        self.items.append('\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)\n'
                          % (f(at[0]), f(at[1]), uid("nc", at)))

    # --- ワイヤ途中の端点で分割し、T 字に junction を打つ ---
    def _inside(self, p, a, b):
        if p in (a, b):
            return False
        if a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]):
            return True
        return a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0])

    def split_wires(self):
        for _ in range(4):
            pts = set(self.pinpts)
            for a, b in self.wires:
                pts.update((a, b))
            new, changed = [], False
            for a, b in self.wires:
                inner = [p for p in pts if self._inside(p, a, b)]
                if not inner:
                    new.append((a, b))
                    continue
                changed = True
                chain = [a] + sorted(inner, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) + [b]
                new.extend(zip(chain, chain[1:]))
            self.wires = new
            if not changed:
                break

    def junctions(self):
        ends = defaultdict(int)
        for a, b in self.wires:
            ends[a] += 1
            ends[b] += 1
        pins = defaultdict(int)
        for p in self.pinpts:
            pins[p] += 1
        out = []
        for p in sorted(set(ends)):
            # ピンが 1 つ重なる点は「ワイヤ端 2 本 + ピン」で 3 方向になる
            if ends[p] + (1 if pins.get(p) else 0) >= 3:
                out.append(p)
        return out

    def render(self, title, rev, date, comment, paper="A3"):
        self.split_wires()
        lib_blocks = "\n".join(
            "\t\t" + LIBSYMS[n]["block"].replace('(symbol "%s"' % n, '(symbol "%s:%s"' % (NAME, n), 1)
            .replace("\n", "\n\t\t").rstrip("\t")
            for n in sorted(self.used))
        out = ['(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n'
               '\t(generator_version "10.0")\n\t(uuid "%s")\n\t(paper "%s")\n'
               '\t(title_block\n\t\t(title "%s")\n\t\t(date "%s")\n\t\t(rev "%s")\n'
               '\t\t(company "anderdesign")\n'
               '\t\t(comment 1 "%s")\n'
               '\t)\n\t(lib_symbols\n%s\n\t)\n' % (SHEET_UUID, paper, title, date, rev, comment, lib_blocks)]
        for a, b in self.wires:
            out.append('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n'
                       '\t\t(stroke (width 0) (type default))\n\t\t(uuid "%s")\n\t)\n'
                       % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), uid("w", a, b)))
        for p in self.junctions():
            out.append('\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n'
                       '\t\t(uuid "%s")\n\t)\n' % (f(p[0]), f(p[1]), uid("j", p)))
        out.extend(self.items)
        out.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n'
                   '\t(embedded_fonts no)\n)\n')
        return "".join(out)




# ------------------------------------------------------------------ 部品配置 (dmx_usb_pro/scripts/gen_sch.py の part() を共通化)
EXPECT = {}  # "ref.pin" -> net。verify_net.py がネットリストと突き合わせる


def make_part(s):
    """s (Sheet) に部品を置く part() を返す。"""
    def part(ref, lib, value, x, y, nets, rot=0, n=2, fp=None, hside=0.0, direct=(), **kw):
        """全ピンを nets で明示して置く。隣り合う同一ネットのピン (同じ向き・2.54 間隔) は
        スタブ端を 1 本のワイヤでまとめ、電源記号 / ラベルを 1 つだけ付ける (文字の重なり防止)。
        direct のピンは他部品のピンと座標で直結するのでスタブを出さない。"""
        pos = s.place(ref, lib, value, x, y, rot=rot, fp=fp, **kw)
        assert set(nets) == set(pos), (ref, set(pos) ^ set(nets))   # 全ピンを明示する
        info = {}
        for num, net in nets.items():
            assert "%s.%s" % (ref, num) not in EXPECT, (ref, num)
            EXPECT["%s.%s" % (ref, num)] = net
            px, py = pos[num]
            if num in direct:
                continue
            if net is None:
                s.nc((px, py))
                continue
            dx, dy = px - x, py - y
            horiz = abs(dx) > (hside or 0.01)
            info[num] = (net, ("R" if dx > 0 else "L") if horiz else ("D" if dy > 0 else "U"), (px, py))
        # 隣接グループ化
        parent = {k: k for k in info}

        def root(k):
            while parent[k] != k:
                k = parent[k]
            return k
        for a in info:
            for b in info:
                na, da, pa = info[a]
                nb, db, pb = info[b]
                if a < b and na == nb and da == db:
                    along = abs(pa[0] - pb[0]) if da in "UD" else abs(pa[1] - pb[1])
                    same = abs(pa[1] - pb[1]) if da in "UD" else abs(pa[0] - pb[0])
                    if same < 1e-6 and abs(along - 2.54) < 1e-6:
                        parent[root(a)] = root(b)
        groups = {}
        for k in info:
            groups.setdefault(root(k), []).append(k)
        for mem in groups.values():
            net, d, _ = info[mem[0]]
            pts = sorted(info[k][2] for k in mem)
            ddx, ddy, lrot = {"L": (-1, 0, 180), "R": (1, 0, 0), "U": (0, -1, 90), "D": (0, 1, 270)}[d]
            if net == "GND" and d == "D":
                ends = pts                                   # 下向き GND はピン先に直接
            elif net == "+5V" and d == "D":                  # 下向き +5V: 下へ出して左へ逃がす
                assert len(pts) == 1
                q = (pts[0][0], pts[0][1] + 2.54 * n)
                e = (q[0] - 5.08, q[1])
                s.path(pts[0], q, e)
                s.power("+5V", e)
                continue
            else:
                ends = [(px + ddx * 2.54 * n, py + ddy * 2.54 * n) for px, py in pts]
                for a, b in zip(pts, ends):
                    s.wire(a, b)
            for a, b in zip(ends, ends[1:]):
                s.wire(a, b)
            if net in ("+5V", "+3V3"):
                s.power(net, min(ends, key=lambda e: e[1]))  # 縦並びなら一番上
            elif net == "GND":
                s.power("GND", max(ends, key=lambda e: e[1]))
            else:
                s.label(ends[-1] if d in "UD" else ends[0], net, lrot)
        return pos
    return part
