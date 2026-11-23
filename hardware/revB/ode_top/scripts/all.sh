#!/bin/sh
# docker kicad/kicad:10.0 の中で: 基板を作り直し → DRC → 本体との照合 → 確認図
cd "$(dirname "$0")/.."
python3 scripts/gen_pcb.py 2>&1 | grep -v -e wxapp -e Debug
kicad-cli pcb drc --format report --output drc.txt --severity-error --severity-warning --schematic-parity ode_top_revB.kicad_pcb >/dev/null 2>&1
grep -E '^\*\* Found' drc.txt
python3 scripts/verify_pcb.py ../ode_main/ode_main_revB.kicad_pcb 2>&1 | grep -v -e wxapp -e Debug > verify_pcb.txt; tail -1 verify_pcb.txt
for s in top bottom; do kicad-cli pcb render --side $s --width 1800 --height 2200 --zoom 1.0 --quality high --background opaque -o render_$s.png ode_top_revB.kicad_pcb >/dev/null 2>&1; done
kicad-cli pcb export pdf --mode-single --layers F.Cu,F.Silkscreen,F.Courtyard,Edge.Cuts -o place_top.pdf ode_top_revB.kicad_pcb >/dev/null 2>&1
kicad-cli pcb export pdf --mode-single --layers B.Cu,B.Silkscreen,B.Courtyard,Edge.Cuts -o place_bot.pdf ode_top_revB.kicad_pcb >/dev/null 2>&1
