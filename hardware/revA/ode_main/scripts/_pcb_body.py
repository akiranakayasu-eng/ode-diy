#!/usr/bin/env python3
"""ode_main の基板を生成する (KiCad の python で実行。sacn_node_main と sacn_node_out8 の gen_pcb.py を合わせたもの)。

  $KIPY scripts/gen_pcb.py --geom     配置と外形を docs/geom.json に出す (ルータ用)
  python3 scripts/route.py            0.25mm グリッドの A* 迷路ルータ (表裏 2 層だけ使う)
  $KIPY scripts/gen_pcb.py            docs/routes.json を流し込んで基板を保存

100 x 84mm 4 層 FR-4 1.6mm。上辺 (箱の前面) に左から USB-C J1、RJ45 J5、XLR3 J11 / J21 を並べる。
一次側は L 字: 左の列 (x < GX0、上から下まで) と、絶縁帯の下 (y > BY1、全幅)。
  F.Cu / B.Cu が信号、In1.Cu が GND ベタ、In2.Cu が +3V3 ベタ (RJ45 / PHY の区画だけ +3V3_ETH の島)。
  GND / +3V3 / +3V3_ETH の SMD パッドは隣にビアを 1 個ずつ打って内層へ落とす (sacn_node_main と同じ)。
右上はポート 1 / 2 の絶縁側の島 (sacn_node_out8 のポートと同じ寸法、27mm ピッチ)。島は 4 層とも GND_ISO_k。
  島の間・左 (縦の帯) と島の下 (横の帯 y = BY0 .. BY1) は 4 層ともトラック・ビア・ベタ禁止。
  ADM2587E (Uk1) は帯を跨ぎ、帯を渡るのは Ck09 (1nF 2kV) だけ (切り欠き NOTCH_k)。
PHY まわり (左上) と MCU まわり (左下) は sacn_node_main の配置を 270 度回して流用。
LQFP の 0.5mm ピッチを通すため、クリアランス 0.15 / 信号 0.2 / ビア 0.5-0.3 (sacn_node_main と同じ)。
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
import pcbnew  # noqa: E402

NAME = os.path.basename(PROJ)
FPDIR = os.environ.get("KICAD_FPDIR", "/usr/share/kicad/footprints/")
GEOM = os.path.join(PROJ, "docs", "geom.json")
ROUTES = os.path.join(PROJ, "docs", "routes.json")
OUT = os.path.join(PROJ, NAME + ".kicad_pcb")

W, H = 100.0, 84.0
W_SIG, W_PWR = 0.2, 0.5
CLR, EDGE_CLR = 0.15, 0.5
VIA_D, VIA_DRILL = 0.5, 0.3
NPORT = 2
GND = "GND"
V33, V33E, V33A = "+3V3", "/+3V3_ETH", "/+3V3A"
SHEET_CENTER = (210.0 - W / 2, 148.5 - H / 2)   # A3 横の中央へ

# ---- ポートの格子 (sacn_node_out8 と同じ寸法)
PITCH = 27.0
XK0 = 46.0                              # ポート 1 の列の左端
GAP = 7.5                               # 一次側 <-> 絶縁側、ポート間の銅の最短 (カスタム DRC ルール)
BAND = 7.75
YS = 47.0                               # Uk1 の中心 y = 帯の中心
BY0, BY1 = YS - BAND / 2, YS + BAND / 2   # 43.125 / 50.875
GX0 = XK0 - BAND / 2                    # 左の列 (一次側) の右端 = 縦の帯の左端 42.125
ETH_RECT = (11.0, 0.0, 41.5, 33.8)      # In2 の +3V3_ETH の島 (x0, y0, x1, y1)
HOLES = [(3.5, H - 3.5), (W - 3.5, H - 3.5), (W - 3.5, 62.0), (3.5, 62.0)]


def col(k):
    return XK0 + PITCH * (k - 1)


def cx(k):
    return col(k) + 13.5


def island(k):
    return col(k) + BAND / 2, col(k) + PITCH - BAND / 2


def notch(k):
    return (cx(k) - 9.4, BY0, cx(k) - 6.6, BY1)


C09X = lambda k: cx(k) - 8.0    # noqa: E731


def iso_nets(k):
    return {"/%s_%d" % (b, k) for b in ("GND_ISO", "GND2_PWR", "VISO_OUT", "VISO_IN", "DMX_P", "DMX_N", "LEDA")}


GISO = {k: "/GND_ISO_%d" % k for k in range(1, NPORT + 1)}
G2 = {k: "/GND2_PWR_%d" % k for k in range(1, NPORT + 1)}
PLANES = (GND, V33, V33E) + tuple(GISO.values())
PWR_NETS = ["/VBUS", "/VBUS_F", "+5V", V33A, "/VDDCR"] + ["/VISO_OUT_%d" % k for k in range(1, NPORT + 1)] \
    + ["/VISO_IN_%d" % k for k in range(1, NPORT + 1)] + list(G2.values())
NO_STITCH = {"C%d09" % k for k in range(1, NPORT + 1)}


