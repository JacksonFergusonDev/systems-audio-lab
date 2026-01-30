import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgba(c0, c1, t):
    r0, g0, b0, a0 = to_rgba(c0)
    r1, g1, b1, a1 = to_rgba(c1)
    return (lerp(r0, r1, t), lerp(g0, g1, t), lerp(b0, b1, t), lerp(a0, a1, t))


def generate_joyplot(input_file, output_file, lines, decimate, x_zoom, wave_scale):
    # 1. Load Data
    try:
        data = np.load(input_file)
        signal = data["data"] if "data" in data else data[data.files[0]]
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return

    # 2. Pre-process
    signal = signal.flatten()
    signal = signal[::decimate]

    signal = signal.astype(float)
    smin, smax = np.min(signal), np.max(signal)
    if smax == smin:
        print("Error: Signal is constant; cannot normalize.")
        return
    signal = (signal - smin) / (smax - smin)
    signal = signal - 0.5  # center around 0

    # 3. Slice into segments
    total_samples = len(signal)
    samples_per_line = total_samples // lines
    line_spacing = 15

    # Gradient Configuration
    TOP_COLOR = "#3D3229"
    BOTTOM_COLOR = "#3D3229"
    TOP_ALPHA = 1.0
    BOTTOM_ALPHA = 1.0
    FILL_COLOR = "#FFFFFF"
    FILL_FOLLOWS_GRADIENT = False

    # 4. Setup Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # 5. Render Loop
    for i in range(lines):
        start = i * samples_per_line
        end = start + samples_per_line
        if end > total_samples:
            break

        segment = signal[start:end]
        x = np.arange(len(segment))

        y_base = (lines - i) * line_spacing
        y_curve = (segment * wave_scale) + y_base

        if lines <= 1:
            t = 0.0
        else:
            t = i / (lines - 1)

        alpha = lerp(TOP_ALPHA, BOTTOM_ALPHA, t)
        stroke_rgb = lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
        stroke_color = (stroke_rgb[0], stroke_rgb[1], stroke_rgb[2], 1.0)

        if FILL_FOLLOWS_GRADIENT:
            fill_rgb = lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
            fill_color = (fill_rgb[0], fill_rgb[1], fill_rgb[2], 1.0)
            fill_alpha = alpha
        else:
            fill_color = FILL_COLOR
            fill_alpha = 1.0

        ax.fill_between(
            x, y_base, y_curve, color=fill_color, zorder=i, alpha=fill_alpha
        )
        ax.plot(x, y_curve, color=stroke_color, lw=0.8, zorder=i + 1, alpha=alpha)

    # Horizontal zoom
    visible = int(samples_per_line / x_zoom)
    ax.set_xlim(0, max(visible, 2))

    # Minimal styling
    ax.axis("off")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Save
    print(f"Rendering vector graphic to {output_file}...")
    plt.tight_layout()
    plt.savefig(
        output_file, format="pdf", transparent=True, bbox_inches=None, pad_inches=0
    )
    print("Done.")


if __name__ == "__main__":
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

    generate_joyplot(
        args.input, args.output, args.lines, args.decimate, args.zoom, args.scale
    )
