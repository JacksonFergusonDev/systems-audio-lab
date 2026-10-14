# Data Acquisition & Analysis Notebooks

This directory contains the Jupyter notebooks that control the RP2040 oscilloscope, capture data and analyze it. Run them in order: `01` and `03` capture data, and `02` and `04` analyze it.

## Notebooks

### `01_instrument_acquisition.ipynb`

Captures real instrument signals (guitar or synth) from the hardware. It covers:

1. **Calibration:**
    - Estimates the true sample rate ($F_s$) from the 60Hz mains hum. This is a first-pass estimate; notebook `02` checks it against crystal-referenced test tones.
    - Caches the calibration result to `data/calibration.json` so you don't need to recalibrate on every kernel restart.
1. **Data Capture:**
    - Triggers the RP2040 to capture a burst of samples.
    - Converts raw ADC integers (uint16) to float voltages.
1. **Signal Checks:**
    - **Clipping Detection:** Warns if the signal hits the 0V/3.3V rails.
    - **Bias Check:** Monitors the DC offset (Target: 1.65V).
    - **Signal Strength:** Compares the peak-to-peak voltage with the noise floor.
1. **Storage:**
    - Saves data to `data/burst/` as compressed `.npz` archives.
    - Stores metadata with each file (hardware settings, health-check flags, notes) so you can tell later how it was recorded.

### `02_instrument_analysis.ipynb`

Analyzes the guitar captures of the Red Llama overdrive to test whether its CMOS chips clip like vacuum tubes. It uses the `sysaudio` library and produces the report's figures.

1. **Exploratory Analysis:**
    - **Gain Staging:** Measures the gain between the guitar signal and the pedal output ($72\times$ or $37\text{dB}$, after correcting for the DAQ's 0.5× divider).
    - **Noise Floor:** Measures the DAQ's noise, dynamic range and bias stability.
1. **Topology Verification:**
    - **Phase Locking:** Aligns the input and output waveforms with cross-correlation (`smart_align()`) and overlays them, showing the "soft knee" saturation in the time domain.
    - **Spectral Normalization:** Compares the normalized spectra of input and output, showing the harmonics the circuit adds.
1. **Harmonic Fingerprinting:**
    - **Histogram Analysis:** Measures the level of each harmonic ($2f, 3f, \dots$).
    - **Symmetry Check:** Compares even- and odd-order harmonic energy against the clean input, to measure how much asymmetry (even-order content) the circuit adds.
1. **Metrics & Reporting:**
    - Calculates total harmonic distortion (THD) from the energy at the harmonic frequencies only, ignoring broadband noise (**selective THD**).
    - Exports the figures (`.pdf` and `.svg`) to `docs/figures/` for the report.

### `03_transfer_acquisition.ipynb`

Captures the circuit's response to test signals. Notebook `01` records a real guitar; this notebook plays known signals from the laptop instead, so the response can be compared with the input exactly.

1. **Signal Generation:**
    - Uses `sysaudio.audio` to generate logarithmic sine sweeps (20 Hz to 20 kHz), a triangle wave and a 1 kHz sine.
    - Manages audio output via `sounddevice` to drive the pedal input.
1. **Synchronized Capture:**
    - Starts the RP2040 capture just before audio playback.
    - Records the response of the device under test (DUT), here the Red Llama.
1. **Validation:**
    - Verifies that the sweep amplitude remained within the linear headroom of the ADC.
    - Saves the source loopback and the DUT response as a matched pair of files.

### `04_transfer_analysis.ipynb`

Analyzes the test-signal captures: frequency response, distortion against frequency, and the large-signal transfer curve.

1. **Chunked Sweep Analysis:**
    - Stream-mode captures have untimed gaps between 1024-sample blocks, so the usual exponential sine sweep (ESS) deconvolution (Farina, 2000), which needs one continuous recording, can't be used.
    - `sysaudio.chunked_sweep` works out where each block falls in the sweep (assuming a constant block period), then fits the fundamental and harmonics 2–5 to every block by least squares.
    - The DUT/source ratio of fundamentals gives the **Magnitude Response**; harmonic levels give **Distortion vs. Frequency** against the source's own floor.
1. **Transfer Curve:**
    - Plotting output against input for a 100 Hz triangle wave shows the asymmetric, S-shaped saturation curve and a small loop caused by the circuit's capacitors.
1. **Cross-Validation:**
    - A gap-free 1 kHz burst capture agrees with the sweep analysis within 0.2 dB.
    - Quantifies even vs. odd harmonic energy (H2–H8) for the 1 kHz tone, complementing the guitar comparison in notebook `02`.
    - Exports `fig_transfer_bode`, `fig_transfer_curve` and `fig_thd_fingerprint` to `docs/figures/`.
