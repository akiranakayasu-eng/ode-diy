#!/usr/bin/env python3
"""生成した基板の照合 (KiCad の python で実行。検証対象を作り直さない)。

  1. 全パッドのネット == ネットリスト、部品の Value == ネットリスト
  2. 内層ベタのネット (GND / +3V3 / +3V3_ETH) の SMD パッドに、同じネットのビアが 2.5mm 以内にある
     (+3V3_ETH のビアは島の中、+3V3 のビアは島の外)
  3. パスコン: 電源ピン -> コンデンサ の距離 (GND 側はベタ)
  4. SMD パッドの中にビアが無い
  5. Ethernet の差動対と水晶の配線長 (トラック長の合計、ビア数)
  6. 穴数 (PTH / NPTH / ビア)、内層ベタの島の数
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_pcb import (NAME, COMPS, NET, SHEET_CENTER, PLANES, ETH_RECT, V33, V33E, GND)  # noqa: E402

PROJ = os.path.dirname(HERE)
board = pcbnew.LoadBoard(os.path.join(PROJ, NAME + ".kicad_pcb"))
OX, OY = SHEET_CENTER
bad = 0


def mm(v):
    return (v.x / 1e6 - OX, v.y / 1e6 - OY)


# ---- 1 ----------------------------------------------------------------------
n = 0
for fp in board.Footprints():
    ref = fp.GetReference()
    if ref.startswith("H"):
        continue
    if COMPS[ref][0] != fp.GetValue():
        print("!! value", ref, fp.GetValue(), "!=", COMPS[ref][0]); bad += 1
    for p in fp.Pads():
        key = (ref, p.GetNumber())
        want = NET.get(key, "")
        if not p.GetNumber():
            continue
        n += 1
        if p.GetNetname() != want:
            print("!! net", key, p.GetNetname(), "!=", want); bad += 1
print("1. パッド %d 個のネットと部品の Value を照合" % n)

# ---- 2 ----------------------------------------------------------------------
vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
vpos = [(v.GetNetname(), mm(v.GetPosition())) for v in vias]
x0, y0, x1, y1 = ETH_RECT
miss = 0
for net, (x, y) in vpos:
    inside = x0 <= x <= x1 and y0 <= y <= y1
    if (net == V33E and not inside) or (net == V33 and inside):
        print("!! ビアが島の内外を間違えている", net, (x, y)); bad += 1
for fp in board.Footprints():
    pth = {p.GetNumber() for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH}
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or p.GetNetname() not in PLANES or p.GetNumber() in pth:
            continue
        px, py = mm(p.GetPosition())
        d = min((math.dist((px, py), q) for nn, q in vpos if nn == p.GetNetname()), default=99)
        if d > 2.5:
            print("!! ベタのパッドにビアが無い", fp.GetReference(), p.GetNumber(), p.GetNetname(), "%.1f" % d); miss += 1
bad += miss
print("2. 内層ベタのパッド: ビア無し %d (ビア %d 個)" % (miss, len(vias)))


# ---- 3 ----------------------------------------------------------------------
def padpos(ref, num):
    fp = board.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return mm(p.GetPosition())


DEC = [("C31", "U1", "6"), ("C32", "U1", "11"), ("C33", "U1", "19"), ("C34", "U1", "28"), ("C35", "U1", "50"),
       ("C36", "U1", "75"), ("C37", "U1", "100"), ("C28", "U1", "21"), ("C38", "U1", "49"), ("C39", "U1", "73"),
       ("C56", "U3", "1"), ("C55", "U3", "19"), ("C58", "U3", "9"), ("C53", "U3", "6"), ("C4", "U6", "1"), ("C6", "U6", "3"), ("C43", "U4", "4"),
       ("C71", "U7", "5"), ("C72", "U8", "5"), ("C73", "U9", "5")]
print("3. パスコン (電源ピン -> C の電源側パッド)")
for c, u, vp in DEC:
    v, c1 = padpos(u, vp), padpos(c, "1")
    d = math.dist(v, c1)
    print("   %-4s %s.%-3s %.1f mm%s" % (c, u, vp, d, "  !!" if d > 8.0 else ""))
    if d > 8.0:
        bad += 1

# ---- 4 ----------------------------------------------------------------------
nin = 0
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        for v in vias:
            if p.HitTest(v.GetPosition()):
                print("!! via in SMD pad", fp.GetReference(), p.GetNumber()); nin += 1
bad += nin
print("4. SMD パッドの中のビア: %d" % nin)

# ---- 5 ----------------------------------------------------------------------
print("5. 配線長 (トラック合計 / ビア)")
for net in ("/ETH_TXP", "/ETH_TXN", "/ETH_RXP", "/ETH_RXN", "/HSE_IN", "/HSE_OUT", "/X25_IN", "/X25_OUT",
            "/ETH_REF_CLK", "/PHY_REFCLK", "/SW", "/VIN"):
    L = sum(t.GetLength() / 1e6 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == net)
    nv = sum(1 for v in vias if v.GetNetname() == net)
    print("   %-13s %6.1f mm  via %d" % (net, L, nv))

# ---- 6 ----------------------------------------------------------------------
pth = npth = 0
for fp in board.Footprints():
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            pth += 1
        elif p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            npth += 1
print("6. 穴: 部品 PTH %d / NPTH %d / ビア %d" % (pth, npth, len(vias)))
for z in board.Zones():
    for L in (pcbnew.In1_Cu, pcbnew.In2_Cu):
        if z.IsOnLayer(L):
            print("   ベタ %-10s %s: 島 %d" % (z.GetNetname(), pcbnew.LayerName(L), z.GetFilledPolysList(L).OutlineCount()))
print("NG %d" % bad)
sys.exit(1 if bad else 0)
