import pcbnew, sys
sys.path.insert(0, '/w/ode_main/scripts')
from gen_pcb import SHEET_CENTER
b = pcbnew.LoadBoard('/w/ode_main/ode_main.kicad_pcb')
ox, oy = SHEET_CENTER
for ref in ('J1', 'J5', 'J11', 'J21', 'J12', 'J22', 'U11', 'U21', 'C109', 'C209'):
    fp = b.FindFootprintByReference(ref)
    for name, bb in (('crt', fp.GetCourtyard(pcbnew.F_CrtYd).BBox()), ('fab', fp.GetFpShapesBoundingBox()) if hasattr(fp,'GetFpShapesBoundingBox') else ('bb', fp.GetBoundingBox(False))):
        print(ref, name, 'x %.2f..%.2f  y %.2f..%.2f' % (bb.GetLeft()/1e6-ox, bb.GetRight()/1e6-ox, bb.GetTop()/1e6-oy, bb.GetBottom()/1e6-oy))
    for p in fp.Pads():
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            d = p.GetDrillSize()
            print('   ', ref, 'pad', p.GetNumber(), 'at %.2f,%.2f' % (p.GetPosition().x/1e6-ox, p.GetPosition().y/1e6-oy), 'drill %.2fx%.2f' % (d.x/1e6, d.y/1e6), p.GetNetname())
# 絶縁側の銅と一次側の銅の最短距離を実測 (トラック・ビア・パッド・ベタ)
iso = {k: set() for k in (1, 2)}
for k in (1, 2):
    for base in ('GND_ISO', 'GND2_PWR', 'VISO_OUT', 'VISO_IN', 'DMX_P', 'DMX_N', 'LEDA'):
        iso[k].add('/%s_%d' % (base, k))
items = []
for t in b.GetTracks():
    items.append((t.GetNetname(), t, 'trk'))
for fp in b.Footprints():
    for p in fp.Pads():
        items.append((p.GetNetname(), p, fp.GetReference()))
for z in b.Zones():
    items.append((z.GetNetname(), z, 'zone'))
def grp(n):
    for k in (1, 2):
        if n in iso[k]:
            return k
    return 0
best = {}
for i, (n1, a, r1) in enumerate(items):
    g1 = grp(n1)
    for n2, c, r2 in items[i+1:]:
        g2 = grp(n2)
        if g1 == g2 or n1 == n2 or (g1 == 0 and n2 == '') or (g2 == 0 and n1 == ''):
            continue
        if not n1 or not n2:
            continue
        if r1 in ('U11', 'U21', 'C109', 'C209') or r2 in ('U11', 'U21', 'C109', 'C209'):
            continue
        def innotch(o):
            q = o.GetPosition() if o.GetClass() != 'PCB_TRACK' else o.GetStart()
            x, y = q.x/1e6-ox, q.y/1e6-oy
            return any(nx0-0.5 <= x <= nx1+0.5 and ny0-0.5 <= y <= ny1+0.5 for nx0, ny0, nx1, ny1 in ((50.1, 43.125, 52.9, 50.875), (77.1, 43.125, 79.9, 50.875)))
        if innotch(a) or innotch(c):
            continue
        key = tuple(sorted((g1, g2)))
        if a.GetClass() == 'ZONE' or c.GetClass() == 'ZONE':
            continue
        def sh(o):
            return o.GetEffectiveShape(pcbnew.F_Cu) if o.GetClass() == 'PAD' else o.GetEffectiveShape()
        sa, sb = sh(a), sh(c)
        d = sa.GetClearance(sb) / 1e6
        def pos(o):
            q = o.GetPosition() if o.GetClass() != 'PCB_TRACK' else o.GetStart()
            return (round(q.x/1e6-ox, 2), round(q.y/1e6-oy, 2))
        if d < best.get(key, (99,))[0]:
            best[key] = (d, r1, n1, pos(a), r2, n2, pos(c))
for k, v in sorted(best.items()):
    print('最短 (ベタ除く)', k, '%.2f mm' % v[0], v[1:])
