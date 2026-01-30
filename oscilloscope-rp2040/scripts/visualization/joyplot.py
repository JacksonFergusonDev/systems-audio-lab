import argparse
import os
import sys

import numpy as np

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import plots


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Joyplot/Ridgeline plot from audio data."
    )
    parser.add_argument("input", help="Path to input .npz file")
    parser.add_argument(
        "-o", "--output", default="joyplot.pdf", help="Path to output PDF/SVG"
    )
    parser.add_argument("--lines", type=int, default=8, help="Number of lines to stack")
    parser.add_argument(
        "--decimate", type=int, default=7, help="Decimation factor for signal"
    )
    parser.add_argument("--zoom", type=float, default=35, help="Horizontal zoom factor")
    parser.add_argument("--scale", type=float, default=20, help="Vertical wave scaling")

    args = parser.parse_args()

    try:
        data_file = np.load(args.input)
        signal = (
            data_file["data"] if "data" in data_file else data_file[data_file.files[0]]
        )

        plots.plot_joyplot_stacked(
            signal,
            lines=args.lines,
            decimate=args.decimate,
            x_zoom=args.zoom,
            wave_scale=args.scale,
            output_file=args.output,
        )
    except FileNotFoundError:
        print(f"Error: Could not find {args.input}")


if __name__ == "__main__":
    main()
