"""
Script to generate and record a pulsing drone sound.

This script generates a modulated sine wave (pulsing drone), plays it through
the system audio, and simultaneously records the loopback/output via the
DAQ interface. The resulting data is saved for use in harmonic landscape
visualizations.
"""

import time
from typing import List

import numpy as np
import sounddevice as sd
from sysaudio import audio, config, daq, dsp, io

# Configuration
FREQ: float = 55.0
BEAT_FREQ: float = 0.2
DURATION: float = 10.0
AMP: float = 0.2
FILENAME: str = "fun_drone"


def main() -> None:
    """
    Main execution entry point.

    Generates the audio stimulus, manages the playback/capture synchronization,
    processes the raw ADC data, and saves the result to disk.
    """
    fs_audio: int = 48000
    print(f"🔹 Generating Pulsing Drone ({FREQ}Hz)...")
    wave = audio.generate_pulsing_drone(DURATION, fs_audio, AMP, FREQ, BEAT_FREQ)

    frames: List[np.ndarray] = []
    print("🔴 Capturing (Check your volume!)...")

    with daq.DAQInterface() as device:
        # Start non-blocking playback
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        # Stream capture loop
        for chunk in device.stream_generator():
            frames.append(chunk)

            # Stop if audio playback has finished
            if not sd.get_stream().active:
                break

            # Safety timeout
            if (time.time() - start_time) > (DURATION + 1.0):
                break

    print("✅ Capture Complete. Processing...")
    raw_data = np.concatenate(frames)

    # Signal conditioning
    volts = dsp.raw_to_volts(raw_data)

    # Save to disk with metadata
    io.save_signal(
        volts,
        config.FS_DEFAULT,
        config.DATA_DIR_BURST,
        prefix=FILENAME,
        user_notes="Harmonic Landscape Source Data",
    )


if __name__ == "__main__":
    main()
