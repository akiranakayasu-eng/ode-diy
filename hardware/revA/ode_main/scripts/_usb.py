import pcbnew
b=pcbnew.LoadBoard('/w/ode_main/ode_main.kicad_pcb')
for n in ('/USB_DP','/USB_DM','/X25_IN','/X25_OUT'):
    L=sum(t.GetLength()/1e6 for t in b.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetNetname()==n)
    v=sum(1 for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()==n)
    print(n, round(L,1), 'via', v)
