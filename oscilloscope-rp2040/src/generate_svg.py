import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba

# --- CONFIGURATION ---
INPUT_FILE = "oscilloscope-rp2040/data/continuous/song.npz"
OUTPUT_FILE = "docs/figures/title_graphic.pdf"

LINES = 8
DECIMATE = 7

WAVE_SCALE = 20
LINE_SPACING = 15

# Horizontal zoom: >1 = zoom in (show less of each segment, looks stretched)
X_ZOOM = 35

LINE_WIDTH = 0.8

# --- GLOBAL GRADIENT CONTROLS ---
# Set the top/bottom colors here (any matplotlib color: hex, 'black', etc.)
TOP_COLOR = "#3D3229"
BOTTOM_COLOR = "#3D3229"

# Opacity gradient:
TOP_ALPHA = 1.0
BOTTOM_ALPHA = 1.0

# Fill color that masks stuff behind (leave white unless you want a tinted fill)
FILL_COLOR = "#FFFFFF"
FILL_FOLLOWS_GRADIENT = False  # If True, fill will also color-gradient + alpha-gradient


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgba(c0, c1, t):
    r0, g0, b0, a0 = to_rgba(c0)
    r1, g1, b1, a1 = to_rgba(c1)
    return (lerp(r0, r1, t), lerp(g0, g1, t), lerp(b0, b1, t), lerp(a0, a1, t))


def generate_joyplot():
    # 1. Load Data
    try:
        data = np.load(INPUT_FILE)
        signal = data["data"] if "data" in data else data[data.files[0]]
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}")
        return

    # 2. Pre-process
    signal = signal.flatten()
    signal = signal[::DECIMATE]

    signal = signal.astype(float)
    smin, smax = np.min(signal), np.max(signal)
    if smax == smin:
        print("Error: Signal is constant; cannot normalize.")
        return
    signal = (signal - smin) / (smax - smin)
    signal = signal - 0.5  # center around 0

    # 3. Slice into segments
    total_samples = len(signal)
    samples_per_line = total_samples // LINES

    # 4. Setup Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # 5. Render Loop
    for i in range(LINES):
        start = i * samples_per_line
        end = start + samples_per_line
        if end > total_samples:
            break

        segment = signal[start:end]
        x = np.arange(len(segment))

        y_base = (LINES - i) * LINE_SPACING
        y_curve = (segment * WAVE_SCALE) + y_base

        # t = 0 at top line, 1 at bottom line
        if LINES <= 1:
            t = 0.0
        else:
            t = i / (LINES - 1)

        # Alpha gradient
        alpha = lerp(TOP_ALPHA, BOTTOM_ALPHA, t)

        # Color gradient for the stroke
        stroke_rgb = lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
        stroke_color = (
            stroke_rgb[0],
            stroke_rgb[1],
            stroke_rgb[2],
            1.0,
        )  # keep color opaque; alpha handled separately

        # Fill: either constant masking white, or follow gradient
        if FILL_FOLLOWS_GRADIENT:
            fill_rgb = lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
            fill_color = (fill_rgb[0], fill_rgb[1], fill_rgb[2], 1.0)
            fill_alpha = alpha
        else:
            fill_color = FILL_COLOR
            fill_alpha = 1.0  # keep masking consistent

        ax.fill_between(
            x, y_base, y_curve, color=fill_color, zorder=i, alpha=fill_alpha
        )
        ax.plot(
            x, y_curve, color=stroke_color, lw=LINE_WIDTH, zorder=i + 1, alpha=alpha
        )

    # Horizontal zoom by cropping x-range
    visible = int(samples_per_line / X_ZOOM)
    ax.set_xlim(0, max(visible, 2))

    # Minimal styling
    ax.axis("off")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Save
    print(f"Rendering vector graphic to {OUTPUT_FILE}...")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_FILE, format="pdf", transparent=True, bbox_inches=None, pad_inches=0
    )
    print("Done.")


if __name__ == "__main__":
    generate_joyplot()
