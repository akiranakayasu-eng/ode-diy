# ode_main rev B ケース（基板の組み合わせ・挟み込み式）の 3D 寸法モデル v0
# 出力: case_assembly.glb（組んだ姿）、case_exploded.glb（分解図）、dims.json
# 単位 mm。原点 = 底板の上面・左前の角（外形基準）。x = 幅（右へ）、y = 奥行き（奥へ）、z = 高さ（上へ）
import json, sys, numpy as np, trimesh
from trimesh.creation import box, cylinder

T = 1.6            # 基板の厚み
MB_W, MB_D = 76.0, 80.0   # 本体の大きさ（仮）
GAP_F = 0.5        # 本体の前端と前の側板のすき間（コネクタを前の板に合わせるため狭い）
GAP_S = 3.0        # 本体と左右・後ろの側板のすき間（11/11 作者の指摘で 0.5 → 3）
OVH = 2.0          # 底板・天板が側板より外へ出る量
SP_LOW = 5.0       # 底板〜本体（プラスチックスペーサー）
SP_HIGH = 35.0     # 本体上面〜天板下面（XLR の金具 30mm + 5mm）
HOLE_IN = 3.5      # 四隅の穴の中心（本体の端から）
TAB_W, TAB_N = 10.0, 2     # つめの幅と 1 辺の数
SLOT_CLR = 0.2     # 穴のすき間（つめより片側 0.1mm）

# 外形
OUT_W = MB_W + 2 * (GAP_S + T + OVH)
OUT_D = MB_D + GAP_F + GAP_S + 2 * (T + OVH)
X0 = OVH + T + GAP_S          # 本体の左端
Y0 = OVH + T + GAP_F          # 本体の前端
Z_MB = SP_LOW                 # 本体の下面
Z_MBTOP = Z_MB + T
Z_TOP = Z_MBTOP + SP_HIGH     # 天板の下面
WALL_H = Z_TOP                # 側板の本体部分の高さ（つめを除く）

COL = {
    'plate': [20, 90, 50, 255], 'main': [25, 110, 60, 255], 'wall': [30, 100, 55, 230],
    'xlr': [40, 40, 45, 255], 'rj': [190, 190, 195, 255], 'usb': [170, 170, 175, 255],
    'spacer': [235, 235, 225, 255], 'led': [255, 80, 60, 255], 'sw': [30, 30, 30, 255],
    'ic': [20, 20, 20, 255], 'jst': [245, 245, 240, 255],
}

def bx(x0, y0, z0, x1, y1, z1):
    b = box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b

def cyl_z(x, y, z0, z1, r, sections=32):
    c = cylinder(radius=r, height=z1 - z0, sections=sections)
    c.apply_translation([x, y, (z0 + z1) / 2]); return c

def cyl_y(x, z, y0, y1, r, sections=48):
    c = cylinder(radius=r, height=y1 - y0, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z]); return c

def diff(a, cutters):
    for c in cutters:
        a = a.difference(c)
    return a

def colored(m, key):
    m.visual.face_colors = COL[key]; return m

# 四隅の穴（本体・底板・天板で共通）
corner = [(X0 + HOLE_IN, Y0 + HOLE_IN), (X0 + MB_W - HOLE_IN, Y0 + HOLE_IN),
          (X0 + HOLE_IN, Y0 + MB_D - HOLE_IN), (X0 + MB_W - HOLE_IN, Y0 + MB_D - HOLE_IN)]

# 側板の位置（内側の面）
WX0 = X0 - GAP_S - T; WX1 = X0 + MB_W + GAP_S     # 左右の板の x（左板は WX0..WX0+T、右板は WX1..WX1+T）
WY0 = Y0 - GAP_F - T; WY1 = Y0 + MB_D + GAP_S     # 前後の板の y
# 前後の板は左右の板の間に入る（左右の板が全長）
FRONT_X = (WX0 + T, WX1)
SIDE_Y = (WY0, WY1 + T)

def tab_positions(a, b):
    L = b - a; return [a + L * (i + 1) / (TAB_N + 1) for i in range(TAB_N)]

def slots_for_plate(z0, z1):
    s = []
    for cx in tab_positions(*FRONT_X):
        s.append(bx(cx - TAB_W / 2 - SLOT_CLR / 2, WY0 - SLOT_CLR / 2, z0, cx + TAB_W / 2 + SLOT_CLR / 2, WY0 + T + SLOT_CLR / 2, z1))
        s.append(bx(cx - TAB_W / 2 - SLOT_CLR / 2, WY1 - SLOT_CLR / 2, z0, cx + TAB_W / 2 + SLOT_CLR / 2, WY1 + T + SLOT_CLR / 2, z1))
    for cy in tab_positions(*SIDE_Y):
        s.append(bx(WX0 - SLOT_CLR / 2, cy - TAB_W / 2 - SLOT_CLR / 2, z0, WX0 + T + SLOT_CLR / 2, cy + TAB_W / 2 + SLOT_CLR / 2, z1))
        s.append(bx(WX1 - SLOT_CLR / 2, cy - TAB_W / 2 - SLOT_CLR / 2, z0, WX1 + T + SLOT_CLR / 2, cy + TAB_W / 2 + SLOT_CLR / 2, z1))
    return s

