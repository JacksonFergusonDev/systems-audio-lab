import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, io, viz


def main():
    filepath = io.select_file_cli(config.DATA_DIR_BURST)
    if filepath:
        print(f"Loading: {filepath}")
        signal, fs = io.load_signal(filepath)

        viz.analyze_signal_plot(signal, fs, title=f"File: {os.path.basename(filepath)}")


if __name__ == "__main__":
    main()
