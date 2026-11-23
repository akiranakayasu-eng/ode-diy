import pcbnew
b=pcbnew.LoadBoard('ode_main_revB.kicad_pcb'); ox,oy=148.5-38,105-42
vias=[t for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=="GND"]
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname()!="GND" or z.GetLayer()!=pcbnew.B_Cu: continue
    ps=z.GetFilledPolysList(pcbnew.B_Cu)
    for i in range(ps.OutlineCount()):
        o=ps.Outline(i); bb=o.BBox()
        if pcbnew.ToMM(bb.GetHeight())>15 and pcbnew.ToMM(bb.GetWidth())<3:
            print("frag", pcbnew.ToMM(bb.GetX())-ox, pcbnew.ToMM(bb.GetY())-oy, pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
            for v in vias:
                if o.PointInside(v.GetPosition()): print("  via", pcbnew.ToMM(v.GetPosition().x)-ox, pcbnew.ToMM(v.GetPosition().y)-oy)
            # width profile
            for y in range(int(pcbnew.ToMM(bb.GetY())-oy), int(pcbnew.ToMM(bb.GetBottom())-oy)+1, 2):
                xs=[x/20 for x in range(160,200) if o.PointInside(pcbnew.VECTOR2I(pcbnew.FromMM(x/20+ox),pcbnew.FromMM(y+oy)))]
                print("  y",y, (min(xs),max(xs)) if xs else None)