def plate(z0, key):
    p = bx(0, 0, z0, OUT_W, OUT_D, z0 + T)
    cut = slots_for_plate(z0 - 1, z0 + T + 1) + [cyl_z(x, y, z0 - 1, z0 + T + 1, 1.6) for x, y in corner]
    return colored(diff(p, cut), key)

# コネクタ（前端に並ぶ。x は rev A の位置から左端 160 を引いた値）
# 高さは rev A 実物の実測（11/11）: XLR 上端 26（金具 30）、RJ45 15、USB-C 4
CONN = {
    'USB-C': dict(x=8.5, w=9.0, h=3.3, top=4.0, depth=7.5, protrude=0.5),
    'RJ45': dict(x=32.5, w=16.0, h=13.5, top=15.0, depth=21.0, protrude=2.0),
    'XLR': dict(x=55.5, w=26.0, h=26.0, top=26.0, depth=26.0, protrude=3.3, latch=30.0, hole_r=11.5, latch_w=7.0),
}

def connectors():
    ms = []
    zc = Z_MBTOP
    u = CONN['USB-C']; ms.append(colored(bx(X0 + u['x'] - u['w'] / 2, Y0 - u['protrude'], zc, X0 + u['x'] + u['w'] / 2, Y0 - u['protrude'] + u['depth'], zc + u['top']), 'usb'))
    r = CONN['RJ45']; ms.append(colored(bx(X0 + r['x'] - r['w'] / 2, Y0 - r['protrude'], zc, X0 + r['x'] + r['w'] / 2, Y0 - r['protrude'] + r['depth'], zc + r['top']), 'rj'))
    x = CONN['XLR']; cx = X0 + x['x']
    cz = zc + x['top'] / 2
    body = bx(cx - 13, WY0 + T + 0.3, zc, cx + 13, Y0 + 22, zc + x['top'])      # 前板の内側の本体（形は目安）
    nose = cyl_y(cx, cz, WY0 - 0.5, WY0 + T + 0.3, x['hole_r'] - 0.5)             # 前板の丸穴に入る筒
    latch = bx(cx - x['latch_w'] / 2 + 1, WY0 - 0.5, cz, cx + x['latch_w'] / 2 - 1, WY0 + 6, zc + x['latch'])
    ms += [colored(body, 'xlr'), colored(nose, 'xlr'), colored(latch, 'rj')]
    return ms

def front_cutouts():
    zc = Z_MBTOP; c = []; cl = 0.5
    u = CONN['USB-C']  # 角の丸い長円（USB-C の口の形に合わせる。11/11 作者）
    ux = X0 + u['x']; uz = zc + u['top'] - u['h'] / 2; hw = u['w'] / 2 + cl; hr = u['h'] / 2 + cl
    c.append(bx(ux - hw + hr, WY0 - 1, uz - hr, ux + hw - hr, WY0 + T + 1, uz + hr))
    c.append(cyl_y(ux - hw + hr, uz, WY0 - 1, WY0 + T + 1, hr, 32)); c.append(cyl_y(ux + hw - hr, uz, WY0 - 1, WY0 + T + 1, hr, 32))
    r = CONN['RJ45']; c.append(bx(X0 + r['x'] - r['w'] / 2 - cl, WY0 - 1, zc - 0.3, X0 + r['x'] + r['w'] / 2 + cl, WY0 + T + 1, zc + r['top'] + cl))
    x = CONN['XLR']; cx = X0 + x['x']; cz = zc + x['top'] / 2
    c.append(cyl_y(cx, cz, WY0 - 1, WY0 + T + 1, x['hole_r']))
    c.append(bx(cx - x['latch_w'] / 2, WY0 - 1, cz, cx + x['latch_w'] / 2, WY0 + T + 1, zc + x['latch'] + cl))  # 丸 + プッシュ金具の形（寸法は仮）
    return c

def wall_front_back(y, front):
    a, b = FRONT_X
    w = bx(a, y, 0, b, y + T, WALL_H)
    tabs = []
    for cx in tab_positions(a, b):
        tabs.append(bx(cx - TAB_W / 2, y, -T, cx + TAB_W / 2, y + T, 0))
        tabs.append(bx(cx - TAB_W / 2, y, WALL_H, cx + TAB_W / 2, y + T, WALL_H + T))
    for t in tabs: w = w.union(t)
    if front: w = diff(w, front_cutouts())
    return colored(w, 'wall')

