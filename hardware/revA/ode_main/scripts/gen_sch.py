#!/usr/bin/env python3
"""ode_main.kicad_sch を生成する。

自作 ODE (ENTTEC ODE Mk2 の置き換え、Art-Net -> DMX512)。sacn_node_main を縮小した 1 枚基板。
  U1 STM32F407VGT6  Ethernet MAC + LwIP で Art-Net / HTTP / WebSocket を受け、DMX を PE0 (/PE1) から出す
                    (sacn_node と同じタイマ + DMA -> GPIOE->ODR。ファーム共通化のためピンも同じ)
  U3 LAN8742A       RMII PHY (sacn_node_main と同じ)
  J5 RJ45           Amphenol RJMG1BD3B8K1ANR
  J1 USB-C          5V 受電 (CC 5.1k x 2、PD なし)。D+/D- は PA12/PA11 (USB DFU 書き込み用)
  Q1 AO3401A        突入電流の緩和 (VBUS 側の容量を 10uF 以下にし、+5V の大容量はゲート RC でゆっくりつなぐ)
  U6 AP7361C-33E    +5V -> +3V3 LDO (1A、セラミック安定)
  ポート 1 / 2      ADM2587E 絶縁 (sacn_node_out8 / dmx_usb_pro と同じ周辺)、XLR3 + JST XH3 並列
                    1 GND / 2 Data- / 3 Data+。rev A は 2 ポート分を配置し、ポート 2 は未実装でもよい
  U7 / U8 / U9      74AHCT1G125: TX1 / TX2 / DE を 3.3V -> 5V (ADM2587E VIH = 0.7 VCC)
  SW2 LOCK          ロック解除 + 全消灯 (押したまま電源を入れると IP と PIN を初期値に戻す案)
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
NPORT = 2


def gen_lib():
    kilib.write_lib(PROJ, NAME, [
        kilib.std("Device", "R", R0805),
        kilib.std("Device", "C", C0805),
        kilib.std("Device", "LED", LED0805),
        kilib.std("Device", "FerriteBead", L0805),
        kilib.std("Device", "Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"),
        kilib.std("Device", "Crystal_GND24", XTAL),
        kilib.std("Switch", "SW_Push", "Button_Switch_SMD:SW_SPST_TL3342"),
        kilib.std("Connector", "RJ45_Amphenol_RJMG1BD3B8K1ANR"),
        kilib.std("Connector", "USB_C_Receptacle_USB2.0_16P", USBC),
        kilib.std("Connector_Generic", "Conn_02x05_Odd_Even",
                  "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical"),
        kilib.std("Connector_Generic", "Conn_01x03",
                  "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"),
        kilib.std("Connector_Generic", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),
        kilib.std("MCU_ST_STM32F4", "STM32F407VGTx"),
        kilib.std("Interface_Ethernet", "LAN8742A"),
        kilib.std("Regulator_Linear", "AP7361C-33E"),
        kilib.std("Transistor_FET", "AO3401A"),
        kilib.std("Power_Protection", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6"),
        kilib.std("74xGxx", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5"),
        kilib.std("Diode", "SM712_SOT23"),
        kilib.std("Memory_EEPROM", "24AA02E-OT", value="24AA02E48T-I/OT"),
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

# ---------------------------------------------------------------- U1 STM32F407VGT6 (LQFP-100)
MCU = {
    # 電源
    "6": "+3V3", "11": "+3V3", "19": "+3V3", "28": "+3V3", "50": "+3V3", "75": "+3V3", "100": "+3V3",
    "10": "GND", "27": "GND", "74": "GND", "99": "GND", "20": "GND", "21": "+3V3A", "22": "+3V3A",
    "49": "VCAP1", "73": "VCAP2",
    # クロック・リセット・ブート
    "12": "HSE_IN", "13": "HSE_OUT", "14": "NRST", "94": "BOOT0", "37": "BOOT1",
    # Ethernet RMII (sacn_node_main と同じ)
    "24": "ETH_REF_CLK", "25": "ETH_MDIO", "32": "ETH_CRS_DV", "16": "ETH_MDC", "33": "ETH_RXD0",
    "34": "ETH_RXD1", "48": "ETH_TX_EN", "51": "ETH_TXD0", "52": "ETH_TXD1", "53": "PHY_RST_N",
    # DMX (PE0 / PE1 = TX1 / TX2、PD8 = DE。sacn_node と同じピン)
    "97": "TX1_M", "98": "TX2_M", "88": "EN_M",
    # LED / スイッチ
    "78": "LED_LOCK", "79": "LED_STAT", "85": "BTN_LOCK",
    # USB (OTG_FS, VBUS 検出なし)
    "70": "USB_DM", "71": "USB_DP",
    # デバッグ・I2C
    "68": "UART_TX", "69": "UART_RX", "72": "SWDIO", "76": "SWCLK", "89": "SWO",
    "92": "I2C_SCL", "93": "I2C_SDA",
}
for p in range(1, 101):
    MCU.setdefault(str(p), None)
assert len(MCU) == 100

PHY = {"1": "+3V3_ETH", "19": "+3V3_ETH", "9": "+3V3", "6": "VDDCR", "25": "GND",
       "4": "X25_OUT", "5": "X25_IN", "24": "RBIAS", "2": "PHY_LED2", "3": "PHY_LED1", "10": None,
       "7": "ETH_RXD1", "8": "ETH_RXD0", "11": "ETH_CRS_DV", "12": "ETH_MDIO", "13": "ETH_MDC",
       "14": "PHY_REFCLK", "15": "PHY_RST_N", "16": "ETH_TX_EN", "17": "ETH_TXD0", "18": "ETH_TXD1",
       "20": "ETH_TXN", "21": "ETH_TXP", "22": "ETH_RXN", "23": "ETH_RXP"}

RJ = {"R1": "ETH_TXP", "R2": "ETH_TXN", "R3": "ETH_RXP", "R6": "ETH_RXN", "R4": "+3V3_ETH", "R5": "+3V3_ETH",
      "R7": None, "R8": "GND", "SH": "CHASSIS", "L1": "LED1_A", "L2": "GND", "L4": "LED2_A", "L3": "GND"}   # Amphenol dwg sheet 2: R8 = GND of the internal 75R/1000pF 2kV Bob Smith network, L1/L2 yellow, L4/L3 green


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

    # ---------------- U1 STM32F407VGT6
    part("U1", "STM32F407VGTx", "STM32F407VGT6", 203.2, 182.88, MCU, hside=20.0,
         direct=("27", "74", "99"), ref_off=(-20.32, -76.2), val_off=(5.08, -76.2))
    s.text((101.6, 287.02), "U1: PE0/PE1 = TX1/TX2 (timer-triggered DMA2 -> GPIOE->ODR, same as sacn_node), PD7 = DE (both ports, also ~RE)", 1.27)
    s.text((101.6, 289.56), "PD4 = LOCK button, PC10 = LOCK LED, PC11 = STAT LED, PA11/PA12 = USB FS (DFU, no VBUS sensing)", 1.27)
    row(66.04, 152.4, [("C31", "C", "100n", "+3V3", "GND"), ("C32", "C", "100n", "+3V3", "GND"),
                       ("C33", "C", "100n", "+3V3", "GND"), ("C34", "C", "100n", "+3V3", "GND"),
                       ("C35", "C", "100n", "+3V3", "GND"), ("C36", "C", "100n", "+3V3", "GND"),
                       ("C37", "C", "4.7u", "+3V3", "GND"), ("C38", "C", "2.2u", "VCAP1", "GND"),
                       ("C39", "C", "2.2u", "VCAP2", "GND"), ("C28", "C", "1u", "+3V3A", "GND"),
                       ("C29", "C", "100n", "+3V3A", "GND")])
    s.text((149.86, 83.82), "C31-C36 = VDD x6 + VBAT, C37 bulk, C38/C39 VCAP (2.2u low ESR), C28/C29 VDDA/VREF+", 1.27)
    part("Y1", "Crystal_GND24", "8MHz", 114.3, 142.24, {"1": "HSE_IN", "3": "HSE_OUT", "2": "GND", "4": "GND"},
         direct=("4",), ref_off=(-2.54, -5.08), val_off=(3.81, 7.62))
    row(170.18, 96.52, [("C41", "C", "18p", "HSE_IN", "GND"), ("C42", "C", "18p", "HSE_OUT", "GND"),
                        ("C40", "C", "100n", "NRST", "GND"), ("R31", "R", "10k", "BOOT0", "GND"),
                        ("R32", "R", "10k", "BOOT1", "GND")])
    s.text((86.36, 127), "Y1 8MHz HSE (CL 12pF)", 1.27)
    part("SW1", "SW_Push", "RESET", 114.3, 198.12, {"1": "NRST", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    part("SW2", "SW_Push", "LOCK", 114.3, 213.36, {"1": "BTN_LOCK", "2": "GND"}, ref_off=(-2.54, -3.81),
         val_off=(-2.54, 3.81))
    s.text((86.36, 226.06), "SW2: lock release + blackout (U1 internal pull-up). Held at power-on: reset IP/PIN", 1.27)
    part("JP1", "Conn_01x02", "BOOT0", 99.06, 241.3, {"1": "+3V3", "2": "BOOT0"}, mirror=True,
         ref_off=(-2.54, -3.81), val_off=(-7.62, 6.35))
    s.text((86.36, 254), "JP1: short at reset -> ST system bootloader (USB DFU on J1)", 1.27)
    led("R33", "D5", "LED_LOCK", "LEDA_LOCK", "LOCK", 25.4, 274.32)
    led("R34", "D6", "LED_STAT", "LEDA_STAT", "STAT", 40.64, 274.32)

    # ---------------- U3 LAN8742A + J5 RJ45 (sacn_node_main と同じ)
    part("U3", "LAN8742A", "LAN8742A-CZ", 330.2, 139.7, PHY, hside=10.0,
         ref_off=(-17.78, -33.02), val_off=(-2.54, 33.02))
    s.text((294.64, 86.36), "U3 LAN8742A RMII PHY: LED2/nINTSEL strapped L (R66) -> pin 14 = 50MHz REFCLKO", 1.27)
    s.text((294.64, 88.9), "LED1/REGOFF strapped L (R65) -> internal 1.2V regulator on. PHYAD0 = 0 (internal)", 1.27)
    part("J5", "RJ45_Amphenol_RJMG1BD3B8K1ANR", "RJMG1BD3B8K1ANR", 431.8, 139.7, RJ, hside=17.0,
         ref_off=(-20.32, -15.24), val_off=(-20.32, 17.78))
    s.text((406.4, 119.38), "J5: L1(A)/L2(K) yellow = LED1, L4(A)/L3(K) green = LED2. R8 = internal 75R/1000pF common -> GND. TCT/RCT -> +3V3_ETH (DS Fig 3-23)", 1.27)
    part("Y2", "Crystal_GND24", "25MHz", 279.4, 175.26, {"1": "X25_IN", "3": "X25_OUT", "2": "GND", "4": "GND"},
         direct=("4",), ref_off=(-2.54, -5.08), val_off=(3.81, 7.62))
    row(213.36, 279.4, [("C51", "C", "18p", "X25_IN", "GND"), ("C52", "C", "18p", "X25_OUT", "GND"),
                        ("R61", "R", "12.1k 1%", "RBIAS", "GND"), ("R62", "R", "33", "PHY_REFCLK", "ETH_REF_CLK"),
                        ("R63", "R", "1.5k", "+3V3", "ETH_MDIO"), ("R64", "R", "10k", "+3V3", "PHY_RST_N"),
                        ("R65", "R", "10k", "PHY_LED1", "GND"), ("R66", "R", "10k", "PHY_LED2", "GND"),
                        ("R67", "R", "470", "PHY_LED1", "LED1_A"), ("R68", "R", "470", "PHY_LED2", "LED2_A"),
                        ("R73", "R", "1M", "CHASSIS", "GND"),
                        ("C61", "C", "1n/2kV", "CHASSIS", "GND", C1206)])
    s.text((276.86, 231.14), "R61 RBIAS 12.1k 1%. R62 33R at REFCLKO. R63 MDIO pull-up. R73 // C61: RJ45 / USB shield to GND", 1.27)
    row(246.38, 279.4, [("R69", "R", "49.9 1%", "+3V3_ETH", "ETH_TXP"), ("R70", "R", "49.9 1%", "+3V3_ETH", "ETH_TXN"),
                        ("R71", "R", "49.9 1%", "+3V3_ETH", "ETH_RXP"), ("R72", "R", "49.9 1%", "+3V3_ETH", "ETH_RXN"),
                        ("C53", "C", "1u", "VDDCR", "GND"), ("C54", "C", "470p", "VDDCR", "GND"),
                        ("C55", "C", "100n", "+3V3_ETH", "GND"), ("C56", "C", "100n", "+3V3_ETH", "GND"),
                        ("C57", "C", "4.7u", "+3V3_ETH", "GND"), ("C58", "C", "100n", "+3V3", "GND"),
                        ("C59", "C", "100n", "+3V3_ETH", "GND"), ("C60", "C", "100n", "+3V3_ETH", "GND")])
    s.text((276.86, 264.16), "R69-R72 49.9R 1% pull-ups at the PHY. C53/C54 VDDCR, C55 VDD1A, C56 VDD2A, C57 bulk,", 1.27)
    s.text((276.86, 266.7), "C58 VDDIO, C59/C60 at J5 TCT/RCT", 1.27)

    # ---------------- EEPROM / デバッグ
    part("U4", "24AA02E-OT", "24AA02E48T-I/OT", 330.2, 299.72,
         {"1": "I2C_SCL", "3": "I2C_SDA", "4": "+3V3", "2": "GND", "5": None}, hside=5.0, direct=("5",),
         ref_off=(-7.62, -10.16), val_off=(-7.62, 12.7))
    row(325.12, 345.44, [("R37", "R", "4.7k", "+3V3", "I2C_SCL"), ("R38", "R", "4.7k", "+3V3", "I2C_SDA"),
                         ("C43", "C", "100n", "+3V3", "GND")])
    s.text((309.88, 284.48), "U4: EUI-48 MAC address (read-only area 0xFA-0xFF)", 1.27)
    part("J3", "Conn_02x05_Odd_Even", "SWD", 431.8, 299.72,
         {"1": "+3V3", "2": "SWDIO", "3": "GND", "4": "SWCLK", "5": "GND", "6": "SWO", "7": None, "8": None,
          "9": "GND", "10": "NRST"}, hside=3.0, ref_off=(-2.54, -8.89), val_off=(-2.54, 11.43))
    s.text((411.48, 284.48), "J3 Cortex Debug 10-pin (1.27mm)", 1.27)
    part("J4", "Conn_01x03", "UART", 487.68, 299.72, {"1": "GND", "2": "UART_TX", "3": "UART_RX"},
         mirror=True, fp="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
         ref_off=(-2.54, -5.08), val_off=(-2.54, 6.35))
    s.text((474.98, 284.48), "J4: 1 GND / 2 TX (PA9) / 3 RX (PA10)", 1.27)

    # ---------------- 電源: USB-C 5V -> +5V (突入緩和) -> +3V3
    USB = {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
           "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
           "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
           "A8": None, "B8": None, "SH": "CHASSIS"}
    part("J1", "USB_C_Receptacle_USB2.0_16P", "USB-C 5V", 30.48, 340.36, USB, hside=8.0,
         ref_off=(-10.16, -25.4), val_off=(-10.16, 27.94))
    s.text((12.7, 302.26), "J1 USB-C: 5V from a USB charger (>= 5V 1A). CC1/CC2 5.1k each (sink, default USB power, no PD)", 1.27)
    s.text((12.7, 304.8), "D+/D- to PA12/PA11 for USB DFU. U5 USBLC6-2SC6 ESD. VBUS side <= 10uF (C1 4.7u)", 1.27)
    row(388.62, 12.7, [("R1", "R", "5.1k", "CC1", "GND"), ("R2", "R", "5.1k", "CC2", "GND")])
    part("U5", "USBLC6-2SC6", "USBLC6-2SC6", 96.52, 340.36,
         {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "2": "GND"}, hside=5.0,
         ref_off=(-7.62, -10.16), val_off=(-7.62, 12.7))
    row(388.62, 50.8, [("F1", "Polyfuse", "PTC 1.1A/6V", "VBUS", "VBUS_F"),
                       ("C1", "C", "4.7u/10V", "VBUS_F", "GND"),
                       ("C2", "C", "1u", "VBUS_F", "Q1_G"),
                       ("R3", "R", "100k", "Q1_G", "GND")])
    part("Q1", "AO3401A", "AO3401A", 165.1, 340.36, {"1": "Q1_G", "2": "VBUS_F", "3": "+5V"},
         ref_off=(5.08, -2.54), val_off=(5.08, 2.54))
    s.text((139.7, 317.5), "Q1 P-MOS soft start: C2/R3 ramp Vgs (~20ms) so C3/C4 and ADM2587E caps charge slowly", 1.27)
    row(388.62, 106.68, [("C3", "C", "22u/10V", "+5V", "GND", C1210), ("C4", "C", "100n", "+5V", "GND"),
                         ("C5", "C", "10u/10V", "+3V3", "GND", C1210), ("C6", "C", "100n", "+3V3", "GND")])
    part("U6", "AP7361C-33E", "AP7361C-33E", 223.52, 340.36, {"1": "+5V", "2": "GND", "3": "+3V3"},
         ref_off=(-7.62, -6.35), val_off=(-7.62, 7.62))
    s.text((200.66, 325.12), "U6 AP7361C-33E: +5V -> +3V3, 1A, ceramic stable. Load ~0.25A (F407 + PHY + LEDs) -> 0.43W", 1.27)
    row(388.62, 165.1, [("FB1", "FerriteBead", "BLM21PG221SN1D", "+3V3", "+3V3A"),
                        ("FB2", "FerriteBead", "BLM21PG221SN1D", "+3V3", "+3V3_ETH")], dx=25.4)
    s.text((160.02, 406.4), "FB1: +3V3 -> +3V3A (VDDA), FB2: +3V3 -> +3V3_ETH (PHY analog)", 1.27)
    led("R29", "D4", "+3V3", "LEDA_PWR", "PWR", 241.3, 384.81)

    # ---------------- 3.3V -> 5V バッファ (TX1 / TX2 / DE)
    for k, (ref, a, y) in enumerate((("U7", "TX1_M", "TXD_1"), ("U8", "TX2_M", "TXD_2"), ("U9", "EN_M", "DE"))):
        x = 297.18 + 55.88 * k
        part(ref, "74AHCT1G125", "74AHCT1G125", x, 368.3, {"1": "GND", "2": a, "3": "GND", "4": y, "5": "+5V"},
             hside=5.0, ref_off=(-5.08, -7.62), val_off=(-5.08, 10.16))
        part("C%d" % (71 + k), "C", "100n", x + 17.78, 393.7, {"1": "+5V", "2": "GND"}, **RC)
    part("R74", "R", "10k", 297.18 + 55.88 * 2 + 30.48, 393.7, {"1": "EN_M", "2": "GND"}, **RC)
    s.text((287.02, 350.52), "U7/U8/U9 74AHCT1G125 (VIH 2.0V at 5V): TX1/TX2/DE to 5V logic for ADM2587E. R74 keeps DE low until U1 runs", 1.27)

    # ---------------- ポート 1 / 2 (sacn_node_out8 のポートと同じ)
    for k in range(1, NPORT + 1):
        X, Y = 60.96 + (k - 1) * 152.4, 459.74
        n = lambda base: "%s_%d" % (base, k)  # noqa: E731
        s.text((X - 22.86, Y - 25.4), "PORT %d%s" % (k, "" if k == 1 else " (optional, may be left unpopulated)"), 2.54)
        adm = {"2": "+5V", "8": "+5V", "7": n("TXD"), "6": "DE", "5": "DE", "4": None,
               "12": n("VISO_OUT"), "19": n("VISO_IN"), "13": n("DMX_P"), "18": n("DMX_P"),
               "15": n("DMX_N"), "17": n("DMX_N"),
               "1": "GND", "3": "GND", "9": "GND", "10": "GND",
               "11": n("GND2_PWR"), "14": n("GND2_PWR"), "16": n("GND_ISO"), "20": n("GND_ISO")}
        part("U%d1" % k, "ADM2587E", "ADM2587EBRWZ", X, Y, adm, hside=14.0,
             ref_off=(-12.7, -13.97), val_off=(-12.7, 24.13))
        row(Y + 50.8, X - 25.4, [("C%d01" % k, "C", "100n", "+5V", "GND"),
                                 ("C%d02" % k, "C", "10n", "+5V", "GND"),
                                 ("C%d03" % k, "C", "100n", "+5V", "GND"),
                                 ("C%d04" % k, "C", "10u", "+5V", "GND")])
        s.text((X - 27.94, Y + 66.04), "C%d01/C%d02 VCC 2, C%d03/C%d04 VCC 8" % (k, k, k, k), 1.27)
        row(Y + 86.36, X - 25.4, [("C%d05" % k, "C", "100n", n("VISO_OUT"), n("GND2_PWR")),
                                  ("C%d06" % k, "C", "10u", n("VISO_OUT"), n("GND2_PWR")),
                                  ("C%d07" % k, "C", "100n", n("VISO_IN"), n("GND_ISO")),
                                  ("C%d08" % k, "C", "10n", n("VISO_IN"), n("GND_ISO")),
                                  ("C%d09" % k, "C", "1n/2kV", n("GND_ISO"), "GND", C1206)])
        s.text((X - 27.94, Y + 101.6), "C%d05/06 VISOOUT 12, C%d07/08 VISOIN 19, C%d09 stitching" % (k, k, k), 1.27)
        part("FB%d01" % k, "FerriteBead", "BLM21PG221SN1D", X + 38.1, Y + 43.18,
             {"1": n("VISO_OUT"), "2": n("VISO_IN")}, rot=90, ref_off=(-2.54, -3.81), val_off=(-6.35, 5.08))
        part("FB%d02" % k, "FerriteBead", "BLM21PG221SN1D", X + 38.1, Y + 60.96,
             {"1": n("GND2_PWR"), "2": n("GND_ISO")}, rot=90, ref_off=(-2.54, -3.81), val_off=(-6.35, 5.08))
        part("D%d1" % k, "SM712_SOT23", "SM712", X + 50.8, Y + 10.16,
             {"1": n("DMX_P"), "2": n("DMX_N"), "3": n("GND_ISO")},
             ref_off=(-2.54, -5.08), val_off=(-10.16, 5.08))
        part("J%d1" % k, "XLR3F", "DMX %d (XLR3 F)" % k, X + 86.36, Y - 7.62,
             {"1": n("GND_ISO"), "2": n("DMX_N"), "3": n("DMX_P")},
             ref_off=(-5.08, -6.35), val_off=(-5.08, 7.62))
        part("J%d2" % k, "Conn_01x03", "DMX %d (JST XH 3P)" % k, X + 86.36, Y + 20.32,
             {"1": n("GND_ISO"), "2": n("DMX_N"), "3": n("DMX_P")},
             ref_off=(-2.54, -5.08), val_off=(-2.54, 6.35))
        s.text((X + 63.5, Y + 30.48), "J%d1 / J%d2: 1 GND_ISO, 2 Data-, 3 Data+" % (k, k), 1.27)
        rp = part("R%d01" % k, "R", "1k", X + 63.5, Y + 78.74, {"1": n("VISO_IN"), "2": n("LEDA")},
                  direct={"2"}, **RC)
        s.label(rp["2"], n("LEDA"), 0)
        part("D%d2" % k, "LED", "ISO", X + 63.5, Y + 86.36, {"2": n("LEDA"), "1": n("GND_ISO")}, rot=90,
             direct={"2"}, ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
        # ERC: フェライト経由の電源と GND2 はソースが無いので旗を立てる
        for j, net in enumerate((n("VISO_IN"), n("GND2_PWR"), n("GND_ISO"))):
            fx, fy = X - 25.4 + 17.78 * j, Y + 116.84
            s.power("FLAG", (fx, fy))
            s.wire((fx, fy), (fx, fy + 5.08))
            s.label((fx, fy + 5.08), net, 0)

    # ---------------- PWR_FLAG (+3V3 は U6 が出すので立てない)
    for k, net in enumerate(("VBUS", "+5V", "+3V3A", "+3V3_ETH", "VDDCR", "CHASSIS", "GND")):
        x, y = 381.0 + 17.78 * k, 444.5
        s.power("FLAG", (x, y))
        s.wire((x, y), (x, y + 5.08))
        if net in ("GND", "+5V"):
            s.power(net, (x, y + 5.08))
        else:
            s.label((x, y + 5.08), net, 0)
    return s


if __name__ == "__main__":
    sheet = build()
    open(OUT, "w").write(sheet.render("ode_main: Art-Net to DMX512 node (ENTTEC ODE Mk2 replacement)", "A", "2026-10-25",
                                      "STM32F407VGT6 + LAN8742A RMII, USB-C 5V, 2x ADM2587E isolated DMX (port 2 optional)",
                                      paper="A1"))
    json.dump(EXPECT, open(os.path.join(PROJ, "docs", "expected_nets.json"), "w"), indent=1, sort_keys=True)
    print("wrote", OUT, "wires:", len(sheet.wires), "junctions:", len(sheet.junctions()))
