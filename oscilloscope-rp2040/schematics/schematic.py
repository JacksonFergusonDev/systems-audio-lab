from pathlib import Path

import schemdraw
import schemdraw.elements as elm

schemdraw.theme("default")


# ==========================================
# 1. GLOBAL CONFIGURATION
# ==========================================


# --- Component Values & Types ---
COMPONENT_CONFIG = {
    # Input Stage
    "R_PROT_VAL": "10k",
    "C_AC_VAL": "220nF\n(Socket)",
    # Attenuator (Voltage Divider)
    "R_DIV1_VAL": "10k\n(Socket)",
    "R_DIV2_VAL": "10k\n(Socket)",
    # Bias Network
    "R_INJ_VAL": "220k\n(Socket)",
    "V_MID_VAL": "\n(1.65V)",
    "R_BIAS_TOP_VAL": "100k",
    "R_BIAS_BOT_VAL": "100k",
    "C_FILT_VAL": "10uF",
    # Protection / Clamp
    "R_CLAMP_VAL": "10k",
    "D_CLAMP_TYPE": "1N4148",
    # Voltage Rails
    "V_DD_VAL": "3.3V",
}


# --- Output Filenames ---
BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# Define base names for easier multi-format exporting
BASE_NAME_COMPACT = "signal_conditioning_universal-compact"
BASE_NAME_BLOCKED = "signal_conditioning_universal-blocked"


# --- Title Configuration ---
TITLE_TEXT_COMPACT = "Universal RP2040 Analog Interface"
TITLE_TEXT_BLOCKED = "Universal RP2040\nAnalog Interface"


TITLE_SIZE_COMPACT = 16
TITLE_POS_COMPACT = (6, 6.5)


TITLE_SIZE_BLOCKED = 17
TITLE_POS_BLOCKED = (0, 6)


# --- Layout Tuning ---
UNIT_SIZE = 2.5
FONT_SIZE = 12
BIAS_CAP_GAP = 2.5
GAP_STAGE = 2.5
GAP_BIG = 3.0
BOX_PAD_X = 0.6
BOX_PAD_Y = 0.45


