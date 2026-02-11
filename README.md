# ⚡ systems-audio-lab

**A vertically integrated audio analysis platform.**

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Hardware](https://img.shields.io/badge/Hardware-RP2040-red.svg)
![Version](https://img.shields.io/badge/Version-v1.0_Prototype-orange.svg)
![Analysis Status](https://img.shields.io/badge/Analysis-In_Progress-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

### 📡 The Mission: Vertical Integration

Most audio analysis relies on "black box" equipment. This project builds the **entire signal chain** from scratch:
1.  **Power:** A custom linear regulator to eliminate switching noise.
2.  **Device:** A discrete CMOS overdrive circuit to generate soft-clipping distortion.
3.  **Probe:** A custom RP2040 oscilloscope to capture the waveform.
4.  **Analysis:** A Python pipeline to deconvolve the Transfer Function.

By owning every stage of the pipeline, this system eliminates the "dependency hell" of unknown hardware variables, allowing for precise correlation between **circuit topology** and **spectral output**.

---

### 📄 [Read the Full Engineering Report (PDF)](docs/systems_audio_tech_report.pdf)
*A detailed technical report covering the full systems engineering approach: logistics automation, power supply design, analog circuit fabrication, and custom DAQ instrumentation for spectral validation.*

---

## 🚧 Currently In Progress: Transfer Function Deconvolution

Hardware and basic signal analysis are **complete and validated**. Transfer function analysis is under active development.

* **Completed:** Waveform capture, harmonic analysis confirming soft-clipping topology and harmonic asymmetry (Notebooks `01` & `02`).
* **In Progress:** Implementing **Exponential Sine Sweep (ESS) deconvolution** in Notebook `04` to separate linear frequency response from harmonic distortion components, enabling automated Bode plot generation.

---

## 🔬 Signal Analysis: Quantifying "Warmth"

The primary goal was to test whether **CMOS inverter chips** (normally used for digital logic), when biased into their linear region, produce soft-clipping distortion similar to vacuum tubes.

**The Results:**
Using the custom RP2040 oscilloscope, I captured the saturation behavior of the Red Llama overdrive circuit.

![Topology Analysis](docs/figures/fig_analysis_topology.svg)

1.  **Time Domain (Left):** Shows **"soft knee"** compression. Unlike diodes which clip sharply at $V_f$, the CMOS chips round off the waveform smoothly.
2.  **Frequency Domain (Right):** The spectrum reveals a dominant **2nd harmonic** (one octave above fundamental). This even-order harmonic content is consistent with the "tube sound" hypothesis, mathematically validating the circuit design.

---

## 🏗 System Architecture

This project consists of four interconnected subsystems, each enabling the next.

### 1. [Logistics: Star Ground](https://github.com/JacksonFergusonDev/star-ground)
* **The Problem:** Manual BOM management leads to "Logistical Entropy" (missing parts/delays).
* **The Solution:** A deterministic dependency manager that parses PDF BOMs and calculates strict safety stock levels.
* **Status:** *Complete / External Repository*

### 2. [Infrastructure: Linear Power Regulator](power-regulator-12v-to-9v/)
* **The Problem:** Cheap wall adapters introduce switching noise (ripple) that pollutes sensitive measurements.
* **The Solution:** A custom 12V → 9V linear voltage regulator with thermal management to support high-current loads.
* **Key Components:** L7809CV regulator, Schottky diode for reverse polarity protection, heatsink with ventilation.

### 3. [The Device: Red Llama Overdrive](red-llama-build/)
* **The Problem:** Need a "Device Under Test" (DUT) with predictable non-linearity.
* **The Solution:** Built a Red Llama clone using CD4049 CMOS inverter chips.
* **Modification:** Replaced standard diodes with Schottky (1N5817) to recover 0.4V of headroom.

<img src="red-llama-build/assets/red_llama_complete.jpg" width="52%" alt="Red Llama Build"> <img src="red-llama-build/assets/red_llama_effects_board_only.jpg" width="45%" alt="Red Llama Circuit">

### 4. [Instrumentation: RP2040 Oscilloscope](oscilloscope-rp2040/)
* **The Problem:** Needed to measure the harmonic content of the overdrive circuit but didn't have an oscilloscope.
* **The Solution:** Built a USB oscilloscope around the RP2040 microcontroller with custom analog signal conditioning.
* **Architecture:** Store-and-forward firmware separates high-speed sampling from USB transmission to avoid data loss.
* **Performance:** 97.8 kSps (calibrated against 60 Hz mains), 12-bit resolution, 1.3 mV noise floor.

<img src="oscilloscope-rp2040/assets/oscilloscope_1.0_gain.jpg" width="45%" alt="Oscilloscope Build"> <img src="oscilloscope-rp2040/assets/oscilloscope_screen.png" width="54%" alt="Oscilloscope Screen">

---

## 🚀 Getting Started

This project uses **uv** for dependency management.

### 1. Clone & Enter

```bash
git clone https://github.com/JacksonFergusonDev/systems-audio-lab.git
cd systems-audio-lab
```

### 2. Install Environment
We use an editable install so changes to the `sysaudio` library are immediately reflected in the notebooks.

```bash
# Initialize virtual environment
uv venv
source .venv/bin/activate

# Install dependencies and local package
uv pip install -e .
```

### 3. Usage Options
Option A: Interactive Analysis (Jupyter) Launch the lab to view the engineering reports and signal processing pipelines.

```bash
jupyter lab
```

Option B: Headless Tools (CLI Scripts) You can run the capture and visualization tools directly from the command line.

```bash
# Example: Launch the real-time oscilloscope visualization
python oscilloscope-rp2040/scripts/visualization/live_scope.py

# Example: Record a single burst of data
python oscilloscope-rp2040/scripts/capture/record.py
```

---

## 📂 Repository Structure

```text
.
├── docs/                      # Engineering Report (LaTeX/PDF) & Analysis Figures
├── oscilloscope-rp2040/       # Firmware (MicroPython) & Analysis Pipeline
│   ├── firmware/              # RP2040 Sampling Logic
│   ├── notebooks/             # Jupyter Analysis Notebooks
│   │   ├── 01_instrument_acquisition.ipynb  # Waveform Capture 🟢
│   │   ├── 02_instrument_analysis.ipynb     # Harmonic Analysis 🟢
│   │   ├── 03_transfer_acquisition.ipynb    # Sine Sweep Generation 🟢
│   │   └── 04_transfer_analysis.ipynb       # Deconvolution (In Progress) 🟡
│   ├── sysaudio/              # Analysis Library (FFT, Plotting, Signal Processing)
│   └── schematics/            # Signal Conditioning Circuit Design
├── red-llama-build/           # Guitar Overdrive Test Circuit
│   └── procurement/           # Bills of Materials
└── power-regulator-12v-to-9v/ # Linear Power Supply Design
```

---

## 🔮 Future Roadmap: Silicon Revision (v2.0)

With the measurement chain validated, the next iteration focuses on **Determinism** and **Automation**.

**Current State:** The v1.0 oscilloscope relies on CPU-polled USB Serial for data transmission. This introduces non-deterministic latency (jitter) dependent on the host OS scheduler.

**The Goal:** Design a custom PCB that implements a **Zero-Copy Architecture**, ensuring that sample timing is defined purely by hardware clocks, not software loops.

### Planned Improvements

**1. Deterministic Transport (Ethernet vs USB)**
* **The Problem:** USB is non-deterministic; the device must wait for the host OS to poll for data (1ms - 125µs intervals).
* **The Fix:** Implement an **Ethernet PHY (W5500/LAN8720)**.
* **The Result:** The device pushes data via **UDP Streaming** immediately upon acquisition, decoupling the sampling clock from the host OS scheduler.

**2. Zero-Copy DMA Architecture**
* **The Problem:** Moving data from ADC to memory via CPU interrupts consumes cycles and risks dropping samples during high load.
* **The Fix:** Implement a **Direct Memory Access (DMA)** pipeline.
* **The Result:** The ADC writes directly to a ring buffer in RAM, and a second DMA channel feeds the Ethernet MAC. The CPU never touches the sample data, guaranteeing cycle-accurate throughput.

**3. Signal Chain Upgrade**
* **External ADC:** Replace the RP2040's internal 12-bit ADC with a **24-bit Audio Codec** (I2S). This increases dynamic range for measuring low-level harmonics (-90dB noise floor).
* **On-board DAC:** Integrate a DAC (PCM5102) to generate test signals directly from hardware, enabling self-contained frequency sweeps.

**4. Programmable Input Stage**
* **Software-Controlled Gain:** Replace manual jumpers with a Programmable Gain Amplifier (PGA).
* **Automated Characterization:** Implement a "One-Click Bode Plot" routine: the system generates a sweep, captures the response via DMA, and streams the data via UDP without manual intervention.

---

## 📧 Contact

**Jackson Ferguson**

-   **GitHub:** [@JacksonFergusonDev](https://github.com/JacksonFergusonDev)
-   **LinkedIn:** [Jackson Ferguson](https://www.linkedin.com/in/jackson--ferguson/)
-   **Email:** jackson.ferguson0@gmail.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
