import pcbnew, math
b=pcbnew.LoadBoard('ode_main_revB.kicad_pcb'); ox,oy=148.5-38,105-42
L=0
for t in b.GetTracks():
    if t.GetNetname()=="/1V2O" and t.Type()==pcbnew.PCB_TRACE_T: L+=pcbnew.ToMM(t.GetLength())
print("1V2O len %.1f vias %d"%(L,sum(1 for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=="/1V2O")))
vias=[t for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=="GND"]
pads=[p for f in b.Footprints() for p in f.Pads() if p.GetNetname()=="GND"]
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname()!="GND" or z.GetLayer() not in (pcbnew.F_Cu,pcbnew.B_Cu): continue
    ps=z.GetFilledPolysList(z.GetLayer())
    for i in range(ps.OutlineCount()):
        o=ps.Outline(i); bb=o.BBox(); a=abs(o.Area())/1e12
        nv=sum(1 for v in vias if ps.Contains(v.GetPosition()) and o.PointInside(v.GetPosition()))
        npd=sum(1 for p in pads if p.IsOnLayer(z.GetLayer()) and o.PointInside(p.GetPosition()))
        w,h=pcbnew.ToMM(bb.GetWidth()),pcbnew.ToMM(bb.GetHeight())
        if nv+npd<=1 or (max(w,h)>10 and nv<3):
            print(b.GetLayerName(z.GetLayer()),"frag x%.1f y%.1f %.1fx%.1f area %.1f vias %d pads %d"%(pcbnew.ToMM(bb.GetX())-ox,pcbnew.ToMM(bb.GetY())-oy,w,h,a,nv,npd))
