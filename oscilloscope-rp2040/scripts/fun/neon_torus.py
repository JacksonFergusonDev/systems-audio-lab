import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
from matplotlib.collections import LineCollection

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, daq, dsp

# --- CONFIGURATION ---
FREQ_1 = 55.0
FREQ_2 = 56.0  # 1 Hz difference = 1 beat per second
DURATION = 10.0
AMP = 0.2
DELAY_SAMPLES = 800  # "Opening" of the loop.


def generate_drone(duration, fs, amp):
    t = np.arange(int(duration * fs)) / fs
    # Sum of two sines
    wave = np.sin(2 * np.pi * FREQ_1 * t) + np.sin(2 * np.pi * FREQ_2 * t)
    # Normalize to amp
    wave = (wave / 2) * amp
    return wave.astype(np.float32)


def plot_phase_portrait(signal, delay, filename_base="phase_portrait"):
    print("🎨 Rendering Phase Portrait...")

    # 1. Create X and Y (Time-Delay Embedding)
    x = signal[:-delay]
    y = signal[delay:]

    # 2. Setup the "Neon" aesthetic
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 10))

    # 3. Create a colored line collection (Color by time/index)
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Create a color map based on time (0 to 1)
    norm = plt.Normalize(0, len(x))
    lc = LineCollection(segments, cmap="cool", norm=norm, alpha=0.3, linewidth=1.0)
    lc.set_array(np.arange(len(x)))

    ax.add_collection(lc)

    # 4. Styling
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")

    # 5. Save Logic (Vector Graphics)
    # Target: .../docs/figures/
    save_dir = os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "..", "docs", "figures")
    )
    os.makedirs(save_dir, exist_ok=True)

    # Save PDF
    pdf_path = os.path.join(save_dir, f"{filename_base}.pdf")
    plt.savefig(pdf_path, bbox_inches="tight", pad_inches=0, facecolor="black")

    # Save SVG
    svg_path = os.path.join(save_dir, f"{filename_base}.svg")
    plt.savefig(svg_path, bbox_inches="tight", pad_inches=0, facecolor="black")

    print(f"✨ Saved vector plots to:\n   {pdf_path}\n   {svg_path}")
    plt.show()


def main():
    fs_audio = 48000
    print(f"🔹 Generating Drone ({FREQ_1}Hz + {FREQ_2}Hz)...")
    wave = generate_drone(DURATION, fs_audio, AMP)

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

    # Remove DC and Normalize
    ac_signal = dsp.remove_dc(volts)
    norm_signal = ac_signal / np.max(np.abs(ac_signal))

    plot_phase_portrait(norm_signal, DELAY_SAMPLES)


if __name__ == "__main__":
    main()
