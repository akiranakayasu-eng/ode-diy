# ode_main rev B ケース（基板の組み合わせ・挟み込み式）の 3D 寸法モデル v5（前板の RJ45・XLR の穴を F.Fab の中心に、窓をアンテナの根元の前まで、2026-11-23、本体 PCB 4 版に合わせ、左右を実物の向きに、アンテナの横と下に窓）
# 出力: case_assembly.glb（組んだ姿）、case_exploded.glb（分解図）、dims.json
# 単位 mm。原点 = 底板の上面・左前の角（外形基準）。x = 幅（右へ）、y = 奥行き（奥へ）、z = 高さ（上へ）
import json, sys, numpy as np, trimesh
from trimesh.creation import box, cylinder

T = 1.6            # 基板の厚み
MB_W, MB_D = 76.0, 84.0   # 本体の大きさ（PCB 4 版）
GAP_F = 0.5        # 本体の前端と前の側板のすき間（コネクタを前の板に合わせるため狭い）
GAP_S = 3.0        # 本体と左右の側板のすき間（11/11 作者の指摘で 0.5 → 3）
ANT_OUT = 6.0      # ESP32-S3-WROOM-1 のアンテナ部が本体の後ろの辺から外へ出る長さ（データシート図 10、PCB 4 版）
ANT_CLR = 15.0     # アンテナの後ろの空き（設計ガイド 1.4.7 の 15mm、11/23 作者の決定）
GAP_B = ANT_OUT + ANT_CLR   # 本体の後ろの辺と後ろの側板のすき間 = 21
OVH = 2.0          # 底板・天板が側板より外へ出る量
SP_LOW = 5.0       # 底板〜本体（プラスチックスペーサー）
SP_HIGH = 35.0     # 本体上面〜天板下面（XLR の金具 30mm + 5mm）
# 本体の取り付け穴 M3（PCB 4 版の KiCad の座標。原点は前から見て本体の右前の角、x は左へ、y は奥へ）
HOLES = [(3.5, 59.5), (72.5, 58.0), (72.5, 80.5), (49.5, 80.5)]
TAB_W, TAB_N = 10.0, 2     # つめの幅と 1 辺の数
SLOT_CLR = 0.2     # 穴のすき間（つめより片側 0.1mm）

# 外形
OUT_W = MB_W + 2 * (GAP_S + T + OVH)
OUT_D = MB_D + GAP_F + GAP_B + 2 * (T + OVH)   # 84 + 0.5 + 21 + 7.2 = 112.7
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
    'mod': [170, 170, 175, 255], 'ant': [210, 60, 60, 255], 'keep': [90, 160, 255, 60],
}

