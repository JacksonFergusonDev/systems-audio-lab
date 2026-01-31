"""
Script to generate and visualize a "Neon Torus" phase portrait.

This script generates a drone sound (beating sine waves), plays it via audio,
captures the resulting signal via DAQ, and visualizes it as a phase portrait
using time-delay embedding.
"""

import os
import sys
import time

import numpy as np
import sounddevice as sd

# Ensure src is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, daq, dsp, plots  # noqa: E402

# Configuration
FREQ_1: float = 55.0
FREQ_2: float = 56.0
DURATION: float = 10.0
AMP: float = 0.2
DELAY_SAMPLES: int = 800


def main() -> None:
    """
    Main execution entry point.

    Generates the audio stimulus, captures the system response, processes
    the signal (DC removal, normalization), and renders the phase portrait.
    """
    fs_audio: int = 48000
    print(f"🔹 Generating Drone ({FREQ_1}Hz + {FREQ_2}Hz)...")
    wave = audio.generate_drone(DURATION, fs_audio, AMP, FREQ_1, FREQ_2)

    frames = []
    print("🔴 Capturing...")
    with daq.DAQInterface() as device:
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        # Capture loop
        for chunk in device.stream_generator():
            frames.append(chunk)
            if not sd.get_stream().active:
                break
            if (time.time() - start_time) > (DURATION + 1.0):
                break

    print("Processing...")
    raw_data = np.concatenate(frames)

    # Signal conditioning
    volts = dsp.raw_to_volts(raw_data)
    ac_signal = dsp.remove_dc(volts)

    # Normalize for plotting (avoid division by zero)
    peak = np.max(np.abs(ac_signal))
    if peak > 0:
        norm_signal = ac_signal / peak
    else:
        norm_signal = ac_signal

    plots.plot_phase_portrait(norm_signal, DELAY_SAMPLES)


if __name__ == "__main__":
    main()
