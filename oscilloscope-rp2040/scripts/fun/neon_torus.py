import os
import sys
import time

import numpy as np
import sounddevice as sd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, daq, dsp, plots

# --- CONFIGURATION ---
FREQ_1 = 55.0
FREQ_2 = 56.0
DURATION = 10.0
AMP = 0.2
DELAY_SAMPLES = 800


def main():
    fs_audio = 48000
    print(f"🔹 Generating Drone ({FREQ_1}Hz + {FREQ_2}Hz)...")
    wave = audio.generate_drone(DURATION, fs_audio, AMP, FREQ_1, FREQ_2)

    frames = []
    print("🔴 Capturing...")
    with daq.DAQInterface() as device:
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        for chunk in device.stream_generator():
            frames.append(chunk)
            if not sd.get_stream().active:
                break
            if (time.time() - start_time) > (DURATION + 1.0):
                break

    print("Processing...")
    raw_data = np.concatenate(frames)
    volts = dsp.raw_to_volts(raw_data)
    ac_signal = dsp.remove_dc(volts)
    norm_signal = ac_signal / np.max(np.abs(ac_signal))

    plots.plot_phase_portrait(norm_signal, DELAY_SAMPLES)


if __name__ == "__main__":
    main()