def bx(x0, y0, z0, x1, y1, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
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
# 本体 PCB の x（KiCad の上面図、前の辺が上）→ ケースの x（前から見て右へ）。上面図は前から見ると左右が逆なので反転する
# （v2 のチェック 中 1。前から見て左から XLR｜RJ45｜USB-C、アンテナは後ろの右）
def PX(x):
    return X0 + MB_W - x

corner = [(PX(x), Y0 + y) for x, y in HOLES]

# 側板の位置（内側の面）
WX0 = X0 - GAP_S - T; WX1 = X0 + MB_W + GAP_S     # 左右の板の x（左板は WX0..WX0+T、右板は WX1..WX1+T）
WY0 = Y0 - GAP_F - T; WY1 = Y0 + MB_D + GAP_B     # 前後の板の y
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

# アンテナの横と下の空きを取る窓（v3 チェック 中 2、11/23 作者の決定「側板と底板を切り欠く」）
# 窓の前の端は本体の後ろの辺より前（v4 チェック 中 1: アンテナの根元にもかける）
WIN_Y_BOTTOM = (Y0 + MB_D - ANT_CLR, Y0 + MB_D + GAP_B - 2.0)   # 底板: 根元から前へも 15mm（H1 のスペーサーの座 y 66.4 より後ろ）
WIN_Y_SIDE = (Y0 + MB_D - 7.6, Y0 + MB_D + GAP_B - 2.0)       # 右の側板: 下のつめ（y 69.5〜79.5）の後ろから
WIN_Y = WIN_Y_BOTTOM
WIN_X_BOTTOM = (PX(19.5) - 13.5, WX1 - 2.0)     # 底板: アンテナの左 13.5mm（下 6.6 と合わせて 15mm）から右の側板の手前 2mm まで（v4 チェック 低 1）
WIN_Z_SIDE = (0.0, Z_MBTOP + 15.0)                # 右の側板: 下の端から、アンテナの面の上 15mm まで（v4 チェック 低 1）

def plate(z0, key, window=False):
    p = bx(0, 0, z0, OUT_W, OUT_D, z0 + T)
    cut = slots_for_plate(z0 - 1, z0 + T + 1) + [cyl_z(x, y, z0 - 1, z0 + T + 1, 1.6) for x, y in corner]
    if window:
        cut.append(bx(WIN_X_BOTTOM[0], WIN_Y_BOTTOM[0], z0 - 1, WIN_X_BOTTOM[1], WIN_Y_BOTTOM[1], z0 + T + 1))
    return colored(diff(p, cut), key)

# コネクタ（前端に並ぶ。x は rev A の位置から左端 160 を引いた値）
# 高さは rev A 実物の実測（11/11）: XLR 上端 26（金具 30）、RJ45 15、USB-C 4
CONN = {
    # x は PCB 4 版の F.Fab の本体の中心（フットプリントの原点ではない。v3 チェック 中 1）
    'USB-C': dict(x=8.55, w=9.0, h=3.3, top=4.0, depth=7.5, protrude=0.5),
    'RJ45': dict(x=28.1, w=15.75, h=13.5, top=15.0, depth=21.0, protrude=-0.5),   # F.Fab x 20.23〜35.98、前の辺は基板の端から 0.5 内側
    'XLR': dict(x=59.5, w=26.0, h=26.0, top=26.0, depth=26.0, protrude=3.3, latch=30.0, hole_r=11.5, latch_w=7.0),
}

def connectors():
    ms = []
    zc = Z_MBTOP
    u = CONN['USB-C']; ms.append(colored(bx(PX(u['x']) - u['w'] / 2, Y0 - u['protrude'], zc, PX(u['x']) + u['w'] / 2, Y0 - u['protrude'] + u['depth'], zc + u['top']), 'usb'))
    r = CONN['RJ45']; ms.append(colored(bx(PX(r['x']) - r['w'] / 2, Y0 - r['protrude'], zc, PX(r['x']) + r['w'] / 2, Y0 - r['protrude'] + r['depth'], zc + r['top']), 'rj'))
    x = CONN['XLR']; cx = PX(x['x'])
    cz = zc + x['top'] / 2
    body = bx(cx - 13, WY0 + T + 0.3, zc, cx + 13, Y0 + 22, zc + x['top'])      # 前板の内側の本体（形は目安）
    nose = cyl_y(cx, cz, WY0 - 0.5, WY0 + T + 0.3, x['hole_r'] - 0.5)             # 前板の丸穴に入る筒
    latch = bx(cx - x['latch_w'] / 2 + 1, WY0 - 0.5, cz, cx + x['latch_w'] / 2 - 1, WY0 + 6, zc + x['latch'])
    ms += [colored(body, 'xlr'), colored(nose, 'xlr'), colored(latch, 'rj')]
    return ms

def front_cutouts():
    zc = Z_MBTOP; c = []; cl = 0.5
    u = CONN['USB-C']  # 角の丸い長円（USB-C の口の形に合わせる。11/11 作者）
    ux = PX(u['x']); uz = zc + u['top'] - u['h'] / 2; hw = u['w'] / 2 + cl; hr = u['h'] / 2 + cl
    c.append(bx(ux - hw + hr, WY0 - 1, uz - hr, ux + hw - hr, WY0 + T + 1, uz + hr))
    c.append(cyl_y(ux - hw + hr, uz, WY0 - 1, WY0 + T + 1, hr, 32)); c.append(cyl_y(ux + hw - hr, uz, WY0 - 1, WY0 + T + 1, hr, 32))
    r = CONN['RJ45']; c.append(bx(PX(r['x']) - r['w'] / 2 - cl, WY0 - 1, zc - 0.3, PX(r['x']) + r['w'] / 2 + cl, WY0 + T + 1, zc + r['top'] + cl))
    x = CONN['XLR']; cx = PX(x['x']); cz = zc + x['top'] / 2
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
    if x == WX1:    # アンテナ側（前から見て右）の側板に窓
        w = diff(w, [bx(x - 1, WIN_Y_SIDE[0], WIN_Z_SIDE[0] - 0.01, x + T + 1, WIN_Y_SIDE[1], WIN_Z_SIDE[1])])
    return colored(w, 'wall')

def main_board():
    m = bx(X0, Y0, Z_MB, X0 + MB_W, Y0 + MB_D, Z_MBTOP)
    m = diff(m, [cyl_z(x, y, Z_MB - 1, Z_MBTOP + 1, 1.6) for x, y in corner])
    parts = [colored(m, 'main')]
    # ESP32-S3-WROOM-1（18 × 25.5 × 3.1）: 本体の左後ろの角。アンテナ部 6mm が後ろの辺から外へ出る
    parts.append(colored(bx(PX(1.5), Y0 + MB_D - 19.5, Z_MBTOP, PX(19.5), Y0 + MB_D, Z_MBTOP + 3.1), 'mod'))
    parts.append(colored(bx(PX(1.5), Y0 + MB_D, Z_MBTOP, PX(19.5), Y0 + MB_D + ANT_OUT, Z_MBTOP + 0.8), 'ant'))
    parts.append(colored(bx(PX(25.5), Y0 + 29.5, Z_MBTOP, PX(32.5), Y0 + 36.5, Z_MBTOP + 1.4), 'ic'))  # W5500
    parts.append(colored(bx(PX(55.8), Y0 + 40.6, Z_MBTOP, PX(63.2), Y0 + 53.4, Z_MBTOP + 2.5), 'ic'))  # ADM2587E
    parts.append(colored(bx(PX(29.0), Y0 + 68.8, Z_MBTOP, PX(48.0), Y0 + 74.3, Z_MBTOP + 6), 'jst'))   # J6 天板への JST PH 8P
    return parts


def antenna_keepout():
    """アンテナの後ろ 15mm の空き（確認用の半透明の箱。部品・金属・銅を置かない）"""
    return [colored(bx(PX(1.5), Y0 + MB_D + ANT_OUT, Z_MBTOP - 3, PX(19.5), Y0 + MB_D + ANT_OUT + ANT_CLR, Z_MBTOP + 6), 'keep')]

def top_plate_parts(z0):
    p = plate(z0, 'plate')
    # 天板の LED 4 つ・ロック解除ボタン・リセット穴（位置は目安）
    led_y = Y0 + 58     # 天板の基板では裏の JST（y 68.8〜74.3）と重ならない所へ（v2 のチェック 低 1）。位置は目安
    leds = [colored(bx(X0 + 10 + i * 8 - 1, led_y - 0.6, z0 + T, X0 + 10 + i * 8 + 1, led_y + 0.6, z0 + T + 0.8), 'led') for i in range(4)]
    sw = colored(cyl_z(X0 + 52, led_y, z0 + T, z0 + T + 3.5, 1.8), 'sw')
    swb = colored(bx(X0 + 52 - 3, led_y - 3, z0 + T, X0 + 52 + 3, led_y + 3, z0 + T + 1.5), 'sw')
    p = diff(p, [cyl_z(X0 + 64, led_y, z0 - 1, z0 + T + 1, 0.75)])  # リセット穴 φ1.5
    p.visual.face_colors = COL['plate']
    jst = colored(bx(PX(29.0), Y0 + 68.8, z0 - 6, PX(48.0), Y0 + 74.3, z0), 'jst')   # 本体の J6 の真上（ケーブル 1:1）
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
    parts['bottom'] = [plate(-T, 'plate', window=True)]
    parts['spacers_low'] = spacers()[0::2]
    mb = main_board() + connectors() + antenna_keepout()
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
    dims = dict(window_y_bottom=[round(WIN_Y_BOTTOM[0], 2), round(WIN_Y_BOTTOM[1], 2)], window_y_side=[round(WIN_Y_SIDE[0], 2), round(WIN_Y_SIDE[1], 2)], window_bottom_x=[round(WIN_X_BOTTOM[0], 2), round(WIN_X_BOTTOM[1], 2)], window_side_z=[round(WIN_Z_SIDE[0], 2), round(WIN_Z_SIDE[1], 2)], outer_w=round(OUT_W, 2), outer_d=round(OUT_D, 2), outer_h=round(Z_TOP + T + T, 2), holes=HOLES, antenna_out=ANT_OUT, antenna_clear=ANT_CLR, gap_back=GAP_B,
                main_board=[MB_W, MB_D], spacer_low=SP_LOW, spacer_high=SP_HIGH,
                wall_h_without_tabs=round(WALL_H, 2), front_back_wall_w=round(FRONT_X[1] - FRONT_X[0], 2),
                side_wall_d=round(SIDE_Y[1] - SIDE_Y[0], 2), tab=[TAB_W, T], slot=[TAB_W + SLOT_CLR, T + SLOT_CLR])
    json.dump(dims, open(f'{out}/dims.json', 'w'), ensure_ascii=False, indent=1)
    print(dims)
