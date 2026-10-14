# Execution Scripts (`scripts/`)

This directory contains the command-line scripts for capturing data, generating test signals, viewing signals live and analyzing saved files. Run them from the project root, for example `python oscilloscope-rp2040/scripts/capture/record.py`.

## 1. Capture (`scripts/capture/`)

Headless utilities for acquiring raw data from the hardware.

- **`master_transfer.py` (Transfer Function)**
  - **Function:** Plays a test signal through the laptop's audio output and records the circuit's response at the same time. Choose the mode by setting `MODE` at the top of the file; the script takes no arguments.
  - **Modes:**
    - **Sweep:** Plays a 5-second log sine sweep (20 Hz to 20 kHz) and records in stream mode until the audio finishes.
    - **Steady:** Plays a constant 1 kHz tone and captures one burst once the signal has settled.
  - **Use Case:** Measuring the frequency response, linearity and total harmonic distortion (THD) of the device under test (DUT).

- **`record.py` (Burst Mode)**
  - **Function:** Triggers a "science mode" capture: 16,384 samples with no gaps.
  - **Output:** Saves a timestamped `.npz` file to `data/burst/`.
  - **Use Case:** Spectrum analysis, or anything that needs an unbroken recording.

- **`stream.py` (Continuous Mode)**
  - **Function:** Joins many 1,024-sample "video mode" bursts into one long recording. There are untimed gaps between bursts (about 25% of the time is lost), so the result is not one continuous signal.
  - **Output:** Saves a timestamped `.npz` file to `data/continuous/`.
  - **Use Case:** Recording over seconds to minutes when gaps don't matter, or for analysis that treats each block separately.

## 2. Signal Generation (`scripts/signal/`)

Tools that play test signals while showing the captured result live.

- **`play_wave.py`**
  - **Function:** Generates continuous waveforms (Sine, Triangle, Square, Saw) via the host audio output.
  - **Features:** Shows the live oscilloscope view of the signal coming back from the circuit.
  - **Use Case:** Probing circuit behavior at specific frequencies (e.g., checking for clipping with a triangle wave).

- **`play_sweep.py`**
  - **Function:** Plays a logarithmic sine sweep (20Hz to 20kHz).
  - **Features:** Automatically stops the oscilloscope visualization when the audio sweep completes.
  - **Use Case:** Watching the circuit's high-frequency roll-off live.

## 3. Visualization (`scripts/visualization/`)

Real-time monitoring and rendering tools.

- **`live_scope.py` / `playback_scope.py`**
  - **Function:** Connects to the hardware (or plays back a file) and renders a live voltage-vs-time plot.
  - **Features:**
    - **Software Trigger:** Stabilizes the waveform for steady viewing.
    - **Blitting:** Redraws only the changing parts of the Matplotlib plot to keep the frame rate above 20 FPS.
    - **Diagnostic Overlay:** Displays FPS and status.

- **`render_scope_video.py`**
  - **Function:** Converts saved `.npz` recordings into 60 FPS MP4 videos.
  - **Features:**
    - **Styles:** Clean, CRT bloom and glitch looks.
    - **Time-Sync:** Resamples the signal to the video frame rate so playback runs at the correct speed.
    - **FFmpeg:** Encodes the video as H.264 (FFmpeg must be installed).

## 4. Analysis (`scripts/analysis/`)

Post-processing tools for examining saved datasets.

- **`spectrum.py`**
  - **Function:** Loads a chosen `.npz` file and plots its spectrum.
  - **Visualization:**
    - **Top Plot:** Time-domain signal (Voltage vs Time).
    - **Bottom Plot:** Magnitude Spectrum (FFT).
  - **Metrics:** Automatically estimates the fundamental frequency (pitch) of the signal.

## Workflow Example (Transfer Function)

1. **Set Levels:** Run `scripts/signal/play_wave.py` (sine) and adjust the laptop volume until the signal on the live scope is clearly visible without hitting the 0V or 3.3V limits (unless you want clipping).
1. **Capture Sweep:** Set `MODE = "sweep"` in `scripts/capture/master_transfer.py` and run it to record the frequency response.
1. **Capture Steady Tone:** Set `MODE = "steady"` and run it again to record a 1 kHz tone for THD. For the saturation curve (a triangle wave), use notebook `03_transfer_acquisition.ipynb`.
1. **Analyze:** Open `notebooks/04_transfer_analysis.ipynb` to process the captured files.
