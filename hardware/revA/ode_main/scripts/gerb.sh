#!/bin/bash
set -e
B=ode_main
cd /w/$B; rm -rf fab; mkdir -p fab
L=F.Cu,B.Cu,In1.Cu,In2.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts
kicad-cli pcb export gerbers --output fab/ --check-zones --layers $L $B.kicad_pcb >/dev/null
kicad-cli pcb export drill --output fab/ --format excellon --drill-origin absolute --excellon-units mm --excellon-separate-th $B.kicad_pcb >/dev/null
ls fab | tr '\n' ' '; echo
cd fab; rm -f ../${B}_revA_gerber.zip; python3 -c "import zipfile,os; z=zipfile.ZipFile('../${B}_revA_gerber.zip','w',zipfile.ZIP_DEFLATED); [z.write(f) for f in sorted(os.listdir('.'))]"
ls -la ../${B}_revA_gerber.zip
