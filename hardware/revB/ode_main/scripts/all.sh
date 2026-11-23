#!/bin/sh
# 全部やり直す (docker kicad/kicad:10.0 の中で): geom -> route -> build -> DRC -> 照合
cd "$(dirname "$0")/.."
python3 scripts/gen_pcb.py --geom 2>&1 | grep -v wxapp || exit 1
ROUTE_TRIES=${1:-30} python3 scripts/route.py > docs/route.log 2>&1
tail -1 docs/route.log
python3 scripts/gen_pcb.py 2>&1 | grep -v wxapp
kicad-cli pcb drc --format report --output drc.txt --severity-error --severity-warning ode_main_revB.kicad_pcb >/dev/null 2>&1
grep -E '^\*\* Found' drc.txt
grep -E '^\[' drc.txt | sed 's/: .*//' | sort | uniq -c | sort -rn
python3 scripts/verify_pcb.py 2>&1 | grep -v wxapp | grep -v "島 0"
