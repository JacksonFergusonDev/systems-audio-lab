"""
Script to replay a continuous signal recording in an oscilloscope-like view.

This utility allows the user to select a recording from the 'continuous' data
directory and visualizes it frame-by-frame, mimicking the live oscilloscope
experience. It is useful for reviewing long capture sessions.
"""

import os

import numpy as np
from sysaudio import config, dsp, io, viz


def main() -> None:
    """
    Main execution entry point.

    Prompts the user to select a file, loads the signal data, converts raw
    ADC values to voltages if necessary, and launches the playback visualization.
    """
    # 1. Select File via CLI menu
    filepath = io.select_file_cli(config.DATA_DIR_CONTINUOUS)
    if not filepath:
        return

    print(f"Loading {filepath}...")
    data, fs = io.load_signal(filepath)

    # 2. Normalize Data if needed (handle raw uint16 captures vs processed floats)
    if np.issubdtype(data.dtype, np.integer):
        print("Detected Raw ADC data. Converting to Volts...")
        data = dsp.raw_to_volts(data)

    # 3. Launch Visualization
    viz.run_playback_scope(data, fs, title=f"PLAYBACK: {os.path.basename(filepath)}")


if __name__ == "__main__":
    main()
