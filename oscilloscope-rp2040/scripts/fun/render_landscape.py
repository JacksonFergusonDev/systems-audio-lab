import glob
import os
import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, dsp

# --- VISUAL CONFIGURATION (EDIT ME!) ---
SLICES = 70
OVERLAP = 0.14
RES_FACTOR = 10
STACK_ORDER = "bottom_front"

# --- NEW: DYNAMIC RANGE CONTROLS ---
# GAMMA: Compression factor (0.0 to 1.0).
# 1.0 = Linear (Normal). 0.5 = Square Root (Boosts lows). 0.3 = Aggressive squash.
GAMMA = 0.8

# HEIGHT_FACTOR: How tall the max peak should be relative to the gap between lines.
# Lower this if the main peak is overlapping too much.
HEIGHT_FACTOR = 0.8

# Gradient
CUSTOM_PALETTE = [
    "#020202",  # Black
    "#13010B",  # Deep Purple
    "#011409",  # Magenta
    "#005A66",  # Orange
    "#3D0023",  # Yellow
]

BG_COLOR = "none"
FILL_COLOR = "white"
LINE_WIDTH = 1.2
AXIS_VISIBILITY = "off"


def load_latest_file():
    """Finds the most recent 'fun_drone' file in the burst directory."""
    search_path = os.path.join(config.DATA_DIR_BURST, "fun_drone*.npz")
    files = glob.glob(search_path)
    if not files:
        raise FileNotFoundError(
            f"No recordings found in {search_path}. Run record_drone.py first!"
        )

    # Sort by modification time (newest last)
    latest_file = max(files, key=os.path.getmtime)
    print(f"📂 Loading: {os.path.basename(latest_file)}")

    data = np.load(latest_file)

    try:
        return data["signal"], float(data["fs"])
    except KeyError:
        print(f"⚠️  KeyError! keys found in file: {list(data.files)}")
        first_key = data.files[0]
        print(f"   -> Defaulting to first key: '{first_key}'")
        return data[first_key], float(data["fs"])


def plot_joyplot(signal, fs, filename_base="harmonic_landscape"):
    print(f"🎨 Rendering Landscape (Gamma={GAMMA})...")

    total_samples = len(signal)
    samples_per_slice = total_samples // SLICES

    # Setup Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Create Custom Colormap
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_theme", CUSTOM_PALETTE, N=256
    )

    # Iterate through slices
    for i in range(SLICES):
        start = i * samples_per_slice
        end = start + samples_per_slice
        chunk = signal[start:end]

        # 1. Compute Spectrum
        freqs, mags = dsp.compute_spectrum(chunk, fs)

        # 2. Crop (0-600Hz)
        mask = (freqs > 0) & (freqs < 600)
        f_raw = freqs[mask]
        m_raw = mags[mask]

        if len(f_raw) < 2:
            continue

        # 3. Smooth
        f_smooth = np.linspace(f_raw.min(), f_raw.max(), len(f_raw) * RES_FACTOR)
        spl = make_interp_spline(f_raw, m_raw, k=3)
        m_smooth = spl(f_smooth)
        m_smooth = np.maximum(m_smooth, 0)  # Clip negatives

        # --- NORMALIZATION & COMPRESSION ---

        # A. Normalize Linear (0.0 to 1.0)
        peak = np.max(m_smooth) if np.max(m_smooth) > 1e-4 else 1.0
        m_smooth = m_smooth / peak

        # B. Apply Gamma Compression (The "Squash")
        # This boosts quiet parts while keeping Peak=1.0 the same.
        m_smooth = np.power(m_smooth, GAMMA)

        # 4. Perspective Math
        # Apply HEIGHT_FACTOR here
        y_base = i * OVERLAP
        y_curve = m_smooth * HEIGHT_FACTOR + y_base

        # 5. Z-Order Logic
        if STACK_ORDER == "bottom_front":
            z_base = (SLICES - i) * 2
        else:
            z_base = i * 2

        # 6. Color Logic
        vol_metric = np.max(np.abs(chunk))
        vol_metric = max(0.0, min(1.0, vol_metric))

        color = cmap(vol_metric)

        # Draw
        ax.fill_between(
            f_smooth, y_base, y_curve, color=FILL_COLOR, alpha=1.0, zorder=z_base
        )
        ax.plot(f_smooth, y_curve, color=color, lw=LINE_WIDTH, zorder=z_base + 1)

    ax.axis(AXIS_VISIBILITY)
    ax.set_xlim(0, 600)

    # Save
    save_dir = os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "..", "docs", "figures")
    )
    os.makedirs(save_dir, exist_ok=True)

    pdf_path = os.path.join(save_dir, f"{filename_base}.pdf")
    svg_path = os.path.join(save_dir, f"{filename_base}.svg")

    plt.savefig(pdf_path, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.savefig(svg_path, bbox_inches="tight", pad_inches=0, transparent=True)

    print(f"✨ Saved to: {os.path.basename(pdf_path)}")
    plt.show()


def main():
    # 1. Load Data
    voltages, fs = load_latest_file()

    # 2. Process (Remove DC)
    ac_signal = dsp.remove_dc(voltages)

    # 3. Render
    plot_joyplot(ac_signal, fs)


if __name__ == "__main__":
    main()
