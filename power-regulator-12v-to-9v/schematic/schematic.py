from pathlib import Path
import schemdraw
import schemdraw.elements as elm

# Configuration
schemdraw.theme("default")

COMPONENT_CONFIG = {
    "D_PROT_VAL": "1N5817",
    "C_BULK_IN": "100µF",
    "C_FILT_IN": "100nF",
    "REG_LABEL": "L7809",
    "C_BULK_OUT": "10µF",
    "C_FILT_OUT": "100nF",
}

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Define both output targets
FILE_SVG = str(EXPORT_DIR / "power_supply_regulator.svg")
FILE_PDF = str(EXPORT_DIR / "power_supply_regulator.pdf")

TITLE_TEXT = "9V Center-Negative Power Supply"
UNIT_SIZE = 2.5
FONT_SIZE = 10

# Spacing tuning
CAP_PAIR_SPACING = 1.8
STAGE_GAP = 0.8


def draw_schematic():
    # We initialize with the SVG file, so it saves that automatically on exit
    with schemdraw.Drawing(file=FILE_SVG, show=False) as d:
        d.config(unit=UNIT_SIZE, fontsize=FONT_SIZE)

        d.add(elm.Label().label(TITLE_TEXT, fontsize=12).at((2, 1.5)))
        d.here = (0, 0)

        # ===== INPUT SECTION =====
        d.push()
        d.add(elm.Dot(open=True).label("Center (+12V)", loc="left"))
        d.add(elm.Gap().down())
        d.add(elm.Dot(open=True).label("Sleeve (GND)", loc="left"))

        input_gnd = d.add(elm.Ground())
        input_ground_y = input_gnd.start[1]
        d.pop()

        # Main rail
        d.add(elm.Line().right(STAGE_GAP))
        d.add(
            elm.Schottky()
            .right()
            .label(
                f"$D_{{prot}}$\n{COMPONENT_CONFIG['D_PROT_VAL']}",
                loc="bottom",
                fontsize=8,
            )
        )
        d.add(elm.Line().right(STAGE_GAP))

        # Input Caps
        d.push()
        d.add(
            elm.Capacitor(polar=True)
            .down()
            .label(
                f"$C_{{in1}}$\n{COMPONENT_CONFIG['C_BULK_IN']}",
                loc="bottom",
                fontsize=8,
            )
        )
        d.add(elm.Ground())
        d.pop()

        d.add(elm.Line().right(CAP_PAIR_SPACING))

        d.push()
        d.add(
            elm.Capacitor()
            .down()
            .label(
                f"$C_{{in2}}$\n{COMPONENT_CONFIG['C_FILT_IN']}",
                loc="bottom",
                fontsize=8,
            )
        )
        d.add(elm.Ground())
        d.pop()

        # ===== REGULATOR =====
        d.add(elm.Line().right(STAGE_GAP))
        reg = d.add(
            elm.VoltageRegulator()
            .anchor("in")
            .label(f"{COMPONENT_CONFIG['REG_LABEL']}\n(+9V Reg)", loc="top", fontsize=9)
        )

        d.push()
        d.add(elm.Ground().at(reg.gnd))
        d.pop()

        # ===== OUTPUT SECTION =====
        d.add(elm.Line().right(STAGE_GAP).at(reg.out))

        # Output Caps
        d.push()
        d.add(
            elm.Capacitor(polar=True)
            .down()
            .label(
                f"$C_{{out1}}$\n{COMPONENT_CONFIG['C_BULK_OUT']}",
                loc="bottom",
                fontsize=8,
            )
        )
        d.add(elm.Ground())
        d.pop()

        d.add(elm.Line().right(CAP_PAIR_SPACING))

        d.push()
        d.add(
            elm.Capacitor()
            .down()
            .label(
                f"$C_{{out2}}$\n{COMPONENT_CONFIG['C_FILT_OUT']}",
                loc="bottom",
                fontsize=8,
            )
        )
        d.add(elm.Ground())
        d.pop()

        # ===== OUTPUT JACK =====
        d.add(elm.Line().right(STAGE_GAP))

        output_x = d.here[0]

        # Positive output (Sleeve)
        d.add(elm.Dot(open=True).label("Sleeve (+9V)", loc="right"))

        # Output center (GND)
        d.push()
        d.add(elm.Ground().at((output_x, input_ground_y)))
        d.add(
            elm.Dot(open=True)
            .at((output_x, input_ground_y))
            .label("Center (GND)", loc="right")
        )
        d.pop()

        # Explicitly save the PDF version before the context manager closes (and saves SVG)
        d.save(FILE_PDF)


if __name__ == "__main__":
    draw_schematic()
    print(f"Schematics generated:\n - {FILE_SVG}\n - {FILE_PDF}")
