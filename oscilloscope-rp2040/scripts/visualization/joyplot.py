"""
Script to generate a Ridgeline/Joyplot visualization from a signal file.

This script parses command-line arguments to customize the rendering of a
stacked line plot (Joyplot).
"""

import argparse
import os
import sys

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import io, plots  # noqa: E402


def main() -> None:
    """
    Main execution entry point.

    Parses CLI arguments for input file, styling options (lines, zoom, scale),
    and output path. Loads the signal using the project's standard IO module
    and delegates rendering to `src.plots.plot_joyplot_stacked`.
    """
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

    # Load signal using the standard project loader
    # io.load_signal handles FileNotFoundError and legacy formats internally
    signal, _ = io.load_signal(args.input)

    plots.plot_joyplot_stacked(
        signal,
        lines=args.lines,
        decimate=args.decimate,
        x_zoom=int(args.zoom),
        wave_scale=args.scale,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