def wall_side(x):
    a, b = SIDE_Y
    w = bx(x, a, 0, x + T, b, WALL_H)
    for cy in tab_positions(a, b):
        w = w.union(bx(x, cy - TAB_W / 2, -T, x + T, cy + TAB_W / 2, 0))
        w = w.union(bx(x, cy - TAB_W / 2, WALL_H, x + T, cy + TAB_W / 2, WALL_H + T))
    return colored(w, 'wall')

def main_board():
    m = bx(X0, Y0, Z_MB, X0 + MB_W, Y0 + MB_D, Z_MBTOP)
    m = diff(m, [cyl_z(x, y, Z_MB - 1, Z_MBTOP + 1, 1.6) for x, y in corner])
    parts = [colored(m, 'main')]
    parts.append(colored(bx(X0 + 30, Y0 + 52, Z_MBTOP, X0 + 44, Y0 + 66, Z_MBTOP + 1.4), 'ic'))  # MCU（目安）
    parts.append(colored(bx(X0 + 52, Y0 + 40, Z_MBTOP, X0 + 62, Y0 + 47.5, Z_MBTOP + 2.5), 'ic'))  # ADM2587E（目安）
    parts.append(colored(bx(X0 + 58, Y0 + 66, Z_MBTOP, X0 + 74, Y0 + 72, Z_MBTOP + 6), 'jst'))   # 天板への JST PH 8P（目安）
    return parts

def top_plate_parts(z0):
    p = plate(z0, 'plate')
    # 天板の LED 4 つ・ロック解除ボタン・リセット穴（位置は目安）
    led_y = Y0 + MB_D - 14
    leds = [colored(bx(X0 + 10 + i * 8 - 1, led_y - 0.6, z0 + T, X0 + 10 + i * 8 + 1, led_y + 0.6, z0 + T + 0.8), 'led') for i in range(4)]
    sw = colored(cyl_z(X0 + 52, led_y, z0 + T, z0 + T + 3.5, 1.8), 'sw')
    swb = colored(bx(X0 + 52 - 3, led_y - 3, z0 + T, X0 + 52 + 3, led_y + 3, z0 + T + 1.5), 'sw')
    p = diff(p, [cyl_z(X0 + 64, led_y, z0 - 1, z0 + T + 1, 0.75)])  # リセット穴 φ1.5
    p.visual.face_colors = COL['plate']
    jst = colored(bx(X0 + 58, Y0 + 66, z0 - 6, X0 + 74, Y0 + 72, z0), 'jst')
    return [p, sw, swb, jst] + leds

def spacers():
    s = []
    for x, y in corner:
        s.append(colored(cyl_z(x, y, 0, Z_MB, 2.75, 6), 'spacer'))
        s.append(colored(cyl_z(x, y, Z_MBTOP, Z_TOP, 2.75, 6), 'spacer'))
    return s

def build(explode=0.0):
    e = explode
    parts = {}
    parts['bottom'] = [plate(-T, 'plate')]
    parts['spacers_low'] = spacers()[0::2]
    mb = main_board() + connectors()
    parts['main'] = [m.copy().apply_translation([0, 0, e * 0.6]) for m in mb]
    parts['spacers_high'] = [m.copy().apply_translation([0, 0, e * 0.6]) for m in spacers()[1::2]]
    parts['front'] = [wall_front_back(WY0, True).apply_translation([0, -e, e * 0.3])]
    parts['back'] = [wall_front_back(WY1, False).apply_translation([0, e, e * 0.3])]
    parts['left'] = [wall_side(WX0).apply_translation([-e, 0, e * 0.3])]
    parts['right'] = [wall_side(WX1).apply_translation([e, 0, e * 0.3])]
    parts['top'] = [m.apply_translation([0, 0, e * 1.6]) for m in top_plate_parts(Z_TOP)]
    sc = trimesh.Scene()
    for k, ms in parts.items():
        for i, m in enumerate(ms):
            sc.add_geometry(m, node_name=f'{k}_{i}', geom_name=f'{k}_{i}')
    return sc

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    # glTF は y が上なので、z 上 → y 上へ回す
    R = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    for name, e in [('case_assembly', 0.0), ('case_exploded', 25.0)]:
        sc = build(e); sc.apply_transform(R)
        sc.export(f'{out}/{name}.glb')
    dims = dict(outer_w=round(OUT_W, 2), outer_d=round(OUT_D, 2), outer_h=round(Z_TOP + T + T, 2),
                main_board=[MB_W, MB_D], spacer_low=SP_LOW, spacer_high=SP_HIGH,
                wall_h_without_tabs=round(WALL_H, 2), front_back_wall_w=round(FRONT_X[1] - FRONT_X[0], 2),
                side_wall_d=round(SIDE_Y[1] - SIDE_Y[0], 2), tab=[TAB_W, T], slot=[TAB_W + SLOT_CLR, T + SLOT_CLR])
    json.dump(dims, open(f'{out}/dims.json', 'w'), ensure_ascii=False, indent=1)
    print(dims)
