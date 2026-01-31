"""
Script to visualize the frequency spectrum of a captured signal file.

This utility allows the user to select a previously recorded burst file
and displays a static report containing the waveform and its FFT magnitude spectrum.
"""

import os
import sys

# Ensure src is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, io, viz


def main() -> None:
    """
    Interactive script entry point.

    Prompts the user to select a burst recording from the data directory
    and generates a static analysis plot (Time Domain + Frequency Spectrum).
    """
    filepath = io.select_file_cli(config.DATA_DIR_BURST)

    if filepath:
        print(f"Loading: {filepath}")
        signal, fs = io.load_signal(filepath)

        viz.analyze_signal_plot(signal, fs, title=f"File: {os.path.basename(filepath)}")


if __name__ == "__main__":
    main()
