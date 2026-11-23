#!/usr/bin/env python3
"""天板 PCB の照合 (KiCad の python で): J1.n と J6.n のネット (ケーブルは n 番どうし) と、J1.n が J6.n の真上か、M3 穴、つめの穴、外形。
  python3 scripts/verify_pcb.py ../ode_main/ode_main_revB.kicad_pcb
"""
import math
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pcb as G  # noqa: E402

top = pcbnew.LoadBoard(os.path.join(G.PROJ, G.NAME + ".kicad_pcb"))
main = pcbnew.LoadBoard(sys.argv[1])
TOFF = G.SHEET_CENTER
MOFF = (148.5 - 76.0 / 2, 105.0 - 84.0 / 2)
ng = 0


def mm(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def bare(n):
    if not n or n.startswith("unconnected"):
        return ""
    return n.lstrip("/")


j6 = {}
for p in main.FindFootprintByReference("J6").Pads():
    x, y = mm(p.GetPosition())
    j6[p.GetNumber()] = (x - MOFF[0], y - MOFF[1], p.GetNetname())
j1 = top.FindFootprintByReference("J1")
print("J1 は裏:", j1.IsFlipped())
for p in sorted(j1.Pads(), key=lambda q: int(q.GetNumber())):
    x, y = mm(p.GetPosition())
    x, y = x - TOFF[0], y - TOFF[1]
    xm, ym = G.X0 + G.MB_W - x, G.H - G.Y0 - y          # 天板 → 本体の座標
    hit = [(k, v) for k, v in j6.items() if math.hypot(v[0] - xm, v[1] - ym) < 0.01]
    k, v = hit[0] if hit else ("-", (0, 0, ""))
    n = p.GetNumber()
    same = bare(j6[n][2]) == bare(p.GetNetname())                      # ケーブルの線 n でつながる相手
    above = bool(hit) and k == n
    ok = same and above
    ng += not ok
    print("%s J1.%s %-10s ← ケーブルの線 %s → J6.%s %-12s / 真下は J6.%s" % ("OK" if ok else "NG", n, p.GetNetname() or "(なし)", n, n, j6[n][2] or "(なし)", k))


def bodybox(fp, layers):
    bbs = [it.GetBoundingBox() for it in fp.GraphicalItems() if it.GetLayer() in layers]
    return (min(pcbnew.ToMM(b.GetLeft()) for b in bbs), min(pcbnew.ToMM(b.GetTop()) for b in bbs),
            max(pcbnew.ToMM(b.GetRight()) for b in bbs), max(pcbnew.ToMM(b.GetBottom()) for b in bbs))


mb = bodybox(main.FindFootprintByReference("J6"), (pcbnew.F_Fab,))
tb = bodybox(j1, (pcbnew.B_Fab,))
my = sorted((G.H - G.Y0 - (mb[1] - MOFF[1]), G.H - G.Y0 - (mb[3] - MOFF[1])))
ty = (tb[1] - TOFF[1], tb[3] - TOFF[1])
row = G.J1_AT[1]
print("参考 本体 (F.Fab) の前後の範囲 (列から): J6 の真上 %.2f〜%.2f / J1 %.2f〜%.2f (広い側が逆 = J6 を並びの軸のまわりに裏返した向き)"
      % (my[0] - row, my[1] - row, ty[0] - row, ty[1] - row))

mh = sorted((round(mm(f.GetPosition())[0] - MOFF[0], 2), round(mm(f.GetPosition())[1] - MOFF[1], 2))
            for f in main.Footprints() if f.GetReference().startswith("H"))
th = sorted((round(G.X0 + G.MB_W - (mm(f.GetPosition())[0] - TOFF[0]), 2), round(G.H - G.Y0 - (mm(f.GetPosition())[1] - TOFF[1]), 2))
            for f in top.Footprints() if f.GetReference().startswith("H"))
ok = mh == th
ng += not ok
print("%s M3 穴 (本体の座標で) 本体 %s / 天板 %s" % ("OK" if ok else "NG", mh, th))
bb = top.GetBoardEdgesBoundingBox()
print("外形 %.2f x %.2f (case_model v5: %.1f x %.1f)" % (pcbnew.ToMM(bb.GetWidth()) - 0.1, pcbnew.ToMM(bb.GetHeight()) - 0.1, G.W, G.H))
for cx, cy, d in G.slots():
    print("  つめの穴 中心 (%.2f, %.2f) %s 長円 %.1f x %.1f (10.2 x 1.8 の長方形が入る)" % (cx, cy, "横" if d == "x" else "縦", G.SLOT_L + G.SLOT_W if d == "x" else G.SLOT_W, G.SLOT_W if d == "x" else G.SLOT_L + G.SLOT_W))
print("NG", ng)
