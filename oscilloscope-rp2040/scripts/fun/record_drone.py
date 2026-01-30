import os
import sys
import time

import numpy as np
import sounddevice as sd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, config, daq, dsp, io

# --- EXPERIMENT CONFIG ---
FREQ = 55.0
BEAT_FREQ = 0.2
DURATION = 10.0
AMP = 0.2
FILENAME = "fun_drone"


def main():
    fs_audio = 48000
    print(f"🔹 Generating Pulsing Drone ({FREQ}Hz)...")
    wave = audio.generate_pulsing_drone(DURATION, fs_audio, AMP, FREQ, BEAT_FREQ)

    frames = []
    print("🔴 Capturing (Check your volume!)...")
    with daq.DAQInterface() as device:
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        for chunk in device.stream_generator():
            frames.append(chunk)
            if not sd.get_stream().active:
                break
            if (time.time() - start_time) > (DURATION + 1.0):
                break

    print("✅ Capture Complete. Processing...")
    raw_data = np.concatenate(frames)
    volts = dsp.raw_to_volts(raw_data)

    io.save_signal(
        volts,
        config.FS_DEFAULT,
        config.DATA_DIR_BURST,
        prefix=FILENAME,
        user_notes="Harmonic Landscape Source Data",
    )


if __name__ == "__main__":
    main()