# ==========================================
# 2. COMPONENT BUILDER
# ==========================================
class RP2040AFEBuilder:
    def __init__(self, drawing):
        self.d = drawing
        self.cfg = COMPONENT_CONFIG

    def _lbl(self, symbol, key):
        """Helper to format labels as '$Symbol$\nValue'"""
        val = self.cfg.get(key, "")
        if val:
            return f"{symbol}\n{val}"
        return symbol

    def add_input(self):
        elms = []
        elms.append(self.d.add(elm.Dot(open=True).label("Input", loc="left")))

        lbl = self._lbl("$R_{prot}$", "R_PROT_VAL")
        elms.append(self.d.add(elm.Resistor().label(lbl, loc="bottom")))
        return elms

    def add_coupling(self, anchor):
        elms = []
        self.d.here = anchor.end

        lbl = self._lbl("$C_{ac}$", "C_AC_VAL")
        c_ac = self.d.add(elm.Capacitor().right().label(lbl, loc="bottom"))
        return c_ac, elms

    def add_attenuator(self):
        elms = []

        # Top Resistor (R_div1)
        lbl_r1 = self._lbl("$R_{div1}$", "R_DIV1_VAL")
        r_div1 = self.d.add(elm.Resistor().label(lbl_r1, loc="bottom"))
        elms.append(r_div1)

        # Node A (The Attenuator Output Node)
        node_a = self.d.add(elm.Dot())
        elms.append(node_a)

        # --- DOWNWARD PATH (R_div2 + Jumper) ---
        self.d.push()

        # R_div2
        lbl_r2 = self._lbl("$R_{div2}$", "R_DIV2_VAL")
        r_div2 = self.d.add(elm.Resistor().down().label(lbl_r2, loc="bottom"))
        elms.append(r_div2)

        # Left Branch: Ground (DC Mode)
        self.d.push()
        l_gnd = self.d.add(elm.Line().left(1.0))
        elms.append(l_gnd)
        gnd = self.d.add(elm.Ground())
        elms.append(gnd)
        gnd_lbl = self.d.add(
            elm.Label().label("Pin 1: GND\n(DC Mode)", loc="left", fontsize=10)
        )
        elms.append(gnd_lbl)
        self.d.pop()

        # Right Branch: V_mid (Audio Mode)
        self.d.push()
        l_vmid = self.d.add(elm.Line().right(1.0))
        elms.append(l_vmid)

        # Added: Open Dot to symbolize the header pin / remote connection point
        dot_hdr = self.d.add(elm.Dot(open=True))
        elms.append(dot_hdr)

        # V_mid Label (Right of the dot) - raised slightly
        vmid_lbl = self.d.add(elm.Label().label("$V_{mid}$", loc="right", ofst=0.08))
        elms.append(vmid_lbl)

        # Pin 3 Description (Pushed down significantly to avoid overlap)
        pin3_lbl = self.d.add(
            elm.Label().label(
                "Pin 3: Bias\n(Audio Mode)", loc="bottom", ofst=0.3, fontsize=10
            )
        )
        elms.append(pin3_lbl)
        self.d.pop()

        self.d.pop()  # Return to Node A

        return node_a, elms

    def add_bias(self, anchor_node, offset_up=1.5, offset_left=3.5):
        elms = []
        self.d.push()
        self.d.here = anchor_node.end

        # Vertical connector
        self.d.add(elm.Line().up(offset_up))

        # Injection Resistor
        lbl_inj = self._lbl("$R_{inject}$", "R_INJ_VAL")
        r_inj = self.d.add(elm.Resistor().up().label(lbl_inj))
        elms.append(r_inj)

        # Horizontal Shift
        shift = self.d.add(elm.Line().left(offset_left))
        elms.append(shift)

        # V_mid Node - lowered slightly so "(1.65V)" doesn't touch wire
        lbl_vmid = self._lbl("$V_{mid}$", "V_MID_VAL")
        node_bias = self.d.add(elm.Dot().label(lbl_vmid, loc="right", ofst=0.6))
        elms.append(node_bias)

        # Top Bias (3.3V)
        self.d.push()
        lbl_bias1 = self._lbl("$R_{bias1}$", "R_BIAS_TOP_VAL")
        elms.append(self.d.add(elm.Resistor().up().label(lbl_bias1)))
        elms.append(self.d.add(elm.Vdd().label(self.cfg["V_DD_VAL"])))
        self.d.pop()

        # Bottom Bias (GND)
        self.d.push()
        lbl_bias2 = self._lbl("$R_{bias2}$", "R_BIAS_BOT_VAL")
        elms.append(self.d.add(elm.Resistor().down().label(lbl_bias2)))
        elms.append(self.d.add(elm.Ground()))
        self.d.pop()

        # Filter Cap
        self.d.push()
        elms.append(self.d.add(elm.Line().left(BIAS_CAP_GAP)))
        lbl_cfilt = self._lbl("$C_{filter}$", "C_FILT_VAL")
        elms.append(self.d.add(elm.Capacitor().down().label(lbl_cfilt)))
        elms.append(self.d.add(elm.Ground()))
        self.d.pop()

        self.d.pop()
        return elms

    def add_clamp_adc(self):
        elms = []
        lbl_clamp = self._lbl("$R_{clamp}$", "R_CLAMP_VAL")
        elms.append(self.d.add(elm.Resistor().label(lbl_clamp, loc="bottom")))

        node_adc = self.d.add(elm.Dot())
        elms.append(node_adc)

        diode_label = self.cfg["D_CLAMP_TYPE"]

        # Top Diode
        self.d.push()
        elms.append(self.d.add(elm.Line().up(1.0)))
        elms.append(self.d.add(elm.Diode().up().label("D_top\n\n" + diode_label)))
        elms.append(self.d.add(elm.Vdd().label(self.cfg["V_DD_VAL"])))
        self.d.pop()

        # Bottom Diode
        self.d.push()
        elms.append(self.d.add(elm.Line().down(1.0)))
        elms.append(
            self.d.add(
                elm.Diode()
                .down()
                .reverse()
                .label("D_bot\n\n" + diode_label, loc="bottom")
            )
        )
        elms.append(self.d.add(elm.Ground()))
        self.d.pop()

        self.d.here = node_adc.end
        elms.append(self.d.add(elm.Line().right(1.5)))
        elms.append(self.d.add(elm.Dot(open=True).label("RP2040\nADC", loc="right")))

        return elms


