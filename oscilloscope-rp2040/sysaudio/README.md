# Source Library Architecture (`sysaudio/`)

This directory contains `sysaudio`, the Python package behind the scripts and notebooks. Each module covers one job: talking to the device, signal processing, saving files, plotting, and so on.

## Module Index

### 1. Hardware Abstraction Layer (`daq.py`)

The `DAQInterface` class manages the USB serial connection to the RP2040.

- **Protocol:** Sends the one-byte commands (`s` for a 16,384-sample burst, `v` for a 1,024-sample video burst) and reads back the raw samples.
- **`capture_burst()`**: Returns one full burst.
- **`stream_generator()`**: Yields one 1,024-sample block at a time, for the live scope and stream recordings.

### 2. Digital Signal Processing (`dsp.py`)

Functions for processing ADC data. None of them keep state between calls.

- **`raw_to_volts`**: Converts raw `uint16` samples (0–65535) to volts (0–3.3V).
- **`software_trigger`**: Finds a rising edge so repeating waveforms stay still on screen, like the trigger on a hardware oscilloscope.
- **`compute_spectrum`**: Wraps `numpy.fft` with a Hann window to reduce spectral leakage, scaled by the window's coherent gain so magnitudes read as peak amplitudes.
- **`harmonic_amplitudes` / `calculate_selective_thd`**: Measure each harmonic's main-lobe energy with the local noise floor removed.
- **`estimate_tone_frequency`**: Least-squares frequency fit of a steady tone, resolving far below one FFT bin.

### 3. Calibration Engine (`calibration.py`)

Measures the true sample rate ($F_s$). It has to be measured because it is set by how long each pass of the MicroPython loop takes, not by a hardware clock.

- **Reference tone (preferred):** `calibrate_fs_with_tone` / `fs_from_reference_tone` fit a crystal-referenced sound-card tone; the measured rate is `config.FS_DEFAULT`.
- **Mains hum (legacy):** `calibrate_fs_robust` locates the 60 Hz line. The grid wanders and the coupled hum is weak, so it is only good to about 0.2%.
- **History:** `save_calibration` keeps earlier calibrations under `"previous"` in `data/calibration.json`.

### 4. Diagnostics (`diagnostics.py`)

Checks that a capture is usable.

- **Clipping Detection:** Flags samples nearing 0V or 3.3V.
- **Bias Drift:** Monitors the DC mean to ensure $V_{mid}$ remains centered ($\approx 1.65V$).
- **Peak Check:** Reports the dominant spectral peaks as a pitch sanity check.

### 5. Input/Output (`io.py`)

Handles data persistence and serialization.

- **Format:** Stores the signal and its metadata in NumPy's compressed archive format (`.npz`).
- **Sample rate:** `load_signal` returns the measured `config.FS_DEFAULT`; the `fs` stored in each file is what was assumed at capture time (pass `use_stored_fs=True` to get it).
- **Units:** Burst captures store volts, stream captures raw ADC counts; `dsp.to_volts` accepts either.
- **Legacy metadata:** In the existing captures `clipped` means "failed the health check" (weak signals included) and `adc_bits` reads 16 for the 12-bit ADC. The files are kept as recorded; new captures store `clipped` and `healthy` separately.
- **Older Files:** Loading also handles files saved with earlier metadata layouts.

### 6. Visualization Primitives (`viz.py`)

Matplotlib setup for the oscilloscope windows.

- **`init_scope_plot`**: Creates the figure, axes and lines once up front, so each frame only updates data.
- **`run_live_scope`**: Runs the live display until the window closes. It redraws only the changing parts of the plot (blitting) and can call a function on startup, which the signal scripts use to start audio playback.
- **Style:** Uses a high-contrast dark theme.

### 7. Rendering Engine (`render.py`)

Turns recordings into videos.

- **Styles:** Each look is its own setup function (`setup_clean`, `setup_crt_bloom`, `setup_cyber_glitch`), separate from the data handling.
- **FFmpeg:** Sends Matplotlib frames to FFmpeg for H.264 encoding.
- **Timing:** Maps signal time to video frames so playback runs at the correct speed whatever the sample rate.

### 8. Audio Synthesis (`audio.py`)

Generates test signals and plays them through the laptop's audio output.

- **`ContinuousOscillator`**: Plays a sine, triangle or square wave until stopped, keeping the phase continuous between audio blocks. Use it in a `with` block.
- **`generate_log_sweep`**: Generates a logarithmic sine sweep for transfer function measurements.
- **Audio Devices:** Uses `sounddevice` for playback and device selection.

### 9. Scientific Analysis (`metrics.py`, `plots.py`)

`metrics.py` computes the analysis results; `plots.py` turns them into the figures for the technical report.

- **Topology Plots:** Overlays aligned input and output waveforms to show the saturation shape.
- **Harmonic Fingerprinting:** Bar charts of each harmonic's level, normalized, to compare even and odd harmonics.
- **Export:** `save_pdf_svg` saves each figure as PDF (for the LaTeX report) and SVG (for the READMEs).

### 10. Chunked Sweep Analysis (`chunked_sweep.py`)

Recovers transfer functions from stream-mode sweep captures, whose 1024-sample blocks are separated by untimed gaps.

- **`analyze_chunked_sweep`**: Recovers each block's sweep position from a constant-period fit, then least-squares fits the log-sweep phase model (fundamental + harmonics) per block.
- **`compute_chunked_bode`**: Compares source and DUT captures on a common log-frequency grid, returning normalized gain and harmonics relative to the fundamental.

## Usage

The package isn't run directly; import it into your own scripts:

```python
from sysaudio import daq, dsp, config

with daq.DAQInterface() as device:
    data = device.capture_burst()
    volts = dsp.raw_to_volts(data)
```
