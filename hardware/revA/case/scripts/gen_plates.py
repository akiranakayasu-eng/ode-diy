#!/usr/bin/env python3
"""ODE-DIY ver0（ode_main rev A）のケース板 2 枚（底板・天板）の kicad_pcb を作る。
座標は ode_main.kicad_pcb と同じ（KiCad の座標そのまま、mm、y は下が奥）。
基板: x 160〜260、y 106.5（前＝USB/LAN/XLR）〜190.5（奥）。M3 穴は奥の 4 個だけ。
使い方: python3 gen_plates.py <出力フォルダ>"""
import uuid, os, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
u = lambda: str(uuid.uuid4())

# ---- 寸法
X0, X1 = 148.0, 272.0          # 板の左右（基板の左右に 12mm 張り出してサイドの柱を立てる）
Y0, Y1 = 103.2, 193.5          # 前（XLR の前面にそろえる）〜奥
R = 3.0                        # 角の丸み
PCB_H = [(163.5,168.5),(256.5,168.5),(163.5,187),(256.5,187)]   # 基板の M3 穴
SIDE_P = [(154.0,112.0),(266.0,112.0)]                          # 前の柱（基板の外、板どうしを結ぶ）
CLAMP = [(201.5,116.0),(239.0,137.0),(177.5,156.0)]             # 押さえ（基板に穴なし、上下から樹脂スペーサで挟む）
# 天板の XLR 切り欠き（J11 の外形 206.3〜232.6 × 〜126.5 に余裕。左は押さえの柱があるので 1.0mm）
XN0, XN1, XNY = 206.3-1.0, 232.6+1.5, 133.3+1.5   # XH J12 もこの切り欠きから出す
# 底板の XLR フランジ逃げ（基板の前端より前と少し後ろ）
BN0, BN1, BNY = 206.3-1.5, 232.6+1.5, 108.0

def seg(a,b,c,d): return f'(gr_line (start {a:.3f} {b:.3f}) (end {c:.3f} {d:.3f}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{u()}"))'
def arc(sx,sy,mx,my,ex,ey): return f'(gr_arc (start {sx:.3f} {sy:.3f}) (mid {mx:.3f} {my:.3f}) (end {ex:.3f} {ey:.3f}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{u()}"))'

def plate(notch):
    """外形。notch=(nx0,nx1,ny) なら前の辺に切り欠き。"""
    k = R*(1-0.70710678); s=[]
    if notch:
        nx0,nx1,ny = notch
        s += [seg(X0+R,Y0,nx0,Y0), seg(nx0,Y0,nx0,ny), seg(nx0,ny,nx1,ny), seg(nx1,ny,nx1,Y0), seg(nx1,Y0,X1-R,Y0)]
    else:
        s.append(seg(X0+R,Y0,X1-R,Y0))
    s += [seg(X1,Y0+R,X1,Y1-R), seg(X1-R,Y1,X0+R,Y1), seg(X0,Y1-R,X0,Y0+R)]
    s += [arc(X1-R,Y0,X1-k,Y0+k,X1,Y0+R), arc(X1,Y1-R,X1-k,Y1-k,X1-R,Y1),
          arc(X0+R,Y1,X0+k,Y1-k,X0,Y1-R), arc(X0,Y0+R,X0+k,Y0+k,X0+R,Y0)]
    return s

def window(x0,x1,y0,y1,r=1.0):
    k=r*(1-0.70710678)
    return [seg(x0+r,y0,x1-r,y0), seg(x1,y0+r,x1,y1-r), seg(x1-r,y1,x0+r,y1), seg(x0,y1-r,x0,y0+r),
            arc(x1-r,y0,x1-k,y0+k,x1,y0+r), arc(x1,y1-r,x1-k,y1-k,x1-r,y1),
            arc(x0+r,y1,x0+k,y1-k,x0,y1-r), arc(x0,y0+r,x0+k,y0+k,x0+r,y0)]

def hole(ref,x,y,d):
    return f'''(footprint "case:NPTH_{d}" (layer "F.Cu") (uuid "{u()}") (at {x} {y})
  (property "Reference" "{ref}" (at 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "NPTH {d}" (at 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))
  (attr exclude_from_pos_files exclude_from_bom)
  (pad "" np_thru_hole circle (at 0 0) (size {d} {d}) (drill {d}) (layers "*.Cu" "*.Mask") (uuid "{u()}"))
)'''

def text(t,x,y,size=2.0,layer="F.SilkS",just="",rot=0):
    mir = " (justify mirror)" if layer.startswith("B.") else ""
    j = f" (justify {just})" if just and not mir else mir
    a = f" {rot}" if rot else ""
    return f'(gr_text "{t}" (at {x} {y}{a}) (layer "{layer}") (uuid "{u()}") (effects (font (size {size} {size}) (thickness {size*0.15:.2f})){j}))'

