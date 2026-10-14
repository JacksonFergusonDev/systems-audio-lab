# 12V to 9V Linear Power Supply

**Status:** Built and in use (output ripple not measured) | **Role:** Power supply for the Red Llama pedal

## 1. Project Motivation

Before building the Red Llama (or any guitar pedal), I needed a power source. Most guitar pedals expect a low-noise **9V center-negative** supply (the barrel's center pin is negative).

I had plenty of cheap generic 12V power bricks lying around, but they are unsuitable for audio for two reasons:

1. **Voltage:** 12V exceeds the standard 9V rating for most pedals.
1. **Noise:** Cheap wall adapters are usually switch-mode power supplies (SMPS), whose high-frequency ripple can leak into the audio path.

Rather than buying a dedicated pedal supply, I built a linear voltage regulator. It was my first electronics build: low-risk and useful, and a chance to practice soldering and enclosure work before the audio circuit.

## 2. Theory of Operation

The circuit is built around the **L7809CV**, a common fixed 9V linear regulator. A switching regulator pulses current to hold its output voltage, which creates noise; a linear regulator instead acts like a variable resistor, turning the excess voltage into heat. The design intent is a DC output with the switching ripple of the 12V brick largely removed. The output ripple has not been measured: the L7809's ripple rejection falls with frequency, and typical SMPS switching frequencies lie above the DAQ's 48.8kHz Nyquist limit.

### Thermal Management Strategy

The main constraint on a linear regulator is getting rid of that heat.

$$P_{dissipated} = (V_{in} - V_{out}) \times I_{load}$$

Given my input is $12V$ and output is $9V$, the regulator drops $3V$.

- **For the Red Llama:** The current draw was not measured, but CMOS pedals of this kind typically draw well under $10mA$, giving $P < 0.03W$. The regulator would run cool even without a heatsink.

- **Digital Pedals (future use):** Digital reverbs or delays draw far more; I used a $400mA$ load as the design case.

    $$P_{max} \approx 3V \times 0.4A = 1.2W$$

A standard TO-220 package has a thermal resistance ($\theta_{JA}$) of $\approx 65^\circ C/W$. Without a heatsink, a $1.2W$ load would cause a temperature rise of:

$$\Delta T = 1.2W \times 65^\circ C/W = 78^\circ C$$

Adding the room temperature ($25^\circ C$), the chip would reach $\approx 103^\circ C$. That is within its $125^\circ C$ limit, but too hot for a closed plastic box.

**The Solution:**

1. **Heatsink:** I added a screw-on TO-220 heatsink, which lowers the thermal resistance so the regulator stays cooler at high loads.

1. **Ventilation:** ABS plastic insulates, so a heatsink in a sealed plastic box mostly heats the air inside it. I drilled holes in the top of the enclosure so hot air can rise out and cooler air can flow in.

## 3. Component Selection

| Component | Choice | Justification |
| :--- | :--- | :--- |
| **L7809CV** | 9V Linear Regulator | A common, cheap fixed regulator with built-in thermal shutdown and current limiting. |
| **Input Caps** | 100µF Electrolytic + 100nF Poly | The 100µF acts as a bulk reservoir to smooth out low-frequency ripple from the 12V brick. The 100nF handles high-frequency noise that the electrolytic's ESR might miss. |
| **Output Caps** | 10µF Electrolytic + 100nF Poly | The 10µF supplies sudden changes in load current. The 100nF keeps the regulator from oscillating. |
| **1N5817** | Schottky Diode | Reverse polarity protection: if a center-positive adapter is plugged in by mistake, this blocks the current. I chose a Schottky over a 1N4001 for its lower voltage drop ($V_f \approx 0.45V$ at its rated 1A, $\approx 0.3V$ at a pedal's few mA), which leaves more input voltage. |
| **Heatsink** | 10-Fin TO-220 | Lets the supply run high-current digital pedals without overheating or hitting thermal shutdown. |

## 4. Bill of Materials

Everything was bought from [Tayda Electronics](https://www.taydaelectronics.com/).

| Designator | Value | Component | SKU | Price (ea) | Qty | Total | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | **L7809** | L7809CV-DG Voltage Regulator 9V 1.5A | A-1597 | $0.25 | 1 | $0.25 | TO-220 Package |
| **$D_{prot}$** | **1N5817** | 1N5817 Diode Schottky 1A 20V | A-159 | $0.06 | 1 | $0.06 | Low $V_f$ |
| **$C_{in1}$** | **100µF** | 100uF 35V 105C Radial Electrolytic | A-987 | $0.03 | 1 | $0.03 | Bulk Input |
| **$C_{out1}$** | **10µF** | 10uF 50V 105C Radial Electrolytic | A-4554 | $0.02 | 1 | $0.02 | Bulk Output |
| **$C_{in2}, C_{out2}$** | **100nF** | 100nF 0.1uF 100V 5% Polyester Box | A-564 | $0.10 | 2 | $0.20 | HF Filtering |
| | **Jack (Fem)** | DC Power Jack 2.1mm Enclosed Frame | A-2237 | $0.13 | 1 | $0.13 | Panel Mount |
| | **Plug (Male)** | DC Power Jack 2.1x5.5mm Male With Wire | A-6806 | $0.15 | 1 | $0.15 | Output Pigtail |
| | **Enclosure** | Black Color Plastic Project Box 03 | A-2383 | $2.50 | 1 | $2.50 | ABS Plastic |
| | **Heat Sink** | Heat Sink TO-220 10 Fins 1 Inch | A-1512 | $0.24 | 1 | $0.24 | For U1 |
| | **Screw** | M3 Hexagon Socket Head Cap Screw | A-6379 | $0.10 | 1 | $0.10 | HS Mounting |
| **--** | **--** | **PROJECT TOTAL** | **--** | **--** | **--** | **$3.68** | |
