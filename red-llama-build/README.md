# Red Llama Overdrive: Fabrication & Procurement

**Status:** Fabricated & Validated
**Role:** Device Under Test (DUT) & Software Catalyst

This directory contains the fabrication artifacts and procurement data for the **Red Llama Overdrive**, a clone of the classic Way Huge Electronics circuit. This build served as the primary test subject for the [RP2040 Oscilloscope](../oscilloscope-rp2040/) and the [Linear Power Regulator](../power-regulator-12v-to-9v/).

Crucially, **this project is the origin story for [Star Ground](https://github.com/JacksonFergusonDev/star-ground).**

## 1. The "Star Ground" Origin

Midway through the planning phase of this pedal, I realized that manually cross-referencing vendor BOMs against my local inventory was introducing unacceptable levels of nondeterministic error. The logistical entropy of managing multiple component sources, variable lead times, and "parts bin" verification required a systematic solution.

I paused fabrication to develop **Star Ground**, a Python-based full-stack logistics engine that treats hardware Bill of Materials (BOMs) as strict data objects.

### The Pipeline
The contents of the `procurement/` directory are **not** manually compiled. They are the deterministic outputs of the Star Ground engine:

1.  **Ingestion:** The tool parsed the raw PDF documentation for the Red Llama.
2.  **Inventory Subtraction:** It compared the required BOM against my local `inventory.csv` (my "digital twin").
3.  **Heuristic Buffering:** It applied "Nerd Economics" (yield management algorithms) to calculate safety stock—automatically padding resistors and critical silicon while keeping expensive electromechanical parts at a 1:1 ratio.
4.  **Artifact Generation:** It compiled the final purchasing manifest and Z-height sorted assembly manuals.

**🚀 [View the Tool / Live App](https://star-ground.streamlit.app/)**

### Generated Artifacts
* **`Shopping List.csv`**: The aggregated, algorithmic order list used to purchase components from Tayda Electronics.
* **`My Inventory Updated.csv`**: The post-build state of the local inventory.
* **`Field Manuals/`**: Rendered PDF instructions that reorganize the assembly order by component height (Resistors $\rightarrow$ Sockets $\rightarrow$ Capacitors) for streamlined soldering.

---

## 2. Circuit Topology

The Red Llama is topologically distinct among overdrive circuits as it eschews standard op-amps and discrete clipping diodes in favor of abusing the **CD4049 CMOS Hex Inverter**.

* **Gain Stages:** Two inverter stages are cascaded in series.
* **Clipping Mechanism:** By running the CMOS inverters with high negative feedback, they are forced into a linear amplification region. When driven hard, the internal push-pull MOSFETs hit the power rails, creating a soft, tube-like saturation that eventually squares off into a hard fuzz.

## 3. Engineering Deviations

While the build largely follows the standard topology, I introduced a modification to the power section to maximize dynamic range.

### D2 Substitution: Schottky vs. Silicon

The standard schema calls for a **1N4001** silicon diode at position **D2** for reverse-polarity protection. Silicon diodes exhibit a standard forward voltage drop ($V_f$) of approximately $0.7\text{V}$.

In a 9V circuit, this drop is non-trivial:
$$V_{rail} = V_{source} - V_{diode} = 9.0\text{V} - 0.7\text{V} = 8.3\text{V}$$

**The Modification:**
I replaced the 1N4001 with a **1N5817 Schottky Diode**. Schottky diodes utilize a metal-semiconductor junction rather than a p-n junction, resulting in a significantly lower $V_f$ (typically $0.2\text{V}$ to $0.3\text{V}$).

$$V_{rail(mod)} = 9.0\text{V} - 0.3\text{V} = 8.7\text{V}$$

**Result:**
By recovering $\approx 0.4\text{V}$ of supply voltage, the CMOS inverters have slightly more headroom before hitting the rails. This translates to increased dynamic range and a cleaner transient response before saturation occurs.

## 4. Directory Structure

```text
.
├── assets/                 # Build photos and reference images
├── procurement/            # Star Ground Compiler Outputs
│   ├── Field Manuals/      # Z-Height sorted build docs
│   ├── info.txt            # Build metadata and timestamps
│   ├── Shopping List.csv   # Auto-generated purchasing manifest
│   └── Sticker Sheets/     # Enclosure graphics
└── README.md
```