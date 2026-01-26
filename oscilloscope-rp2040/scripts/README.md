# Execution Scripts (`scripts/`)

This directory contains the user-facing entry points for data capture, visualization, signal generation, and post-mortem analysis. The scripts are categorized by their stage in the signal processing pipeline.

## 1. Capture (`scripts/capture/`)
Headless utilities for acquiring raw data from the hardware.

* **`measure_transfer.py` (Transfer Function)**
    * **Function:** The "Master Recorder" for system identification. Synchronizes audio playback with DAQ capture.
    * **Modes:**
        * **Sweep:** Plays a log sine sweep and records a continuous stream until audio finishes.
        * **Steady:** Plays a constant waveform and captures a precise burst after settling.
    * **Use Case:** Characterizing frequency response, linearity, and THD of the DUT (Device Under Test).

* **`record.py` (Burst Mode)**
    * **Function:** Triggers a "Science Mode" capture ($16,384$ samples).
    * **Output:** Saves a timestamped `.npz` file to `data/burst/`.
    * **Use Case:** High-fidelity spectral analysis where sample continuity is critical.

* **`stream.py` (Continuous Mode)**
    * **Function:** Stitches together multiple "Video Mode" packets into a long-format recording.
    * **Output:** Saves a timestamped `.npz` file to `data/continuous/`.
    * **Use Case:** Logging signals over longer durations (seconds to minutes).

## 2. Signal Generation (`scripts/signal/`)
Tools for generating test signals while visualizing the output in real-time.

* **`play_wave.py`**
    * **Function:** Generates continuous waveforms (Sine, Triangle, Square, Saw) via the host audio output.
    * **Features:** Includes a live oscilloscope view to monitor the signal return loop.
    * **Use Case:** Probing circuit behavior at specific frequencies (e.g., checking for clipping with a triangle wave).

* **`play_sweep.py`**
    * **Function:** Generates a logarithmic sine sweep (20Hz - 20kHz).
    * **Features:** Automatically stops the oscilloscope visualization when the audio sweep completes.
    * **Use Case:** Visualizing the frequency response roll-off of the circuit in real-time.

## 3. Visualization (`scripts/visualization/`)
Real-time monitoring and rendering tools.

* **`live_scope.py` / `playback_scope.py`**
    * **Function:** Connects to the hardware (or plays back a file) and renders a live voltage-vs-time plot.
    * **Features:**
        * **Software Trigger:** Stabilizes the waveform for steady viewing.
        * **Blitting:** Uses advanced Matplotlib rendering techniques to achieve high FPS ($>20$ Hz).
        * **Diagnostic Overlay:** Displays FPS and status.

* **`render_scope_video.py`**
    * **Function:** Converts saved `.npz` recordings into 60 FPS, high-bitrate MP4 videos.
    * **Features:**
        * **Aesthetic Engine:** Supports multiple visual styles (Clinical, CRT Bloom, Cyber Glitch).
        * **Time-Sync:** Decouples rendering framerate from signal sampling rate for smooth playback.
        * **FFmpeg Integration:** Produces visually lossless H.264 output.

## 4. Analysis (`scripts/analysis/`)
Post-processing tools for examining saved datasets.

* **`spectrum.py`**
    * **Function:** Loads a selected `.npz` file and performs Frequency Domain analysis.
    * **Visualization:**
        * **Top Plot:** Time-domain signal (Voltage vs Time).
        * **Bottom Plot:** Magnitude Spectrum (FFT).
    * **Metrics:** Automatically estimates the fundamental frequency (pitch) of the signal.

## Workflow Example (Transfer Function)
1.  **Calibrate Levels:** Run `scripts/signal/play_wave.py` (sine) and adjust laptop volume until the signal on the live scope is healthy (not hitting rails unless desired).
2.  **Capture Sweep:** Run `scripts/capture/measure_transfer.py` (configured for `sweep` mode) to record the frequency response.
3.  **Capture Linearity:** Run `scripts/capture/measure_transfer.py` (configured for `steady` mode with a triangle wave) to record the saturation curve.
4.  **Analyze:** Use `notebooks/03_transfer_function.ipynb` to process the captured files.