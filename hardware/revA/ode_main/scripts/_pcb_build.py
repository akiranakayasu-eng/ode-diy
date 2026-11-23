# ---------------------------------------------------------------- 基板を組む
def load_fp(lib, name):
    d = os.path.join(PROJ, lib + ".pretty") if lib == NAME else FPDIR + lib + ".pretty"
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise SystemExit("footprint not found: %s:%s" % (lib, name))
    fp.SetFPID(pcbnew.LIB_ID(lib, name))   # FootprintLoad は名前だけになるので付け直す
    return fp


def thermal_vias_03(fp):
    """EP のサーマルビアが 0.2mm 穴だと JLCPCB で追加料金になる。0.3mm 穴 / φ0.5 を 2×2 で置き直す (U3)。"""
    small = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
             and abs(pcbnew.ToMM(p.GetDrillSize().x) - 0.2) < 1e-3]
    if not small:
        return
    proto = small[0]
    for p in small:
        fp.Remove(p)
    for dx in (-0.6, 0.6):
        for dy in (-0.6, 0.6):
            q = pcbnew.PAD(proto)
            q.SetDrillSize(pcbnew.VECTOR2I_MM(0.3, 0.3))
            q.SetSize(pcbnew.VECTOR2I_MM(0.5, 0.5))
            q.SetFPRelativePosition(pcbnew.VECTOR2I_MM(dx, dy))
            fp.Add(q)


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
            if ref.startswith("U") and nm in tuple(GISO.values()) + tuple(G2.values()):
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


def hand_routes(b):
    out = []
    for k in range(1, NPORT + 1):
        out += g2_routes(k)[0]
    return out


def hand_vias(b):
    out = []
    for k in range(1, NPORT + 1):
        out += g2_routes(k)[1]
    return out


def primary_ok(x, y, r, m=0.3):
    """一次側 (L 字) の中か"""
    return x + r <= GX0 - m or y - r >= BY1 + m


def region_ok(net, x, y, r):
    """ビア (半径 r) を置いてよい所か: 一次側は L 字の中 (+3V3_ETH は島の中、+3V3 は島の外)、絶縁側は自分の島の中"""
    d = domain(net)
    if d == "P":
        if not primary_ok(x, y, r):
            return False
        x0, y0, x1, y1 = ETH_RECT
        inside = x0 + 0.6 <= x - r and x + r <= x1 - 0.6 and y0 + 0.6 <= y - r and y + r <= y1 - 0.6
        outside = not (x0 - 0.6 < x + r and x - r < x1 + 0.6 and y0 - 0.6 < y + r and y - r < y1 + 0.6)
        if net == V33E:
            return inside
        if net == V33:
            return outside
        return True
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
    for k, (net, (vx, vy)) in enumerate(hand_vias(b)):
        pads.append(dict(ref="HAND", pad="via%d" % k, net=net, x=vx, y=vy, w=VIA_D, h=VIA_D,
                         rot=0.0, thru=True, layers=["F", "B"]))
    g = dict(pads=pads, outline=[list(p) for p in pts], wide_nets=PWR_NETS, w_wide=W_PWR,
             w_sig=W_SIG, keepouts=keepouts(), soft_keepouts=soft_keepouts(),
             pour_nets=list(PLANES), skip_nets=[], route_groups=[], fixed_nets=list(G2.values()))
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
    for x1, y1, x2, y2, w, layer, net in r["tracks"]:
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
    x0, y0, x1, y1 = ETH_RECT
    _zone_style(_zone(b, pcbnew.In2_Cu, _rect(x0, max(y0, m), x1, y1), nets[V33E], 1))
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