# ==========================================
# 3. DRIVERS
# ==========================================


def draw_compact():
    # removed file=... from constructor so we can manually save multiples
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=UNIT_SIZE, fontsize=FONT_SIZE)
        d.add(
            elm.Label()
            .label(TITLE_TEXT_COMPACT, fontsize=TITLE_SIZE_COMPACT, loc="right")
            .at(TITLE_POS_COMPACT)
        )

        builder = RP2040AFEBuilder(d)

        builder.add_input()
        c_ac, _ = builder.add_coupling(d.elements[-1])
        node_a, _ = builder.add_attenuator()

        builder.add_bias(node_a, offset_up=1.5, offset_left=4.0)

        d.here = node_a.end
        d.add(elm.Line().right(2.0))
        builder.add_clamp_adc()

        # Save both formats
        d.save(EXPORT_DIR / f"{BASE_NAME_COMPACT}.svg", transparent=False)
        d.save(EXPORT_DIR / f"{BASE_NAME_COMPACT}.pdf")
        print(f"Saved {BASE_NAME_COMPACT} (.svg and .pdf)")


def draw_blocked():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=UNIT_SIZE, fontsize=FONT_SIZE)
        d.add(
            elm.Label()
            .label(TITLE_TEXT_BLOCKED, fontsize=TITLE_SIZE_BLOCKED, loc="right")
            .at(TITLE_POS_BLOCKED)
        )

        builder = RP2040AFEBuilder(d)

        g1 = builder.add_input()

        l1 = d.add(elm.Line().right(GAP_STAGE))
        c_ac, _ = builder.add_coupling(l1)
        g2 = [c_ac]

        d.here = c_ac.end
        d.add(elm.Line().right(GAP_STAGE))

        node_a, g3 = builder.add_attenuator()

        d.here = node_a.end
        d.add(elm.Line().right(GAP_STAGE))
        node_split = d.add(elm.Dot())

        g4 = builder.add_bias(node_split, offset_up=3.0, offset_left=4.5)

        d.here = node_split.end
        d.add(elm.Line().right(GAP_BIG))
        g5 = builder.add_clamp_adc()

        def box(elms, lbl):
            d.add(
                elm.EncircleBox(
                    elms, includelabels=True, padx=BOX_PAD_X, pady=BOX_PAD_Y
                )
                .linestyle("--")
                .linewidth(1)
                .zorder(-10)
                .label(lbl, loc="top")
            )

        box(g1, "1. Input")
        box(g2, "2. Coupling")
        box(g3, "3. Attenuation (Mode Select)")
        box(g4, "4. Bias")
        box(g5, "5. Clamp/ADC")

        # Save both formats
        d.save(EXPORT_DIR / f"{BASE_NAME_BLOCKED}.svg", transparent=False)
        d.save(EXPORT_DIR / f"{BASE_NAME_BLOCKED}.pdf")
        print(f"Saved {BASE_NAME_BLOCKED} (.svg and .pdf)")


if __name__ == "__main__":
    draw_compact()
    draw_blocked()
