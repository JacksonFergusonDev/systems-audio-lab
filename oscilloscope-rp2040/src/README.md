# Source Library Architecture (`src/`)

This directory contains the core Python package that powers the RP2040 Data Acquisition System. It is architected as a modular library, separating hardware abstraction, signal processing, and data persistence into discrete, testable units.

## Module Index

### 1. Hardware Abstraction Layer (`daq.py`)
The `DAQInterface` class manages the physical link to the RP2040 via USB Serial (UART).
- **Protocol:** Implements the 'Store-and-Forward' handshake (`s` for Burst, `v` for Video).
- **Buffer Management:** Handles raw binary ingestion from the serial buffer to avoid overflows.
- **Generator Pattern:** The `stream_generator()` method yields non-blocking data chunks for real-time applications.

### 2. Digital Signal Processing (`dsp.py`)
A stateless functional module for manipulating raw ADC data.
- **`raw_to_volts`**: Vectorized conversion of `uint16` (0–65535) to Float64 (0–3.3V).
- **`software_trigger`**: Implements a rising-edge detection algorithm to stabilize periodic waveforms for visualization (mimics hardware oscilloscope triggers).
- **`compute_spectrum`**: Wraps `numpy.fft` with Hanning window application to reduce spectral leakage.

### 3. Calibration Engine (`calibration.py`)
Contains the logic for the "Mains Hum Reference" calibration.
- **Algorithm:** Captures a burst, isolates the 60Hz component using FFT, and calculates the spectral offset.
- **Precision:** Uses a weighted average of bins around the peak to achieve sub-bin frequency accuracy.
- **Output:** Returns the *true* sample rate ($F_s$), correcting for MicroPython interpreter latency.

### 4. Diagnostics (`diagnostics.py`)
Automated health checks for the analog front end.
- **Clipping Detection:** Flags samples nearing 0V or 3.3V.
- **Bias Drift:** Monitors the DC mean to ensure $V_{mid}$ remains centered ($\approx 1.65V$).
- **SNR Calculation:** Compares signal magnitude against the noise floor.

### 5. Input/Output (`io.py`)
Handles data persistence and serialization.
- **Format:** Uses NumPy's compressed archive format (`.npz`) to store the signal array and sampling rate metadata efficiently.
- **Legacy Support:** Robust loading logic handles schema changes from previous firmware versions.

### 6. Visualization Primitives (`viz.py`)
Encapsulates `matplotlib` boilerplate for the oscilloscope interface.
- **`init_scope_plot`**: Pre-configures figure assets (lines, axes) to maximize frame rate.
- **`run_live_scope`**: A reusable, blocking visualization loop that handles blitting, window management, and optional "Launch Callbacks" to synchronize audio playback with the GUI.
- **Style:** Enforces a high-contrast dark theme for better readability during analysis.

### 7. Rendering Engine (`render.py`)
The backend for video generation and aesthetic processing.
- **Effects Pipeline:** Modular rendering functions (`setup_clean`, `setup_crt_bloom`) that decouple visual style from data logic.
- **FFmpeg Wrapper:** Handles the piping of Matplotlib figures to the H.264 encoder.
- **Time-Base Management:** Resamples signal time to video time to ensure accurate playback speed regardless of the original sampling rate.

### 8. Audio Synthesis (`audio.py`)
Handles deterministic signal generation and hardware playback for System Identification.
- **`ContinuousOscillator`**: A context manager for infinite waveform playback (Sine, Triangle, Square) with stateful phase tracking.
- **`generate_log_sweep`**: Mathematically precise logarithmic sine sweep generation for transfer function analysis.
- **Device Management:** Wraps `sounddevice` to handle audio stream callbacks and device selection.

### 9. Scientific Analysis (`analysis.py`)
Contains the logic for generating publication-quality figures for the Design Journal.
- **Topology visualization:** Plots phase-locked comparisons of Input vs. Output to reveal saturation curves.
- **Harmonic Fingerprinting:** Generates normalized histograms to quantify Even vs. Odd harmonic distortion.
- **Export Utility:** `save_pdf_svg` handles the output of vector graphics for LaTeX integration.

## Usage
This package is not intended to be run directly. Import it into your scripts as follows:

```python
from src import daq, dsp, config

with daq.DAQInterface() as device:
    data = device.capture_burst()
    volts = dsp.raw_to_volts(data)