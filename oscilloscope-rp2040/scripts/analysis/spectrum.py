import sys
import os
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import io, dsp, config


def analyze_file(filepath):
    print(f"Loading: {filepath}")

    signal, fs = io.load_signal(filepath)

    # Prep analysis
    ac_signal = dsp.remove_dc(signal)
    freqs, mags = dsp.compute_spectrum(ac_signal, fs)
    fundamental = dsp.estimate_fundamental(freqs, mags)

    # Plotting
    t_axis = (np.arange(signal.size) / fs) * 1000

    plt.figure(figsize=(12, 8))

    plt.subplot(2, 1, 1)
    plt.plot(t_axis, signal, color="lime")
    plt.title(f"File: {os.path.basename(filepath)} | Pitch: {fundamental:.1f} Hz")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 1, 2)
    plt.plot(freqs, mags, color="orange")
    plt.xlim(0, 2000)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def main():
    filepath = io.select_file_cli(config.DATA_DIR_BURST)
    if filepath:
        analyze_file(filepath)


if __name__ == "__main__":
    main()
