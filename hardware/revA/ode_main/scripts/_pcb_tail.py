def labels(b):
    out = []
    L = pcbnew.GR_TEXT_H_ALIGN_LEFT
    for k in range(1, NPORT + 1):
        c = cx(k)
        out.append(silk(b, "DMX %d" % k, c, 22.0, 1.0))
        for j, s in enumerate(("G", "D-", "D+")):
            out.append(silk(b, s, c + 4.0 - 2.5 * j, 27.6, 0.8))
        out.append(silk(b, "ISO", c + 1.0, 33.6, 0.8))
    out.append(silk(b, "ISOLATION 2.5kV", 73.0, YS + 5.3, 0.8))
    out.append(silk(b, "USB-C 5V", 2.0, 9.0, 0.8, 90))
    out.append(silk(b, "ETH", 39.5, 12.0, 1.0, 90))
    out.append(silk(b, "PWR", 8.5, 59.3, 0.8))
    out.append(silk(b, "SWD", 59.6, 79.0, 0.8, 90))
    out.append(silk(b, "G T R", 67.0, 80.5, 0.8, 90))
    out.append(silk(b, "BOOT0", 44.5, 66.0, 0.8, 90))
    out.append(silk(b, "RESET", 78.0, 82.4, 0.8))
    out.append(silk(b, "LOCK", 88.0, 82.4, 0.8))
    out.append(silk(b, "LOCK", 78.5, 70.0, 0.8, 0, L))
    out.append(silk(b, "STAT", 78.5, 73.0, 0.8, 0, L))
    out.append(silk(b, NAME + " A", 85.0, 66.5, 1.0))
    out.append(silk(b, "Art-Net to DMX512", 85.0, 68.5, 0.8))
    return out


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
    b.Save(OUT)
    write_pro()
    write_dru()
    print("-> %s  トラック %d / ビア %d / スティッチ %d / 参照記号 %d%s"
          % (OUT, nt, nv, ns, n_ref, (" / 置けない %s" % bad) if bad else ""))


if __name__ == "__main__":
    main()
