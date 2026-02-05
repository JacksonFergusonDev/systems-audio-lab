# Universal RP2040 Spectrograph & Oscilloscope

**Status:** Commissioned (Jan 2026) | **Revision:** 1.1 (System ID Upgrade)

This project transforms a Raspberry Pi RP2040-Zero into a precision, calibrated Data Acquisition (DAQ) device for high-fidelity audio and spectral analysis. Unlike standard ADC examples, this system features a custom Analog Front End (AFE) with bias injection, signal clamping, and a "Store-and-Forward" firmware architecture to decouple sampling stability from USB latency.

In **Phase 2**, the system was expanded to include a host-side **Function Generator** and **Transfer Function Analyzer**, allowing for closed-loop system identification (Bode plots, Linearity testing, and THD measurement).

<img src="./schematics/exports/signal_conditioning_universal-compact.svg" width="80%" alt="Schematic Diagram">

*A more informational version of the schematic, along with an explanation of the circuit, can be found [here](./schematics/README.md).*

## ⚡ System Specifications

| Parameter | Performance |
| :--- | :--- |
| **ADC Depth** | 12-bit (Hardware) $\to$ 16-bit (Scaled) |
| **Sample Rate ($F_s$)** | **97.8 kHz** (Calibrated via 60Hz Mains Reference) |
| **Bandwidth** | DC -- 48.9 kHz (Nyquist) |
| **Buffer** | 16,384 Samples ($\approx 167$ms burst) |
| **Input Range** | 0--3.3V (Unipolar) / $\pm 3.3V$ (AC Coupled) |

## 📂 Repository Architecture

### [`schematics/`](./schematics/)
The physical layer. Contains the schematics and fabrication exports for the Universal AFE.
* **Topology:** Switched Reference with selectable attenuation (Line Level vs. High-Z/Guitar).
* **Protection:** Dual-stage clamping ($R_{prot}$ + 1N4148 diodes) prevents RP2040 latch-up.

### [`firmware/`](./firmware)
The MicroPython logic running on the MCU.
* **Engine:** Uses `@micropython.native` emitters for a jitter-free polling loop.
* **Protocol:** Implements a binary "Handshake" protocol (`s` for Science Burst, `v` for Video) to manage USB serial backpressure.

### [`sysaudio/`](./sysaudio)
The Python library backing the analysis pipeline.
* **Core & Hardware**
    * `sysaudio.daq`: Hardware abstraction for USB UART stream processing.
    * `sysaudio.calibration`: Routines for robust sample rate ($F_s$) verification.
    * `sysaudio.audio`: Host-side signal generation (Sine, Square, Log Sweeps) via `sounddevice`.
* **Experimentation**
    * `sysaudio.experiments`: High-level automation for Notebooks (Linearity, Bandwidth, THD captures).
    * `sysaudio.io`: Standardized file handling for burst (`.npz`) and continuous signal data.
* **Analysis & Viz**
    * `sysaudio.dsp`: Signal processing primitives (FFT, THD calculation, Triggering).
    * `sysaudio.plots`: Publication-ready plotting wrappers (Bode, Transfer Curves, THD Fingerprints).
    * `sysaudio.viz`: Real-time rendering engines for the live oscilloscope.

### [`scripts/`](./scripts)
User-facing tools for interaction.
* **`capture/`**: Headless recording tools.
    * `record.py`: High-fidelity burst capture.
    * `master_transfer.py`: Automated stimulus-response testing (Sweep/Steady).
    * `stream.py`: Continuous data streaming utility.
* **`signal/`**: Interactive function generators.
    * `play_wave.py`: Infinite waveform generator with live scope.
    * `play_sweep.py`: Logarithmic sine sweep generator.
* **`visualization/`**: Monitoring and rendering.
    * `live_scope.py`: Real-time oscilloscope with FFT.
    * `playback_scope.py`: Offline replay of captured signal files.
    * `joyplot.py`: Ridge-line plot generation for spectral waterfalls.
    * `render_scope_video.py`: Exports scope data to video frames.
* **`fun/`**: Creative coding experiments.
    * `neon_torus.py`: XY oscilloscope visualization.
    * `render_landscape.py`: 3D terrain generation from audio data. Used to generate the title graphic for [systems_audio_tech_report.pdf](../docs/systems_audio_tech_report.pdf)

### [`notebooks/`](./notebooks)
The scientific workbench.
* **`01_instrument_acquisition.ipynb`**: Hardware calibration and raw data inspection.
* **`02_instrument_analysis.ipynb`**: Empirical characterization of the Red Llama Overdrive (Harmonics & Topology).
* **`03_transfer_acquisition.ipynb`**: Automated capture of transfer function datasets.
    * *Set A:* Linearity (Triangle Wave).
    * *Set B:* Bandwidth (Log Sine Sweep).
    * *Set C:* Standard THD (1kHz Sine).
* **`04_transfer_analysis.ipynb`**: System Identification (In Progress).
    * *Bode Response:* Magnitude and Phase analysis.
    * *Transfer Curves:* Input vs. Output linearity mapping.
    * *THD Fingerprinting:* Harmonic distortion profiling.

## Hardware Requirements
**Total Cost:** ~$4.14 USD

| Qty | Component | Notes |
| :--- | :--- | :--- |
| 1 | **RP2040-Zero** | Waveshare or generic. |
| 1 | **6.35mm Jack** | Mono (TS). |
| 4 | **10kΩ Resistors** | 1/4W 1% |
| 2 | **100kΩ Resistors** | 1/4W 1% |
| 1 | **220kΩ Resistor** | 1/4W 1% |
| 2 | **1N4148 Diodes** | Signal/Switching. |
| 1 | **220nF Capacitor** | Film/Box preferred. |
| 1 | **10µF Capacitor** | Electrolytic. |
| 1 | **Perfboard** | 40x60mm min. |

> *Full Bill of Materials with Tayda Electronics SKUs and pricing [available here](./schematics/README.md).*

## Quick Start

### 1. Firmware Flash
Flash the RP2040 with MicroPython (v1.27+) and copy `firmware/main.py` to the root of the device.

### 2. Host Environment
Dependencies are managed at the **project root**. Run the following from the top-level `systems-audio-lab` directory:

```bash
# Install dependencies and link the sysaudio package
uv pip install -e .
```

### 3. Execution
Run scripts from the project root to ensure proper package resolution.

Real-Time Monitoring:
```bash
python oscilloscope-rp2040/scripts/visualization/live_scope.py
```

Function Generator (Signal + Scope):
```bash
python oscilloscope-rp2040/scripts/signal/play_wave.py
```

Automated Transfer Function Capture:
```bash
# Capture a 5-second log sweep for Bode plotting
python oscilloscope-rp2040/scripts/capture/master_transfer.py sweep --duration 5 --amp 0.5
```

---

## Future Development

This documentation describes the **v1.0 Prototype** architecture.

Development has begun on **v2.0 ("The Silicon Revision")**, which will transition this logic from a perfboard prototype to an integrated PCBA with dedicated ADCs and DACs.

**View the full [v2.0 Roadmap and Specification](../README.md#-future-roadmap-silicon-revision-v20) in the project root.**
