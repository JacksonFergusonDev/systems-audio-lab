# ⚡ systems-audio-lab

**From Python to Silicon**

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Hardware](https://img.shields.io/badge/Hardware-RP2040-red.svg)
![Hardware Status](https://img.shields.io/badge/Hardware-Validated-success.svg)
![Analysis Status](https://img.shields.io/badge/Analysis-In_Progress-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

This project goes beyond building a guitar pedal, it engineers the supply chain, power infrastructure, and instrumentation required to validate it.

This repository documents a complete systems engineering project, spanning software-driven logistics, custom power regulation, embedded instrumentation, and empirical analysis of non-linear analog circuits.

### 📄 [Read the Full Engineering Monograph (PDF)](docs/design_journal.pdf)
*A technical report covering the design process, thermal analysis, and spectral validation.*

---

## 🚧 Current Status: Implementing the Farina Method
While the hardware, firmware, and organic signal analysis are **fully validated**, the Transfer Function analysis is currently under active development.

* **Completed:** Instrument analysis confirming the "Soft Knee" topology and Harmonic Asymmetry (Notebooks `01` & `02`).
* **In Progress:** I am currently implementing **Angelo Farina's (2000) Exponential Sine Sweep (ESS) Deconvolution** method in Notebook `04`. This will allow for the mathematical separation of the Linear Impulse Response from the Harmonic Distortion products, providing a Bode plot of the system with linear and harmonic components explicitly separated.

---

## 🔬 Key Findings: The Physics of "Tube Sound"

The primary objective was to validate the claim that **CMOS Hex Inverters** (digital logic chips), when biased into a linear class-A region, exhibit soft clipping behavior and harmonic asymmetry comparable to vacuum tube triodes.

**The Evidence:**
Using the custom RP2040 DAQ built for this project, I captured the saturation characteristics of the Red Llama drive (Chapter 6 of the report).

![Topology Analysis](docs/figures/fig_analysis_topology.svg)

1.  **Time Domain (Left):** Note the **"Soft Knee"** compression at the peaks. Unlike silicon diodes which shear waveforms off flatly, the CMOS chips round off the transients, preserving dynamic feel.
2.  **Frequency Domain (Right):** The spectral fingerprint reveals a dominant **2nd Harmonic (Octave)**. This even-order harmonic content characterizes what audio engineers call 'warmth', confirming the tube emulation hypothesis.

---

## 🏗 The Full Stack

This project is divided into four interdependent subsystems, each enabling the next.

### 1. [Logistics: Star Ground](https://github.com/JacksonFergusonDev/star-ground)
* **The Problem:** Manual BOM management is nondeterministic and error-prone.
* **The Solution:** A Python-based logistics engine that parses PDF documentation, subtracts local inventory, and utilizes "Nerd Economics" to calculate heuristic safety stock.
* **Status:** *Production / External Repo*

[🚀 Try the App!](https://star-ground.streamlit.app/)

### 2. [Infrastructure: Linear Power Regulator](power-regulator-12v-to-9v/)
* **The Problem:** Audio circuits require a low-noise floor, but standard wall-warts are noisy Switch Mode Power Supplies (SMPS).
* **The Solution:** A custom fabricated 12V $\to$ 9V Linear Regulator with thermal management to support high-current loads.
* **Key Tech:** L7809CV, Schottky Protection, Thermal Dissipation Analysis.

### 3. [The Device: Red Llama Overdrive](red-llama-build/)
* **The Problem:** Validating the procurement and power systems requires a sensitive analog load.
* **The Solution:** A clone of the Way Huge Red Llama, utilizing CD4049 CMOS Hex Inverters for soft-saturation.
* **Modification:** Replaced D2 (1N4001) with 1N5817 (Schottky) to recover 0.4V of headroom.

<img src="red-llama-build/assets/red_llama_complete.jpg" width="52%" alt="Red Llama Build"> <img src="red-llama-build/assets/red_llama_effects_board_only.jpg" width="45%" alt="Oscilloscope Build">

### 4. [Instrumentation: RP2040 Oscilloscope](oscilloscope-rp2040/)
* **The Problem:** I needed to verify the harmonic content of the Red Llama, but didn't own an oscilloscope.
* **The Solution:** A custom-built RP2040-based oscilloscope.
* **Architecture:** "Store-and-Forward" capture engine using MicroPython `@native` emitters.
* **Performance:** 97.8 kSps (Calibrated), 12-bit depth, 1.3mV Noise Floor.

<img src="oscilloscope-rp2040/assets/oscilloscope_1.0_gain.jpg" width="45%" alt="Oscilloscope Build"> <img src="oscilloscope-rp2040/assets/oscilloscope_screen.png" width="54%" alt="Oscilloscope Screen">

---

## 📂 Repository Structure

```text
.
├── docs/                      # The Engineering Monograph (LaTeX/PDF) & Analysis Figures
├── oscilloscope-rp2040/       # Firmware (MicroPython) & Analysis Pipeline
│   ├── firmware/              # RP2040 Logic (MicroPython)
│   ├── notebooks/             # Jupyter Lab Analysis
│   │   ├── 01_instrument_acquisition.ipynb  # Organic Signal Capture 🟢
│   │   ├── 02_instrument_analysis.ipynb     # Topology Validation 🟢
│   │   ├── 03_transfer_acquisition.ipynb    # Log Sine Sweep Gen 🟢
│   │   └── 04_transfer_analysis.ipynb       # Farina Deconvolution 🟡
│   ├── src/                   # Shared Analysis Library (Metrics, Plots, DSP)
│   └── schematics/            # KiCad/Python Signal Conditioning Schematics
├── red-llama-build/           # The Device Under Test (DUT)
│   └── procurement/           # Star Ground Artifacts (BOMs, Manuals)
└── power-regulator-12v-to-9v/ # The Linear Power Supply Design