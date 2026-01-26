# Data Acquisition & Analysis Notebooks

This directory contains the Jupyter notebooks used for controlling the RP2040 oscilloscope, capturing data, and performing post-processing analysis.

## Notebooks

### `01_instrument_acquisition.ipynb`
**Status:** Active 🟢

The primary interface for capturing organic signal data (Guitar/Synth) from the hardware. It handles the complete acquisition pipeline:

1.  **Calibration:**
    * Measures the *True Sampling Rate (FS)* by analyzing the 60Hz mains hum.
    * Caches the calibration result to `data/calibration.json` so you don't need to recalibrate on every kernel restart.
2.  **Data Capture:**
    * Triggers the RP2040 to capture a burst of samples.
    * Converts raw ADC integers (uint16) to float voltages.
3.  **Real-time Diagnostics:**
    * **Clipping Detection:** Warns if the signal hits the 0V/3.3V rails.
    * **Bias Check:** Monitors the DC offset (Target: 1.65V).
    * **Signal Strength:** Calculates peak-to-peak voltage relative to the noise floor.
4.  **Storage:**
    * Saves data to `data/burst/` as compressed `.npz` archives.
    * Injects rich metadata (Hardware params, Clipping flags, User notes) into the file header for provenance.

### `02_instrument_analysis.ipynb`
**Status:** Active 🟢

The scientific analysis workbench used to characterize the **Red Llama Overdrive** using organic signals and validate the "CMOS Tube Sound" hypothesis. It utilizes the custom `src` library to generate publication-ready figures.

1.  **Exploratory Analysis:**
    * **Gain Staging:** Visualizes the massive signal amplification ($36\times$ / $31\text{dB}$) between the instrument input and the pedal output.
    * **Noise Floor:** Quantifies the detector's dynamic range and bias stability.
2.  **Topology Verification:**
    * **Phase Locking:** Uses cross-correlation `smart_align()` to overlay input vs. output waveforms, revealing the "Soft Knee" saturation curve in the time domain.
    * **Spectral Normalization:** Compares the frequency response shapes to visualize the "plateau" of generated harmonic content.
3.  **Harmonic Fingerprinting:**
    * **Histogram Analysis:** Deconstructs the signal into discrete harmonic orders ($2f, 3f, \dots$).
    * **Symmetry Check:** Proves the "Tube-like" behavior by identifying the dominance of Even-Order harmonics (Asymmetrical Clipping) over Odd-Order harmonics.
4.  **Metrics & Reporting:**
    * Calculates **Selective THD** (Total Harmonic Distortion) to put a quantitative metric on the saturation.
    * Exports vector graphics (`.pdf`) to `docs/figures/` for the final design journal.

### `03_transfer_acquisition.ipynb`
**Status:** Active 🟢

The System Identification interface. Unlike the organic capture in notebook `01`, this notebook generates deterministic test signals to mathematically characterize the circuit.

1.  **Signal Generation:**
    * Uses `src.audio` to generate precision Logarithmic Sine Sweeps ($20\text{Hz} - 20\text{kHz}$).
    * Manages audio output via `sounddevice` to drive the pedal input.
2.  **Synchronized Capture:**
    * Triggers the RP2040 DAQ immediately prior to audio playback.
    * Captures the full sweep response of the DUT (Device Under Test).
3.  **Validation:**
    * Verifies that the sweep amplitude remained within the linear headroom of the ADC.
    * Saves the "Stimulus" (Source) and "Response" (DUT) as paired datasets for deconvolution.

### `04_transfer_analysis.ipynb`
**Status:** In Progress 🟡

The advanced signal processing workbench implementing the **Angelo Farina (2000)** method for characterizing non-linear audio systems.

1.  **Deconvolution Engine:**
    * Generates a "Blue Noise" Inverse Filter to reverse the Log Sine Sweep.
    * Convolves the recorded sweep to extract the **Linear Impulse Response (IR)** of the pedal.
    * **Harmonic Separation:** Isolates the linear response from the harmonic distortion products (which appear as "pre-echoes" in negative time).
2.  **Frequency Domain Analysis:**
    * Applies an asymmetric (causal) window to the IR to discard distortion artifacts.
    * Performs FFT on the windowed IR to derive the true **Linear Bode Plot** (Magnitude Response).
    * *Current Work:* Refining the Inverse Filter envelope to correct low-frequency tilt artifacts.