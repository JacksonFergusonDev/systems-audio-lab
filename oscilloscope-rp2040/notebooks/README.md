# Data Acquisition & Analysis Notebooks

This directory contains the Jupyter notebooks used for controlling the RP2040 oscilloscope, capturing data, and performing post-processing analysis.

## Notebooks

### `01_instrument_acquisition.ipynb`

The primary interface for capturing organic signal data (Guitar/Synth) from the hardware. It handles the complete acquisition pipeline:

1. **Calibration:**
    - Measures the *True Sampling Rate (FS)* by analyzing the 60Hz mains hum.
    - Caches the calibration result to `data/calibration.json` so you don't need to recalibrate on every kernel restart.
1. **Data Capture:**
    - Triggers the RP2040 to capture a burst of samples.
    - Converts raw ADC integers (uint16) to float voltages.
1. **Real-time Diagnostics:**
    - **Clipping Detection:** Warns if the signal hits the 0V/3.3V rails.
    - **Bias Check:** Monitors the DC offset (Target: 1.65V).
    - **Signal Strength:** Calculates peak-to-peak voltage relative to the noise floor.
1. **Storage:**
    - Saves data to `data/burst/` as compressed `.npz` archives.
    - Injects rich metadata (Hardware params, Clipping flags, User notes) into the file header for provenance.

### `02_instrument_analysis.ipynb`

The scientific analysis workbench used to characterize the **Red Llama Overdrive** using organic signals and validate the "CMOS Tube Sound" hypothesis. It utilizes the custom `src` library to generate publication-ready figures.

1. **Exploratory Analysis:**
    - **Gain Staging:** Visualizes the massive signal amplification ($36\times$ / $31\text{dB}$) between the instrument input and the pedal output.
    - **Noise Floor:** Quantifies the detector's dynamic range and bias stability.
1. **Topology Verification:**
    - **Phase Locking:** Uses cross-correlation `smart_align()` to overlay input vs. output waveforms, revealing the "Soft Knee" saturation curve in the time domain.
    - **Spectral Normalization:** Compares the frequency response shapes to visualize the "plateau" of generated harmonic content.
1. **Harmonic Fingerprinting:**
    - **Histogram Analysis:** Deconstructs the signal into discrete harmonic orders ($2f, 3f, \dots$).
    - **Symmetry Check:** Proves the "Tube-like" behavior by identifying the dominance of Even-Order harmonics (Asymmetrical Clipping) over Odd-Order harmonics.
1. **Metrics & Reporting:**
    - Calculates **Selective THD** (Total Harmonic Distortion) to put a quantitative metric on the saturation.
    - Exports vector graphics (`.pdf`) to `docs/figures/` for the final design journal.

### `03_transfer_acquisition.ipynb`

The System Identification interface. Unlike the organic capture in notebook `01`, this notebook generates deterministic test signals to mathematically characterize the circuit.

1. **Signal Generation:**
    - Uses `sysaudio.audio` to generate precision Logarithmic Sine Sweeps ($20\text{Hz} - 20\text{kHz}$).
    - Manages audio output via `sounddevice` to drive the pedal input.
1. **Synchronized Capture:**
    - Triggers the RP2040 DAQ immediately prior to audio playback.
    - Captures the full sweep response of the DUT (Device Under Test).
1. **Validation:**
    - Verifies that the sweep amplitude remained within the linear headroom of the ADC.
    - Saves the "Stimulus" (Source) and "Response" (DUT) as paired datasets for analysis.

### `04_transfer_analysis.ipynb`

The System Identification workbench: frequency response, distortion vs. frequency, and the large-signal transfer curve.

1. **Chunked Sweep Analysis:**
    - Stream-mode captures have untimed gaps between 1024-sample blocks, so whole-signal ESS deconvolution (Farina, 2000) is not applicable.
    - `sysaudio.chunked_sweep` recovers each block's position in the sweep from a constant-period fit, then least-squares fits the exact log-sweep phase model (fundamental + harmonics 2–5) to every block.
    - The DUT/source ratio of fundamentals gives the **Magnitude Response**; harmonic levels give **Distortion vs. Frequency** against the source's own floor.
1. **Transfer Curve:**
    - XY plot of a 100 Hz triangle reveals the asymmetric soft-saturation sigmoid and its capacitive "memory" loop.
1. **Cross-Validation:**
    - A gap-free 1 kHz burst capture agrees with the sweep analysis within 0.7 dB.
    - Exports `fig_transfer_bode`, `fig_transfer_curve` and `fig_thd_fingerprint` to `docs/figures/`.
