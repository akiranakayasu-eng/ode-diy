#!/bin/sh
# kicad-cli (docker kicad/kicad:10.0) で ERC・ネットリスト・PDF を出し、設計意図と照合する
cd "$(dirname "$0")"
chmod -R a+rwX .
docker run --rm -v "$PWD":/w -w /w kicad/kicad:10.0 sh -c 'kicad-cli sch erc --severity-all --format report -o erc.rpt ode_top_revB.kicad_sch; kicad-cli sch export netlist --format kicadsexpr -o netlist.net ode_top_revB.kicad_sch; kicad-cli sch export pdf -o ode_top_revB.pdf ode_top_revB.kicad_sch' 2>&1 | tail -5
python3 scripts/verify_net.py > verify.txt; grep -E "^NG|errors" verify.txt | head -60
grep -cE "^\[" erc.rpt; grep -E "^\[" erc.rpt | sort | uniq -c
