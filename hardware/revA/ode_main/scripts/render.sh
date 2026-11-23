#!/bin/bash
cd "$(dirname "$0")/.."
for s in top bottom; do kicad-cli pcb render --side $s --width 2400 --height 1700 --zoom 1.0 --quality high --background opaque -o render_$s.png ode_main.kicad_pcb >/dev/null 2>&1; done
ls -la render_*.png
