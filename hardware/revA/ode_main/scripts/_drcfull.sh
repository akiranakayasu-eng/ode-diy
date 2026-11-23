#!/bin/bash
# 全部やり直す: geom -> route -> build -> DRC。引数: ROUTE_TRIES
cd "$(dirname "$0")/.."
python3 scripts/_cy.py | grep -v wxapp
python3 scripts/gen_pcb.py --geom | grep -v wxapp || exit 1
ROUTE_TRIES=${1:-40} python3 scripts/route.py > docs/route.log 2>&1
tail -1 docs/route.log; grep "^  FAIL" docs/route.log | tail -5
python3 scripts/gen_pcb.py | grep -v wxapp
kicad-cli pcb drc --format report --output drc.txt --severity-error --severity-warning sacn_node_main.kicad_pcb >/dev/null 2>&1
grep -E '^\*\* Found' drc.txt
grep -E '^\[' drc.txt | sed 's/: .*//' | sort | uniq -c | sort -rn
