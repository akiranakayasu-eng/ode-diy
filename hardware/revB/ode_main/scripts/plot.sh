#!/bin/sh
# 確認用 PDF (表と裏) を出す。docker の中で: sh scripts/plot.sh
cd "$(dirname "$0")/.."
kicad-cli pcb export pdf --mode-single --layers F.Cu,F.Courtyard,F.Silkscreen,Edge.Cuts -o place_top.pdf ode_main_revB.kicad_pcb >/dev/null 2>&1
kicad-cli pcb export pdf --mode-single --layers B.Cu,B.Silkscreen,Edge.Cuts -o place_bot.pdf ode_main_revB.kicad_pcb >/dev/null 2>&1
