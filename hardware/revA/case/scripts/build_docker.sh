set -e
cd /w/kicad
for n in ode_case_bottom ode_case_top; do
  kicad-cli pcb drc --severity-all -o $n.drc.txt $n.kicad_pcb >/dev/null || true
  mkdir -p gerber_$n
  kicad-cli pcb export gerbers -o gerber_$n/ $n.kicad_pcb >/dev/null
  kicad-cli pcb export drill -o gerber_$n/ $n.kicad_pcb >/dev/null
  (cd gerber_$n && rm -f ../${n}_gerber.zip && zip -q ../${n}_gerber.zip *)
  kicad-cli pcb render -o ${n}_top.png --side top -w 1600 -h 1200 $n.kicad_pcb >/dev/null 2>&1 || echo render-fail
  kicad-cli pcb render -o ${n}_bot.png --side bottom -w 1600 -h 1200 $n.kicad_pcb >/dev/null 2>&1 || true
done
