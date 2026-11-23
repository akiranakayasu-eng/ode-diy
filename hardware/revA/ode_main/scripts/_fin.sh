#!/bin/bash
cd "$(dirname "$0")/.."
python3 scripts/gen_pcb.py | grep -v wxapp
kicad-cli pcb drc --format report --output drc.txt --severity-error --severity-warning ode_main.kicad_pcb >/dev/null 2>&1
grep -E '^\*\* Found' drc.txt
python3 scripts/verify_pcb.py 2>&1 | grep -v wxapp
bash scripts/render.sh
