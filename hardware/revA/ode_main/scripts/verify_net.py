#!/usr/bin/env python3
"""netlist.net (kicad-cli sch export netlist --format kicadsexpr) を
docs/expected_nets.json (gen_sch.py が書く設計意図) とピン単位で突き合わせる。

  - 意図したネットに入っているか (ラベル名の先頭 "/" は無視)
  - None (未接続) のピンが単独ネットか
  - 意図に無いピンや、1 ピンしか無いラベルネットが無いか
"""
import json
import os
import re
import sys
from collections import defaultdict

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exp = json.load(open(os.path.join(PROJ, "docs", "expected_nets.json")))
text = open(os.path.join(PROJ, "netlist.net")).read()

got, members = {}, defaultdict(list)
section = text[text.index("(nets"):]
for chunk in re.split(r"\n\s*\(net\s*\n", section)[1:]:
    name = re.search(r'\(name "([^"]*)"\)', chunk).group(1).lstrip("/")
    for r, p in re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', chunk):
        if r.startswith("#"):
            continue
        got["%s.%s" % (r, p)] = name
        members[name].append("%s.%s" % (r, p))

err = 0
for key, net in sorted(exp.items()):
    g = got.get(key)
    if net is None:
        if g is not None and len(members[g]) > 1:
            print("NG  %-8s should be unconnected, in %s %s" % (key, g, members[g])); err += 1
    elif g != net:
        print("NG  %-8s expected %-10s got %s" % (key, net, g)); err += 1
for key in sorted(set(got) - set(exp)):
    print("NG  %-8s not in design intent (net %s)" % (key, got[key])); err += 1
for name, mem in sorted(members.items()):
    if len(mem) == 1 and not name.startswith("unconnected") and not name.startswith("Net-"):
        print("NG  net %s has only %s" % (name, mem)); err += 1
nets = sorted(n for n in members if not n.startswith("unconnected"))
print("pins %d / nets %d / errors %d" % (len(got), len(nets), err))
for n in nets:
    print("  %-10s %s" % (n, " ".join(sorted(members[n]))))
sys.exit(1 if err else 0)