def circle(x,y,r,layer):
    return f'(gr_circle (center {x} {y}) (end {x+r} {y}) (stroke (width 0.2) (type default)) (fill no) (layer "{layer}") (uuid "{u()}"))'

def rect_silk(x0,x1,y0,y1,layer):
    return [f'(gr_line (start {a} {b}) (end {c} {d}) (stroke (width 0.15) (type dash)) (layer "{layer}") (uuid "{u()}"))'
            for a,b,c,d in [(x0,y0,x1,y0),(x1,y0,x1,y1),(x1,y1,x0,y1),(x0,y1,x0,y0)]]

def board(name, items):
    hdr = f'''(kicad_pcb (version 20240108) (generator "pcbnew") (generator_version "8.0")
(general (thickness 1.6) (legacy_teardrops no))
(paper "A4")
(title_block (title "{name}") (date "2026-11-11") (rev "0") (company "ODE-DIY ver0 case"))
(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
 (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user))
(setup (pad_to_mask_clearance 0) (pcbplotparams (layerselection 0x00010fc_ffffffff) (outputformat 1) (outputdirectory "")))
(net 0 "")
'''
    with open(os.path.join(OUT, name + '.kicad_pcb'), 'w') as f:
        f.write(hdr + '\n'.join(items) + '\n)\n')

M3 = 3.2
def common_holes():
    it=[]
    for i,(x,y) in enumerate(PCB_H): it.append(hole(f"H{i+1}",x,y,M3))
    for i,(x,y) in enumerate(SIDE_P): it.append(hole(f"P{i+1}",x,y,M3))
    for i,(x,y) in enumerate(CLAMP): it.append(hole(f"C{i+1}",x,y,M3))
    return it

# ---- 底板
it = plate((BN0,BN1,BNY)) + common_holes()
it += rect_silk(160,260,108.5,190.5,"F.SilkS")                        # 基板の位置（内側の面）
it.append(text("ODE-DIY ver0 PCB", 210, 150, 2.5))
for (x,y) in PCB_H: it.append(text("5mm", x, y-4.5, 1.2))
for (x,y) in CLAMP: it.append(text("5mm NYLON", x, y+4.5, 1.0))
for (x,y) in SIDE_P: it.append(text("POST", x, y+4.5, 1.2))
for (x,y) in [(156,186),(264,186),(156,124),(264,124)]:              # ゴム足（外側の面）
    it.append(circle(x,y,5,"B.SilkS"))
it.append(text("ODE-DIY ver0  BOTTOM", 210, 165, 3, "B.SilkS"))
it.append(text("FRONT: USB / LAN / DMX", 210, 172, 2, "B.SilkS"))
board("ode_case_bottom", it)

# ---- 天板
it = plate((XN0,XN1,XNY)) + common_holes()
def win(x0,x1,y0,y1,m=1.5): return window(x0-m,x1+m,y0-m,y1+m)
it += win(214.4,218.8,181.9,189.2);  it.append(text("SWD", 216.6, 178.5, 1.5))       # J3
it += win(168.2,176.8,185.7,189.3);  it.append(text("UART", 172.5, 182.3, 1.5))      # J4
it += win(205.2,211.3,170.7,174.3);  it.append(text("BOOT0", 208.2, 167.4, 1.5))     # JP1
it.append(text("DMX (XLR / XH)", 219.7, 137.3, 1.5))   # J11・J12 は前の切り欠きの中
for ref,(x,y),lab,rot in [("L1",(168.5,163.5),"PWR",0),("L2",(234,176.5),"LOCK",0),
                          ("L3",(234,179.5),"STAT",0),("L4",(220.5,142),"ISO",0)]:
    it.append(hole(ref,x,y,2.5 if ref in ("L2","L3") else 3.0))   # L2/L3 は 3mm 間隔なので Ø2.5
    if ref in ("L2","L3"): it.append(text(lab, x-3, y, 1.3, just="right"))
    else: it.append(text(lab, x, y+3.3, 1.3))
for ref,(x,y),lab in [("S1",(238,184.5),"RESET"),("S2",(248,184.5),"LOCK")]:
    it.append(hole(ref,x,y,4.0)); it.append(text(lab, x, y+4.3, 1.5))
it.append(text("USB-C", 168.5, 118.5, 1.8))
it.append(text("LAN", 188, 132.5, 1.8))
it.append(text("ODE-DIY", 200, 152, 5))
it.append(text("Art-Net / sACN > DMX", 200, 159, 2))
board("ode_case_top", it)
print("ok")
