import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, daq, dsp, io

# --- EXPERIMENT CONFIG ---
FREQ = 55.0  # Low A (Deep Bass)
BEAT_FREQ = 0.2  # Pulse speed (0.2 Hz = 5 second swell)
DURATION = 10.0
AMP = 0.2  # 0.6 is a good sweet spot for Llama saturation
FILENAME = "fun_drone"


def generate_pulsing_drone(duration, fs, amp, freq, pulse_rate):
    """Generates the source audio signal."""
    t = np.arange(int(duration * fs)) / fs
    carrier = np.sin(2 * np.pi * freq * t)
    modulator = 0.5 * (1 + np.sin(2 * np.pi * pulse_rate * t - np.pi / 2))
    return (carrier * modulator * amp).astype(np.float32)


def main():
    fs_audio = 48000

    # 1. Generate
    print(f"🔹 Generating Pulsing Drone ({FREQ}Hz)...")
    wave = generate_pulsing_drone(DURATION, fs_audio, AMP, FREQ, BEAT_FREQ)

    frames = []

    # 2. Capture
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

    # 3. Save Raw Data
    # We use the 'burst' folder for high-res snippets
    save_path = io.save_signal(
        volts,
        config.FS_DEFAULT,
        config.DATA_DIR_BURST,
        prefix=FILENAME,
        user_notes="Harmonic Landscape Source Data",
    )

    # 4. Quick Preview (Sanity Check)
    print("📊 Displaying Preview (Close window to exit)...")
    plt.figure(figsize=(10, 4))
    plt.plot(volts[::100], color="cyan", lw=0.5)  # Downsample for speed
    plt.title(f"Preview: {os.path.basename(save_path)}")
    plt.xlabel("Samples (x100)")
    plt.ylabel("Voltage (V)")
    plt.style.use("dark_background")
    plt.grid(alpha=0.3)
    plt.show()


if __name__ == "__main__":
    main()
