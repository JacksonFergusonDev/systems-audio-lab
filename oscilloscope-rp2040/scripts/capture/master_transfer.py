import sys
import os
import time
import numpy as np
import sounddevice as sd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, daq, io, config, dsp

# --- USER CONFIGURATION ---
# Uncomment ONE mode below to select it:

MODE = "sweep"
# MODE = "steady"

# --- SWEEP SETTINGS (if MODE="sweep") ---
SWEEP_START = 20.0
SWEEP_END = 20000.0
SWEEP_DURATION = 5.0
SWEEP_AMP = 0.5

# --- STEADY SETTINGS (if MODE="steady") ---
STEADY_SHAPE = "sine"  # "sine", "triangle", "square"
STEADY_FREQ = 1000.0
STEADY_AMP = 0.5
# --------------------------


def run_sweep_capture():
    fs_audio = 48000
    print(f"🔹 Generating Sweep ({SWEEP_START}-{SWEEP_END}Hz, {SWEEP_DURATION}s)...")
    wave = audio.generate_log_sweep(
        SWEEP_START, SWEEP_END, SWEEP_DURATION, fs_audio, SWEEP_AMP
    )

    frames = []

    print("🔴 Starting Capture...")
    with daq.DAQInterface() as device:
        # Start Audio
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        # Capture loop (Continuous Stream)
        for chunk in device.stream_generator():
            frames.append(chunk)

            # Stop if audio finished
            if not sd.get_stream().active:
                print("Audio finished.")
                break

            # Failsafe timeout
            if (time.time() - start_time) > (SWEEP_DURATION + 2.0):
                print("Timeout reached.")
                break

    # Save
    print("Processing...")
    full_array = np.concatenate(frames)
    io.save_signal(
        full_array, config.FS_DEFAULT, config.DATA_DIR_CONTINUOUS, prefix="sweep"
    )


def run_steady_capture():
    print(f"🔹 Starting Oscillator ({STEADY_SHAPE} @ {STEADY_FREQ}Hz)...")

    with audio.ContinuousOscillator(STEADY_SHAPE, STEADY_FREQ, STEADY_AMP) as osc:
        # Allow signal to settle
        time.sleep(0.5)

        print("📸 Capturing Burst...")
        with daq.DAQInterface() as device:
            raw = device.capture_burst()
            volts = dsp.raw_to_volts(raw)

            io.save_signal(
                volts,
                config.FS_DEFAULT,
                config.DATA_DIR_BURST,
                prefix=f"transfer_{STEADY_SHAPE}",
            )


def main():
    if MODE == "sweep":
        run_sweep_capture()
    elif MODE == "steady":
        run_steady_capture()
    else:
        print(f"❌ Unknown MODE: {MODE}")
        print("Please edit the configuration at the top of the file.")


if __name__ == "__main__":
    main()
