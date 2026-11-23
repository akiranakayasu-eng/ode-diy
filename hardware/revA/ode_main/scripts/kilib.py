#!/usr/bin/env python3
"""プロジェクト専用の .kicad_sym を作る共通部 (dmx_usb_pro/scripts/gen_lib.py を一般化)。

標準ライブラリから抽出する。extends 継承のシンボルは親を抽出して子の名前に改名する
(KiCad 内部のフラット化と完全一致させるより確実。作業メモの知見)。
環境変数 KICAD_SYMDIR で標準ライブラリの場所を差し替えられる。
"""
import os
import re

SYMDIR = os.environ.get("KICAD_SYMDIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/")

R0805 = "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
C1210 = "Capacitor_SMD:C_1210_3225Metric_Pad1.33x2.70mm_HandSolder"
L0805 = "Inductor_SMD:L_0805_2012Metric_Pad1.05x1.20mm_HandSolder"
LED0805 = "LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder"


def _f(v):
    s = ("%.4f" % round(v, 4)).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def find_block(text, name):
    m = re.search(r'\n\t\(symbol "%s"\n' % re.escape(name), text)
    if not m:
        raise SystemExit("not found: " + name)
    i = m.start() + 2
    depth, j = 0, i
    while True:
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        elif c == '"':
            j += 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
        j += 1
    return text[i:j + 1]


def set_property(blk, key, val):
    pat = re.compile(r'(\n\t\t\(property "%s" ")((?:[^"\\]|\\.)*)(")' % re.escape(key))
    out, n = pat.subn(lambda m: m.group(1) + val.replace('"', '\\"') + m.group(3), blk, count=1)
    assert n == 1, (key, blk[:60])
    return out


_cache = {}


def std(lib, sym, fp="", rename=None, value=None, desc=None, datasheet=None):
    """標準シンボル 1 個。extends なら親を抽出して sym (または rename) の名前にする。"""
    if lib not in _cache:
        _cache[lib] = open(os.path.join(SYMDIR, lib + ".kicad_sym")).read()
    blk = find_block(_cache[lib], sym)
    m = re.search(r'\(extends "([^"]+)"\)', blk)
    name = rename or sym
    if m:
        parent = m.group(1)
        blk = find_block(_cache[lib], parent)
        assert "(extends" not in blk, sym
        blk = blk.replace('(symbol "%s' % parent, '(symbol "%s' % name)
        value = value or sym
    elif rename:
        blk = blk.replace('(symbol "%s' % sym, '(symbol "%s' % name)
    if value:
        blk = set_property(blk, "Value", value)
    if fp:
        blk = set_property(blk, "Footprint", fp)
    if desc:
        blk = set_property(blk, "Description", desc)
    if datasheet:
        blk = set_property(blk, "Datasheet", datasheet)
    return "\t" + blk.rstrip() + "\n"


def box_symbol(name, ref, value, fp, desc, hw, left, right, top=(), bottom=()):
    """箱型シンボル。left/right/top/bottom は [(番号, 名前, 種別) or None(=空き)]。
    ピン端は 2.54 グリッド、長さ 2.54。hw = 本体の半幅。"""
    nlr = max(len(left), len(right))
    ht = round(((nlr - 1) * 2.54 / 2 + 2.54) / 1.27) * 1.27
    out = ['\t(symbol "%s"\n\t\t(pin_names (offset 0.508))\n\t\t(exclude_from_sim no)\n'
           '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
           '\t\t(duplicate_pin_numbers_are_jumpers no)\n' % name]
    for key, val, x, y, hide in (("Reference", ref, -hw, ht + 1.27, False),
                                 ("Value", value, -hw, -ht - 2.54, False),
                                 ("Footprint", fp, 0, 0, True),
                                 ("Datasheet", "", 0, 0, True),
                                 ("Description", desc, 0, 0, True)):
        out.append('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s'
                   '\t\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t)\n'
                   % (key, val, _f(x), _f(y), "\t\t\t(hide yes)\n" if hide else ""))
    out.append('\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start %s %s)\n\t\t\t\t(end %s %s)\n'
               '\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n'
               '\t\t\t)\n\t\t)\n' % (name, _f(-hw), _f(ht), _f(hw), _f(-ht)))
    out.append('\t\t(symbol "%s_1_1"\n' % name)

    def pin(num, pname, ptype, x, y, ang):
        out.append('\t\t\t(pin %s line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length 2.54)\n'
                   '\t\t\t\t(name "%s" (effects (font (size 1.27 1.27))))\n'
                   '\t\t\t\t(number "%s" (effects (font (size 1.27 1.27))))\n\t\t\t)\n'
                   % (ptype, _f(x), _f(y), ang, pname, num))

    for side, pins in (("L", left), ("R", right)):
        y0 = ht - 2.54
        for k, p in enumerate(pins):
            if p is None:
                continue
            x, ang = (-hw - 2.54, 0) if side == "L" else (hw + 2.54, 180)
            pin(p[0], p[1], p[2], x, y0 - 2.54 * k, ang)
    for side, pins in (("T", top), ("B", bottom)):
        x0 = -(len(pins) - 1) * 2.54 / 2
        x0 = round(x0 / 2.54) * 2.54
        for k, p in enumerate(pins):
            if p is None:
                continue
            y, ang = (ht + 2.54, 270) if side == "T" else (-ht - 2.54, 90)
            pin(p[0], p[1], p[2], x0 + 2.54 * k, y, ang)
    out.append("\t\t)\n\t)\n")
    return "".join(out)


# ADM2587E SOIC-20W (dmx_usb_pro と同じ箱型。ADI ADM2582E/ADM2587E Rev. H のピン配置)
def adm2587_symbol():
    left = [("2", "VCC", "power_in"), ("8", "VCC", "passive"), None,
            ("7", "TxD", "input"), ("6", "DE", "input"), ("5", "~{RE}", "input"),
            ("4", "RxD", "tri_state"), None]
    right = [("12", "VISOOUT", "power_out"), ("19", "VISOIN", "power_in"), None,
             ("13", "Y", "output"), ("15", "Z", "output"), ("18", "A", "input"), ("17", "B", "input")]
    return box_symbol("ADM2587E", "U", "ADM2587EBRWZ", "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm",
                      "ADM2587E isolated RS-485 transceiver with integrated isoPower DC-DC, 2.5kV, 500kbps",
                      12.7, left, right,
                      bottom=[("1", "GND1", "power_in"), ("3", "GND1", "passive"),
                              ("9", "GND1", "passive"), ("10", "GND1", "passive"), None,
                              ("11", "GND2", "power_in"), ("14", "GND2", "passive"),
                              ("16", "GND2", "passive"), ("20", "GND2", "passive")])


def xlr3_symbol():
    pins = [("1", "Common", "passive"), ("2", "Data-", "passive"), ("3", "Data+", "passive")]
    return box_symbol("XLR3F", "J", "XLR3 female", "Connector_Audio:Jack_XLR_Neutrik_NC3FAH_Horizontal",
                      "XLR 3-pin female PCB jack (DMX512: 1 = common, 2 = data-, 3 = data+)", 5.08, pins, [])


def write_lib(proj, name, blocks):
    out = ['(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "eeschema")\n'
           '\t(generator_version "10.0")\n'] + list(blocks) + [")\n"]
    open(os.path.join(proj, name + ".kicad_sym"), "w").write("".join(out))
    open(os.path.join(proj, "sym-lib-table"), "w").write(
        '(sym_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")'
        '(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr ""))\n)\n' % (name, name))
