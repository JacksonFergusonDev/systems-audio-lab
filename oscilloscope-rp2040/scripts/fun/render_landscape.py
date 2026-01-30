import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, dsp, io, plots


def main():
    # 1. Load Data
    # Used to use local 'load_latest_file', now uses io.load_latest_file
    voltages, fs = io.load_latest_file(config.DATA_DIR_BURST, "fun_drone*.npz")

    if voltages is None:
        print("No file found.")
        return

    # 2. Process (Remove DC)
    ac_signal = dsp.remove_dc(voltages)

    # 3. Render
    # Old name: plot_joyplot -> New name: plot_spectral_landscape
    plots.plot_spectral_landscape(ac_signal, fs, gamma=0.8)


if __name__ == "__main__":
    main()
