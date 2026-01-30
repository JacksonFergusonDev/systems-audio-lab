import os
import sys

import numpy as np

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, dsp, io, viz


def main():
    # 1. Select File
    filepath = io.select_file_cli(config.DATA_DIR_CONTINUOUS)
    if not filepath:
        return

    print(f"Loading {filepath}...")
    data, fs = io.load_signal(filepath)

    # 2. Normalize Data if needed
    if np.issubdtype(data.dtype, np.integer):
        print("Detected Raw ADC data. Converting to Volts...")
        data = dsp.raw_to_volts(data)

    # 3. Run
    viz.run_playback_scope(data, fs, title=f"PLAYBACK: {os.path.basename(filepath)}")


if __name__ == "__main__":
    main()
