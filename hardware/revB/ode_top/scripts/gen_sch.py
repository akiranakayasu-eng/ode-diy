#!/usr/bin/env python3
"""ode_top_revB.kicad_sch を生成する (ode_main rev B の天板、2026-11-23)。

天板 = ケースの上の板 (1.6mm FR-4)。四隅の M3 スペーサーで本体の上 35mm に留める。
  J1 JST PH 8P  本体 J6 とケーブルでつなぐ (1 +3V3 / 2 GND / 3 EN_PANEL / 4 BTN_LOCK /
                5 LED_LAN / 6 LED_DMX / 7 LED_LOCK / 8 予備)。ピンの並びは本体 J6 と同じ。
  D1-D4         PWR (+3V3 から常時) / LAN / DMX / LOCK。本体の GPIO は High で点く (680R で約 2mA、rev A と同じ)
  SW1 LOCK      BTN_LOCK を GND へ (本体 IO7 の内部プルアップ)
  SW2 RESET     EN_PANEL を GND へ (本体の R79 1k を通して EN)。クリップで押す
  H1-H4         M3 取り付け穴 (本体・底板とそろえる)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = os.path.basename(PROJ)
sys.path.insert(0, HERE)
import kilib  # noqa: E402
from kilib import R0805, LED0805  # noqa: E402


def gen_lib():
    kilib.write_lib(PROJ, NAME, [
        kilib.std("Device", "R", R0805),
        kilib.std("Device", "LED", LED0805),
        kilib.std("Switch", "SW_Push", "Button_Switch_SMD:SW_SPST_TL3342"),
        kilib.std("Connector_Generic", "Conn_01x08",
                  "Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical"),
        kilib.std("Mechanical", "MountingHole", "MountingHole:MountingHole_3.2mm_M3"),
        kilib.std("power", "+3V3"),
        kilib.std("power", "GND"),
        kilib.std("power", "PWR_FLAG"),
    ])


if __name__ == "__main__":
    gen_lib()
import sch_core  # noqa: E402
from sch_core import Sheet, OUT, EXPECT  # noqa: E402


def build():
    s = Sheet()
    part = sch_core.make_part(s)

    j1 = part("J1", "Conn_01x08", "TO MAIN J6 (JST PH 8P)", 50.8, 60.96,
         {"1": "+3V3", "2": "GND", "3": "EN_PANEL", "4": "BTN_LOCK", "5": "LED_LAN", "6": "LED_DMX", "7": "LED_LOCK",
          "8": None}, ref_off=(-2.54, -12.7), val_off=(-12.7, 15.24), mirror=True, direct=("2",))
    g2 = j1["2"]                                   # GND は右へ長く出してラベルと重ねない
    s.path(g2, (g2[0] + 20.32, g2[1]))
    s.power("GND", (g2[0] + 20.32, g2[1]))
    s.text((38.1, 88.9), "J1 pin order = main board J6 (1:1 cable). 8 = spare", 1.27)

    def led(rr, dd, net, mid, lbl, x, y):
        rp = part(rr, "R", "680", x, y, {"1": net, "2": mid}, direct={"2"}, ref_off=(2.54, -2.54), val_off=(2.54, 0))
        s.label(rp["2"], mid, 0)
        part(dd, "LED", lbl, x, y + 7.62, {"2": mid, "1": "GND"}, rot=90, direct={"2"},
             ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

    led("R1", "D1", "+3V3", "LEDA_PWR", "PWR", 101.6, 45.72)
    led("R2", "D2", "LED_LAN", "LEDA_LAN", "LAN", 121.92, 45.72)
    led("R3", "D3", "LED_DMX", "LEDA_DMX", "DMX", 142.24, 45.72)
    led("R4", "D4", "LED_LOCK", "LEDA_LOCK", "LOCK", 162.56, 45.72)
    s.text((96.52, 76.2), "D1 PWR from +3V3. D2-D4 driven high by main IO4 / IO5 / IO6. 680R ~2mA (same as rev A)", 1.27)

    part("SW1", "SW_Push", "LOCK", 109.22, 99.06, {"1": "BTN_LOCK", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    part("SW2", "SW_Push", "RESET", 142.24, 99.06, {"1": "EN_PANEL", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    s.text((96.52, 109.22), "SW1 LOCK: main IO7 internal pull-up (R83/C78 on main). SW2 RESET: pressed with a clip, main R79 1k to EN", 1.27)

    for k, h in enumerate(("H1", "H2", "H3", "H4")):
        part(h, "MountingHole", "M3", 101.6 + 12.7 * k, 129.54, {}, ref_off=(2.54, -2.54), val_off=(2.54, 2.54))

    for k2, net in enumerate(("+3V3", "GND")):
        x, y = 50.8 + 17.78 * k2, 116.84
        s.power("FLAG", (x, y))
        s.wire((x, y), (x, y + 5.08))
        s.power(net, (x, y + 5.08))
    return s


if __name__ == "__main__":
    sheet = build()
    open(OUT, "w").write(sheet.render("ode_main rev B top panel: LEDs and buttons", "B", "2026-11-23",
                                      "Cable to main J6. Mounted on M3 spacers 35mm above the main board", paper="A4"))
    json.dump(EXPECT, open(os.path.join(PROJ, "docs", "expected_nets.json"), "w"), indent=1, sort_keys=True)
    print("wrote", OUT, "wires:", len(sheet.wires), "junctions:", len(sheet.junctions()))
