"""
Script to render a 3D spectral landscape ("Joyplot") from a drone recording.

This script loads the most recent "fun_drone" burst recording, removes the
DC offset, and generates a stacked spectral visualization using the
`plots.plot_spectral_landscape` function.
"""

import os
import sys

# Ensure src is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sysaudio import config, dsp, io, plots  # noqa: E402


def main() -> None:
    """
    Main execution entry point.

    Loads the latest drone recording, performs signal conditioning,
    and triggers the landscape rendering.
    """
    # 1. Load Data
    print("📂 Searching for latest drone recording...")
    voltages, fs = io.load_latest_file(config.DATA_DIR_BURST, "fun_drone*.npz")

    if voltages is None or fs is None:
        print("❌ No matching file found.")
        return

    # 2. Process (Remove DC offset)
    ac_signal = dsp.remove_dc(voltages)

    # 3. Render
    # Generates a "Joyplot" style frequency domain visualization
    plots.plot_spectral_landscape(ac_signal, fs, gamma=0.8)


if __name__ == "__main__":
    main()
