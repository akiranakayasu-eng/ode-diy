#!/usr/bin/env python3
"""ode_main_revB.kicad_sch を生成する (ESP32-S3 Wi-Fi 一体版、2026-11-19)。

自作 ODE rev B。rev A (STM32F407 + LAN8742A) から MCU と LAN を替えた。
  U1 ESP32-S3-WROOM-1-N16R8  Wi-Fi + Art-Net/sACN + HTTP/WebSocket。USB-C から直接書き込み (USB Serial/JTAG)
  U3 W5500                   SPI Ethernet (SPI2/FSPI の IO_MUX ピン IO10-13)。WIZnet W5500-Ref-RJ45WithMag に合わせる
  J5 RJ45                    Amphenol RJMG1BD3B8K1ANR (rev A と同じ。TCT/RCT が別ピン)
  J1 USB-C                   5V 受電 (CC 5.1k x 2) + D+/D- を U1 IO20/IO19 へ
  U6 MCP1826S-3302           +5V -> +3V3 1A
  ポート 1                   ADM2587E 絶縁、XLR3 + JST XH3 並列 (rev A と同じ)。DMX 1 系統のみ
  J6 JST PH 8P               天板 (LED_LAN / LED_DMX / LED_LOCK / LOCK ボタン / EN)
出典: ESP32-S3-WROOM-1 データシート v1.2 (表 3, 4, 6, 図 7)、W5500 データシート v1.0.5、
      WIZnet W5500-Ref-RJ45WithMag (w5500_sch_v110_use_mag_.pdf)。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = os.path.basename(PROJ)
sys.path.insert(0, HERE)
import kilib  # noqa: E402
from kilib import R0805, C0805, C1206, C1210, L0805, LED0805  # noqa: E402

XTAL = "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"
USBC = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
FUSE0805 = "Fuse:Fuse_0805_2012Metric_Pad1.15x1.40mm_HandSolder"   # rev A の F1 は 1206 パターンに 0805 品だった


def gen_lib():
    kilib.write_lib(PROJ, NAME, [
        kilib.std("Device", "R", R0805),
        kilib.std("Device", "C", C0805),
        kilib.std("Device", "LED", LED0805),
        kilib.std("Device", "FerriteBead", L0805),
        kilib.std("Device", "Polyfuse", FUSE0805),
        kilib.std("Device", "Crystal_GND24", XTAL),
        kilib.std("Switch", "SW_Push", "Button_Switch_SMD:SW_SPST_TL3342"),
        kilib.std("Connector", "RJ45_Amphenol_RJMG1BD3B8K1ANR"),
        kilib.std("Connector", "USB_C_Receptacle_USB2.0_16P", USBC),
        kilib.std("Connector_Generic", "Conn_01x03",
                  "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"),
        kilib.std("Connector_Generic", "Conn_01x08",
                  "Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical"),
        kilib.std("RF_Module", "ESP32-S3-WROOM-1", value="ESP32-S3-WROOM-1-N16R8"),
        kilib.std("Interface_Ethernet", "W5500"),
        kilib.std("Regulator_Linear", "MCP1826S", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
                  value="MCP1826ST-3302E/DB"),
        kilib.std("Transistor_FET", "AO3401A"),
        kilib.std("Power_Protection", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6"),
        kilib.std("74xGxx", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5"),
        kilib.std("Diode", "SM712_SOT23"),
        kilib.std("power", "+5V"),
        kilib.std("power", "+3V3"),
        kilib.std("power", "GND"),
        kilib.std("power", "PWR_FLAG"),
        kilib.adm2587_symbol(),
        kilib.xlr3_symbol(),
    ])


if __name__ == "__main__":
    gen_lib()               # sch_core は import 時に .kicad_sym を読むので先に書く
import sch_core  # noqa: E402
from sch_core import Sheet, OUT, EXPECT  # noqa: E402

RC = dict(ref_off=(2.54, -1.27), val_off=(2.54, 1.27))

# ---------------------------------------------------------------- U1 ESP32-S3-WROOM-1-N16R8 (モジュールのピン番号)
MCU = {
    "1": "GND", "40": "GND", "41": "GND", "2": "+3V3", "3": "EN",
    "4": "LED_LAN_M", "5": "LED_DMX_M", "6": "LED_LOCK_M", "7": "BTN_LOCK_M",    # IO4-IO7 天板
    "8": None, "9": None,                     # IO15 IO16 予備
    "10": "TX_U", "11": "LED_STAT",           # IO17 = U1TXD (DMX)、IO18 = STAT (起動時のグリッチがあるので DE には使わない)
    "12": None,                               # IO8 予備
    "13": "USB_DM_M", "14": "USB_DP_M",       # IO19 / IO20 (R4 / R5 0R を通す、チェック低 3)
    "15": None,                               # IO3 (JTAG 選択の起動ピン) 何もつながない
    "16": None,                               # IO46 (起動ピン、内部プルダウン) 何もつながない
    "17": "ETH_RST_N",                        # IO9
    "18": "ETH_CS_N", "19": "ETH_MOSI", "20": "ETH_SCLK", "21": "ETH_MISO",   # IO10-IO13 (FSPI IO_MUX)
    "22": "ETH_INT_N",                        # IO14
    "23": "DE_M",                             # IO21 = DE (起動時のグリッチが無いピン、チェック低 1)
    "24": None, "25": None,                   # IO47 IO48 予備
    "26": None,                               # IO45 (起動ピン VDD_SPI、内部プルダウン = 3.3V) 何もつながない
    "27": "BOOT",                             # IO0
    "28": None, "29": None, "30": None,       # IO35-37 は Octal PSRAM が使う (N16R8)
    "31": None, "32": None, "33": None, "34": None, "35": None,   # IO38-42 予備
    "36": "UART_RX", "37": "UART_TX_M",       # RXD0 = IO44、TXD0 = IO43 (R77 499R を通す、チェック低 5)
    "38": "CC2_ADC", "39": "CC1_ADC",                 # IO2 = ADC1_CH1 / IO1 = ADC1_CH0 で CC の電圧を読む (電源の強さ、チェック低 8)
}
assert len(MCU) == 41

# ---------------------------------------------------------------- U3 W5500 (LQFP-48)
ETH = {
    "1": "ETH_TXN", "2": "ETH_TXP", "5": "ETH_RXN", "6": "ETH_RXP",
    "4": "+3V3A", "8": "+3V3A", "11": "+3V3A", "15": "+3V3A", "17": "+3V3A", "21": "+3V3A",
    "3": "GND", "9": "GND", "14": "GND", "16": "GND", "19": "GND", "48": "GND", "29": "GND",
    "28": "+3V3",
    "7": None, "12": None, "13": None, "46": None, "47": None,           # DNC / NC
    "10": "EXRES1", "18": None, "20": "TOCAP", "22": "1V2O",
    "23": "GND", "38": None, "39": None, "40": None, "41": None, "42": None,   # 23 RSVD は DS 表 2 で GND 必須 (チェック中 1)、38-42 は NC
    "24": None, "26": None, "25": "LINKLED", "27": "ACTLED",            # SPDLED / DUPLED は使わない
    "30": "X25_IN", "31": "X25_XO",
    "32": "ETH_CS_N", "33": "ETH_SCLK_W", "34": "ETH_MISO", "35": "ETH_MOSI", "36": "ETH_INT_N", "37": "ETH_RST_N",
    "43": None, "44": None, "45": None,       # PMODE2-0: 内部プルアップ = 111 (全対応、オートネゴ)
}
assert len(ETH) == 48

# J5: R1 TD+ / R2 TD- / R3 RD+ / R6 RD- / R4 TCT / R5 RCT / R8 = 内部 75R 終端の共通点 (rev A で GND)
RJ = {"R1": "ETH_TXP", "R2": "ETH_TXN", "R3": "ETH_RDP", "R6": "ETH_RDN", "R4": "ETH_TCT", "R5": "ETH_RCT",
      "R7": None, "R8": "GND", "SH": "CHASSIS",
      "L1": "+3V3", "L2": "LEDK_ACT", "L4": "+3V3", "L3": "LEDK_LINK"}   # L1/L2 黄 = ACT、L4/L3 緑 = LINK (W5500 の LED は Low で点く)


def build():
    s = Sheet()
    part = sch_core.make_part(s)

    def row(y, x0, items, dx=12.7):
        """2 ピン部品 (縦置き: 1 = 上、2 = 下) を横一列に。item = (ref, lib, value, net1, net2[, fp[, rot]])"""
        for k, it in enumerate(items):
            ref, lib, val, a, b = it[:5]
            fp = it[5] if len(it) > 5 else None
            rot = it[6] if len(it) > 6 else 0
            part(ref, lib, val, x0 + dx * k, y, {"1": a, "2": b}, fp=fp, rot=rot, **RC)

    def led(rr, dd, net, mid, lbl, x, y, rval="680"):
        rp = part(rr, "R", rval, x, y, {"1": net, "2": mid}, direct={"2"}, ref_off=(2.54, -2.54), val_off=(2.54, 0))
        s.label(rp["2"], mid, 0)
        part(dd, "LED", lbl, x, y + 7.62, {"2": mid, "1": "GND"}, rot=90, direct={"2"},
             ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

    # ---------------- U1 ESP32-S3-WROOM-1-N16R8
    part("U1", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R8", 203.2, 160.02, MCU, hside=10.0,
         ref_off=(-15.24, -38.1), val_off=(2.54, -38.1))
    s.text((154.94, 220.98), "U1 ESP32-S3-WROOM-1-N16R8 (Akizuki 117256, TELEC 201-220052). IO35-37 used by octal PSRAM.", 1.27)
    s.text((154.94, 223.52), "Strapping: IO0 = BOOT (SW3), IO46 / IO45 / IO3 left open (internal pull-down / floating, defaults).", 1.27)
    s.text((154.94, 226.06), "IO10-13 = FSPI (IO_MUX) to W5500, IO17 = U1TXD (DMX), IO21 = DE, IO4-7 = top panel, IO18 = STAT, IO1/IO2 = CC1/CC2 ADC", 1.27)
    s.text((154.94, 228.6), "Antenna: keep module antenna (18 x 6 mm) outside the board edge, >= 15 mm clearance in the case", 1.27)
    row(66.04, 160.02, [("C31", "C", "22u", "+3V3", "GND", C1210), ("C32", "C", "100n", "+3V3", "GND"),
                        ("C33", "C", "1u", "EN", "GND"), ("R31", "R", "10k", "+3V3", "EN"),
                        ("R32", "R", "10k", "+3V3", "BOOT")])
    s.text((157.48, 83.82), "C31/C32 at module 3V3 (DS fig 7: 22u + 0.1u). R31/C33 EN RC delay 10k/1u (DS fig 7). R32 BOOT pull-up", 1.27)
    part("SW1", "SW_Push", "RESET", 114.3, 142.24, {"1": "EN", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    part("SW3", "SW_Push", "BOOT", 114.3, 160.02, {"1": "BOOT", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    s.text((76.2, 246.38), "SW3 BOOT: hold while releasing RESET -> download boot (IO0 = 0, IO46 = 0, DS table 6)", 1.27)
    led("R34", "D6", "LED_STAT", "LEDA_STAT", "STAT", 40.64, 274.32)
    led("R29", "D4", "+3V3", "LEDA_PWR", "PWR", 25.4, 274.32)

    # ---------------- J6 天板 (JST PH 8P)
    j6 = part("J6", "Conn_01x08", "TOP PANEL (JST PH 8P)", 99.06, 205.74,
              {"1": "+3V3", "2": "GND", "3": "EN_PANEL", "4": "BTN_LOCK", "5": "LED_LAN", "6": "LED_DMX", "7": "LED_LOCK",
               "8": None}, mirror=True, ref_off=(-2.54, -12.7), val_off=(-12.7, 15.24), direct=("2",))
    g2 = j6["2"]                                   # GND は右へ長く出してラベルの外に置く (3 版チェック低 3)
    s.path(g2, (g2[0] + 20.32, g2[1]))
    s.power("GND", (g2[0] + 20.32, g2[1]))
    s.text((76.2, 238.76), "J6 to top panel: 1 +3V3 / 2 GND / 3 EN_PANEL (reset via R79 1k, clip hole) / 4 LOCK button (to GND, U1 pull-up)", 1.27)
    s.text((76.2, 241.3), "5 LED_LAN / 6 LED_DMX / 7 LED_LOCK (active high, series R + LED on the panel) / 8 spare", 1.27)

    # ---------------- U3 W5500 + J5 RJ45 (WIZnet W5500-Ref-RJ45WithMag)
    part("U3", "W5500", "W5500", 330.2, 152.4, ETH, hside=15.0,
         ref_off=(-22.86, -40.64), val_off=(-2.54, 40.64))
    s.text((294.64, 101.6), "U3 W5500 SPI Ethernet (mode 0/3, up to 80MHz). PMODE2-0 open = 111 auto-negotiation (internal pull-ups)", 1.27)
    s.text((294.64, 104.14), "3V3A via FB2. 1V2O 10n, TOCAP 4.7u, EXRES1 12.4k 1%. RSTn >= 500us low (R64 pull-up)", 1.27)
    part("J5", "RJ45_Amphenol_RJMG1BD3B8K1ANR", "RJMG1BD3B8K1ANR", 469.9, 152.4, RJ, hside=17.0,
         ref_off=(-20.32, -15.24), val_off=(-20.32, 17.78))
    s.text((444.5, 129.54), "J5: L4(A)/L3(K) green = LINK, L1(A)/L2(K) yellow = ACT (W5500 LEDs active low). R8 = internal 75R common -> GND", 1.27)
    s.text((444.5, 132.08), "TX: TXP/TXN 49.9R to 3V3A, TCT 10R from 3V3A + 22n. RX: 49.9R x2 at W5500 side to RCT (10n to GND), then 6.8n AC coupling to RD+/RD-", 1.27)
    part("Y2", "Crystal_GND24", "25MHz", 279.4, 187.96, {"1": "X25_IN", "3": "X25_OUT", "2": "GND", "4": "GND"},
         direct=("4",), ref_off=(-2.54, -5.08), val_off=(3.81, 7.62))
    row(220.98, 271.78, [("C51", "C", "18p", "X25_IN", "GND"), ("C52", "C", "18p", "X25_OUT", "GND"),
                         ("R60", "R", "1M", "X25_IN", "X25_XO"),
                         ("R61", "R", "12.4k 1%", "EXRES1", "GND"),
                         ("C53", "C", "10n", "1V2O", "GND"), ("C54", "C", "4.7u", "TOCAP", "GND"),
                         ("R64", "R", "10k", "+3V3", "ETH_RST_N"), ("R65", "R", "10k", "+3V3", "ETH_INT_N"),
                         ("R66", "R", "10k", "+3V3", "ETH_CS_N"),
                         ("R67", "R", "330", "LEDK_LINK", "LINKLED"), ("R68", "R", "330", "LEDK_ACT", "ACTLED"),
                         ("R73", "R", "1M", "CHASSIS", "GND"),
                         ("C61", "C", "1n/2kV", "CHASSIS", "GND", C1206)])
    s.text((444.5, 220.98), "Y2 25MHz (CL 18pF), R60 1M across. R66 keeps W5500 deselected while U1 boots. R73 // C61: RJ45 / USB shield", 1.27)
    row(264.16, 271.78, [("R69", "R", "49.9 1%", "+3V3A", "ETH_TXP"), ("R70", "R", "49.9 1%", "+3V3A", "ETH_TXN"),
                        ("R75", "R", "10 1%", "+3V3A", "ETH_TCT"), ("C62", "C", "22n", "ETH_TCT", "GND"),
                        ("C63", "C", "6.8n", "ETH_RXP", "ETH_RDP"), ("C64", "C", "6.8n", "ETH_RXN", "ETH_RDN"),
                        ("R71", "R", "49.9 1%", "ETH_RXP", "ETH_RCT"), ("R72", "R", "49.9 1%", "ETH_RXN", "ETH_RCT"),
                        ("C65", "C", "10n", "ETH_RCT", "GND")])
    row(302.26, 271.78, [("C55", "C", "100n", "+3V3A", "GND"), ("C56", "C", "100n", "+3V3A", "GND"),
                         ("C57", "C", "100n", "+3V3A", "GND"), ("C58", "C", "100n", "+3V3A", "GND"),
                         ("C59", "C", "100n", "+3V3A", "GND"), ("C60", "C", "100n", "+3V3A", "GND"),
                         ("C66", "C", "10u", "+3V3A", "GND"), ("C67", "C", "10u", "+3V3", "GND"),
                         ("C68", "C", "100n", "+3V3", "GND")])
    s.text((269.24, 320.04), "C55-C60 at AVDD 4/8/11/15/17/21, C66 3V3A bulk, C67/C68 at VDD 28", 1.27)

    # ---------------- チェック (2026-11-19) を受けて足した部品
    row(259.08, 393.7, [("R76", "R", "0", "ETH_SCLK", "ETH_SCLK_W"), ("C69", "C", "DNP", "ETH_SCLK_W", "GND"),
                       ("R62", "R", "0", "X25_OUT", "X25_XO"), ("R4", "R", "0", "USB_DP", "USB_DP_M"),
                       ("R5", "R", "0", "USB_DM", "USB_DM_M"), ("R77", "R", "499", "UART_TX_M", "UART_TX"),
                       ("R78", "R", "10k", "+3V3", "TX_M"), ("R79", "R", "1k", "EN", "EN_PANEL")])
    row(287.02 + 30.48, 393.7, [("R80", "R", "22k", "CC1", "CC1_ADC"), ("C74", "C", "100n", "CC1_ADC", "GND"),
                       ("R81", "R", "22k", "CC2", "CC2_ADC"), ("C75", "C", "100n", "CC2_ADC", "GND"),
                       ("C76", "C", "DNP", "USB_DP", "GND"), ("C77", "C", "DNP", "USB_DM", "GND"),
                       ("R82", "R", "0", "TX_U", "TX_M")])
    row(287.02 + 78.74, 393.7, [("R83", "R", "1k", "BTN_LOCK", "BTN_LOCK_M"), ("C78", "C", "100n", "BTN_LOCK_M", "GND"),
                       ("R84", "R", "100", "LED_LAN_M", "LED_LAN"), ("R85", "R", "100", "LED_DMX_M", "LED_DMX"),
                       ("R86", "R", "100", "LED_LOCK_M", "LED_LOCK"), ("R87", "R", "10k", "+3V3", "BTN_LOCK_M")])
    s.text((391.16, 388.62), "R83 1k + C78 100n: panel LOCK button to IO7 (ESD, debounce). R84-R86 100R: panel LED lines (cable to touchable panel). R87 10k pull-up [PCB check 1 low 11]", 1.27)
    s.text((391.16, 340.36), "R80/R81 22k + C74/C75 100n: CC to ADC through series R (ESD, boot glitch) [check 2 mid 1]. C76/C77 USB caps DNP, connector side of R4/R5 [HDG USB fig]. R82 UART1 TX series [HDG UART]", 1.27)
    s.text((391.16, 289.56), "R76/C69 SCLK series 0R + cap (DNP) [HDG SPI]. R62 XO series 0R [W5500 fig 3]. R4/R5 USB series 0R [HDG USB]", 1.27)
    s.text((391.16, 292.1), "R77 499R in U0TXD [HDG UART]. R78 TX idle high while U1 boots. R79 1k decouples EN from the panel cable [HDG CHIP_PU]", 1.27)

    # ---------------- デバッグ
    j4 = part("J4", "Conn_01x03", "UART", 487.68, 299.72, {"1": "GND", "2": "UART_TX", "3": "UART_RX"},
              mirror=True, fp="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
              ref_off=(-2.54, -5.08), val_off=(-2.54, 6.35), direct=("1",))
    g1 = j4["1"]                                   # GND は右へ長く出してラベルの外に置く (チェック 2 低 4)
    s.path(g1, (g1[0] + 20.32, g1[1]))
    s.power("GND", (g1[0] + 20.32, g1[1]))
    s.text((469.9, 284.48), "J4: 1 GND / 2 TX (TXD0 IO43) / 3 RX (RXD0 IO44) log", 1.27)

    # ---------------- 電源: USB-C 5V -> +5V (突入緩和) -> +3V3 (rev A と同じ)
    USB = {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
           "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
           "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
           "A8": None, "B8": None, "SH": "CHASSIS"}
    part("J1", "USB_C_Receptacle_USB2.0_16P", "USB-C 5V", 30.48, 340.36, USB, hside=8.0,
         ref_off=(-10.16, -25.4), val_off=(-10.16, 27.94))
    s.text((12.7, 302.26), "J1 USB-C: 5V >= 1.5A charger for Wi-Fi use. CC1/CC2 5.1k each (sink, no PD)", 1.27)
    s.text((12.7, 304.8), "D+/D- to U1 USB (IO20/IO19) for flashing and log. U5 USBLC6-2SC6 ESD. VBUS side <= 10uF (C1 4.7u)", 1.27)
    row(388.62, 12.7, [("R1", "R", "5.1k", "CC1", "GND"), ("R2", "R", "5.1k", "CC2", "GND")])
    part("U5", "USBLC6-2SC6", "USBLC6-2SC6", 96.52, 340.36,
         {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "2": "GND"}, hside=5.0,
         ref_off=(-7.62, -10.16), val_off=(-7.62, 12.7))
    row(388.62, 50.8, [("F1", "Polyfuse", "PICOSMDC110S-2", "VBUS", "VBUS_F"),
                       ("C1", "C", "4.7u/10V", "VBUS_F", "GND"),
                       ("C2", "C", "1u", "VBUS_F", "Q1_G"),
                       ("R3", "R", "100k", "Q1_G", "GND")])
    part("Q1", "AO3401A", "AO3401A", 165.1, 340.36, {"1": "Q1_G", "2": "VBUS_F", "3": "+5V"},
         ref_off=(5.08, -2.54), val_off=(5.08, 2.54))
    s.text((139.7, 317.5), "Q1 P-MOS soft start: C2/R3 ramp Vgs so C3/C4 and ADM2587E caps charge slowly", 1.27)
    row(388.62, 106.68, [("C3", "C", "22u/10V", "+5V", "GND", C1210), ("C4", "C", "100n", "+5V", "GND"),
                         ("C5", "C", "10u/10V", "+3V3", "GND", C1210), ("C6", "C", "100n", "+3V3", "GND")])
    part("U6", "MCP1826S", "MCP1826ST-3302E/DB", 223.52, 340.36, {"1": "+5V", "2": "GND", "3": "+3V3"},
         ref_off=(-7.62, -6.35), val_off=(-7.62, 7.62))
    s.text((200.66, 325.12), "U6 MCP1826 +5V -> +3V3 1A. Load: U1 peak 355mA (DS table 12) + W5500 ~128mA + LEDs", 1.27)
    part("FB2", "FerriteBead", "BLM21PG221SN1D", 165.1, 388.62, {"1": "+3V3", "2": "+3V3A"}, **RC)
    s.text((160.02, 406.4), "FB2: +3V3 -> +3V3A (W5500 AVDD)", 1.27)

    # ---------------- 3.3V -> 5V バッファ (TX / DE)
    for k, (ref, a, y) in enumerate((("U7", "TX_M", "TXD_1"), ("U9", "DE_M", "DE"))):
        x = 297.18 + 55.88 * k
        part(ref, "74AHCT1G125", "74AHCT1G125", x, 368.3, {"1": "GND", "2": a, "3": "GND", "4": y, "5": "+5V"},
             hside=5.0, ref_off=(-5.08, -7.62), val_off=(-5.08, 10.16))
        part("C%d" % (71 + 2 * k), "C", "100n", x + 17.78, 393.7, {"1": "+5V", "2": "GND"}, **RC)
    part("R74", "R", "10k", 297.18 + 55.88 + 30.48, 393.7, {"1": "DE_M", "2": "GND"}, **RC)
    s.text((287.02, 350.52), "U7/U9 74AHCT1G125: TX/DE to 5V logic for ADM2587E. R74 keeps DE low until U1 runs", 1.27)

    # ---------------- ポート 1 (rev A と同じ)
    k = 1
    X, Y = 60.96, 459.74
    n = lambda base: "%s_%d" % (base, k)  # noqa: E731
    s.text((X - 22.86, Y - 25.4), "DMX PORT 1", 2.54)
    adm = {"2": "+5V", "8": "+5V", "7": n("TXD"), "6": "DE", "5": "DE", "4": None,
           "12": n("VISO_OUT"), "19": n("VISO_IN"), "13": n("DMX_P"), "18": n("DMX_P"),
           "15": n("DMX_N"), "17": n("DMX_N"),
           "1": "GND", "3": "GND", "9": "GND", "10": "GND",
           "11": n("GND2_PWR"), "14": n("GND2_PWR"), "16": n("GND_ISO"), "20": n("GND_ISO")}
    part("U11", "ADM2587E", "ADM2587EBRWZ", X, Y, adm, hside=14.0,
         ref_off=(-12.7, -13.97), val_off=(-12.7, 24.13))
    row(Y + 50.8, X - 25.4, [("C101", "C", "100n", "+5V", "GND"),
                             ("C102", "C", "10n", "+5V", "GND"),
                             ("C103", "C", "100n", "+5V", "GND"),
                             ("C104", "C", "10u", "+5V", "GND")])
    s.text((X - 27.94, Y + 66.04), "C101/C102 VCC 2, C103/C104 VCC 8", 1.27)
    row(Y + 86.36, X - 25.4, [("C105", "C", "100n", n("VISO_OUT"), n("GND2_PWR")),
                              ("C106", "C", "10u", n("VISO_OUT"), n("GND2_PWR")),
                              ("C107", "C", "100n", n("VISO_IN"), n("GND_ISO")),
                              ("C108", "C", "10n", n("VISO_IN"), n("GND_ISO")),
                              ("C109", "C", "1n/2kV", n("GND_ISO"), "GND", C1206)])
    s.text((X - 27.94, Y + 101.6), "C105/06 VISOOUT 12, C107/08 VISOIN 19, C109 stitching", 1.27)
    part("FB101", "FerriteBead", "BLM21PG221SN1D", X + 38.1, Y + 43.18,
         {"1": n("VISO_OUT"), "2": n("VISO_IN")}, rot=90, ref_off=(-2.54, -3.81), val_off=(-6.35, 5.08))
    part("FB102", "FerriteBead", "BLM21PG221SN1D", X + 38.1, Y + 60.96,
         {"1": n("GND2_PWR"), "2": n("GND_ISO")}, rot=90, ref_off=(-2.54, -3.81), val_off=(-6.35, 5.08))
    part("D11", "SM712_SOT23", "SM712", X + 50.8, Y + 10.16,
         {"1": n("DMX_P"), "2": n("DMX_N"), "3": n("GND_ISO")},
         ref_off=(-2.54, -5.08), val_off=(-10.16, 5.08))
    part("J11", "XLR3F", "DMX 1 (XLR3 F)", X + 86.36, Y - 7.62,
         {"1": n("GND_ISO"), "2": n("DMX_N"), "3": n("DMX_P")},
         ref_off=(-5.08, -6.35), val_off=(-5.08, 7.62))
    part("J12", "Conn_01x03", "DMX 1 (JST XH 3P)", X + 86.36, Y + 20.32,
         {"1": n("GND_ISO"), "2": n("DMX_N"), "3": n("DMX_P")},
         ref_off=(-2.54, -5.08), val_off=(-2.54, 6.35))
    s.text((X + 63.5, Y + 30.48), "J11 / J12: 1 GND_ISO, 2 Data-, 3 Data+", 1.27)
    rp = part("R101", "R", "1k", X + 63.5, Y + 78.74, {"1": n("VISO_IN"), "2": n("LEDA")},
              direct={"2"}, **RC)
    s.label(rp["2"], n("LEDA"), 0)
    part("D12", "LED", "ISO", X + 63.5, Y + 86.36, {"2": n("LEDA"), "1": n("GND_ISO")}, rot=90,
         direct={"2"}, ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
    for j, net in enumerate((n("VISO_IN"), n("GND2_PWR"), n("GND_ISO"))):
        fx, fy = X - 25.4 + 17.78 * j, Y + 116.84
        s.power("FLAG", (fx, fy))
        s.wire((fx, fy), (fx, fy + 5.08))
        s.label((fx, fy + 5.08), net, 0)

    # ---------------- PWR_FLAG (+3V3 は U6 が出すので立てない)
    for k2, net in enumerate(("VBUS", "+5V", "+3V3A", "CHASSIS", "GND")):
        x, y = 381.0 + 17.78 * k2, 444.5
        s.power("FLAG", (x, y))
        s.wire((x, y), (x, y + 5.08))
        if net in ("GND", "+5V"):
            s.power(net, (x, y + 5.08))
        else:
            s.label((x, y + 5.08), net, 0)
    return s


if __name__ == "__main__":
    sheet = build()
    open(OUT, "w").write(sheet.render("ode_main rev B: Art-Net / sACN to DMX512 node, Wi-Fi + Ethernet", "B", "2026-11-19",
                                      "ESP32-S3-WROOM-1-N16R8 + W5500 SPI Ethernet, USB-C 5V, ADM2587E isolated DMX x1",
                                      paper="A1"))
    json.dump(EXPECT, open(os.path.join(PROJ, "docs", "expected_nets.json"), "w"), indent=1, sort_keys=True)
    print("wrote", OUT, "wires:", len(sheet.wires), "junctions:", len(sheet.junctions()))
