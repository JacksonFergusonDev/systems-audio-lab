# 12V to 9V Linear Power Supply

**Status:** Built & Validated

**Role:** Clean Power Source for the Red Llama Build

## 1. Project Motivation
Before building the Red Llama (or any guitar pedal), I needed a power source. Guitar pedals typically require a **9V Center-Negative** supply with extremely low noise.

I had plenty of cheap generic 12V power bricks lying around, but they are unsuitable for audio for two reasons:
1.  **Voltage:** 12V exceeds the standard 9V rating for most pedals.
2.  **Noise:** Cheap wall warts are usually Switch Mode Power Supplies (SMPS) with high-frequency ripple that leaks into the audio path.

Rather than buying a dedicated pedal supply, I decided to build a **Linear Voltage Regulator**. This served as my "Hello World" into discrete electronics—a low-risk, useful tool to validate my soldering and enclosure fabrication skills before attempting the audio circuit.

## 2. Theory of Operation

The circuit is built around the **L7809CV**, a classic series linear regulator. Unlike switching regulators which pulse current to maintain voltage (creating noise), a linear regulator acts as a variable resistor effectively "burning off" the excess voltage as heat. This results in a practically ripple-free DC output perfect for audio.

### Thermal Management Strategy

The core engineering constraint of a linear regulator is heat dissipation.

$$P_{dissipated} = (V_{in} - V_{out}) \times I_{load}$$

Given my input is $12V$ and output is $9V$, the regulator drops $3V$.
* **For the Red Llama:** The current draw is negligible ($<10mA$). $P \approx 0.03W$. The regulator would run cool even without a heatsink.

* **Future Proofing (Digital Pedals):** Digital reverbs or delays can draw upwards of $400mA$.

    $$P_{max} \approx 3V \times 0.4A = 1.2W$$

A standard TO-220 package has a thermal resistance ($\theta_{JA}$) of $\approx 65^\circ C/W$. Without a heatsink, a $1.2W$ load would cause a temperature rise of:

$$\Delta T = 1.2W \times 65^\circ C/W = 78^\circ C$$

Adding ambient temp ($25^\circ C$), the silicon would hit $\approx 103^\circ C$. While within limits ($125^\circ C$), this is dangerously hot for an enclosed plastic box.

**The Solution:**

1.  **Heatsink:** I added a screw-on TO-220 heatsink. This drastically lowers the thermal resistance, keeping the device safe even at higher current loads.

2.  **Convection Cooling:** ABS plastic is a thermal insulator. A heatsink inside a sealed plastic box just heats the air inside until the box melts. I drilled ventilation holes in the top of the enclosure to establish a convection current, allowing hot air to escape and cool air to enter.

## 3. Component Selection

| Component | Choice | Justification |
| :--- | :--- | :--- |
| **L7809CV** | 9V Linear Regulator | The standard for fixed voltage regulation. Robust thermal shutdown and current limiting features built-in. |
| **Input Caps** | 100µF Electrolytic + 100nF Poly | The 100µF acts as a bulk reservoir to smooth out low-frequency ripple from the 12V brick. The 100nF handles high-frequency noise that the electrolytic's ESR might miss. |
| **Output Caps** | 10µF Electrolytic + 100nF Poly | Provides transient response for the load. The 100nF prevents the regulator from oscillating. |
| **1N5817** | Schottky Diode | **Reverse Polarity Protection.** If I accidentally plug in a Center-Positive adapter, this blocks the current. I chose a Schottky (vs. 1N4001) for its lower forward voltage drop ($V_f \approx 0.45V$), keeping the input voltage higher. |
| **Heatsink** | 10-Fin TO-220 | Selected to allow the supply to drive high-current digital pedals in the future without thermal throttling. |

## 4. Bill of Materials

Everything was sourced from [Tayda Electronics](https://www.taydaelectronics.com/)

| Designator | Value | Component | SKU | Price (ea) | Qty | Total | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | **L7809** | L7809CV-DG Voltage Regulator 9V 1.5A | A-1597 | $0.25 | 1 | $0.25 | TO-220 Package |
| **$D_{prot}$** | **1N5817** | 1N5817 Diode Schottky 1A 20V | A-159 | $0.06 | 1 | $0.06 | Low $V_f$ |
| **$C_{in1}$** | **100µF** | 100uF 35V 105C Radial Electrolytic | A-987 | $0.03 | 1 | $0.03 | Bulk Input |
| **$C_{out1}$** | **10µF** | 10uF 50V 105C Radial Electrolytic | A-4554 | $0.02 | 1 | $0.02 | Bulk Output |
| **$C_{in2}, C_{out2}$** | **100nF** | 100nF 0.1uF 100V 5% Polyester Box | A-564 | $0.10 | 2 | $0.20 | HF Filtering |
| | **Jack (Fem)** | DC Power Jack 2.1mm Enclosed Frame | A-2237 | $0.13 | 1 | $0.13 | Panel Mount |
| | **Plug (Male)**| DC Power Jack 2.1x5.5mm Male With Wire | A-6806 | $0.15 | 1 | $0.15 | Output Pigtail |
| | **Enclosure** | Black Color Plastic Project Box 03 | A-2383 | $2.50 | 1 | $2.50 | ABS Plastic |
| | **Heat Sink** | Heat Sink TO-220 10 Fins 1 Inch | A-1512 | $0.24 | 1 | $0.24 | For U1 |
| | **Screw** | M3 Hexagon Socket Head Cap Screw | A-6379 | $0.10 | 1 | $0.10 | HS Mounting |
| **--** | **--** | **PROJECT TOTAL** | **--** | **--** | **--** | **$3.68** | |