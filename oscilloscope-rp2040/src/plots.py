import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import matplotlib.colors as mcolors
import matplotlib.figure as mf
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from scipy.interpolate import make_interp_spline

from . import config, dsp, metrics

# --- Style Configuration ---
COLORS: Dict[str, str] = {
    "clean": "#2ecc71",  # Green (Input)
    "dirty": "#e74c3c",  # Red (Output)
    "noise": "#7f8c8d",  # Gray (Background)
    "even": "#e67e22",  # Orange
    "odd": "#3498db",  # Blue
}


def save_pdf_svg(fig: mf.Figure, savepath: Union[str, Path], **kwargs: Any) -> None:
    """
    Helper to save a figure in both PDF and SVG formats.

    Parameters
    ----------
    fig : plt.Figure
        The matplotlib figure object.
    savepath : Union[str, Path]
        The target path (extension is ignored/replaced).
    **kwargs : Any
        Additional arguments passed to fig.savefig().
    """
    p = Path(savepath)
    stem = p.with_suffix("")
    fig.savefig(stem.with_suffix(".pdf"), **kwargs)
    fig.savefig(stem.with_suffix(".svg"), **kwargs)


def plot_gain_stage(
    sig_clean: np.ndarray,
    sig_dirty: np.ndarray,
    fs: float,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Visualizes the gain difference (Vpp) between input and output signals.

    Plots software-triggered waveforms to align phases and annotates the
    calculated gain in dB.

    Parameters
    ----------
    sig_clean : np.ndarray
        Clean input signal.
    sig_dirty : np.ndarray
        Distorted/Amplified output signal.
    fs : float
        Sampling rate in Hz.
    savepath : Optional[str]
        Path to save the figure (without extension).
    show : bool
        Whether to display the plot.
    """
    m = metrics.calculate_gain_metrics(sig_clean, sig_dirty, duration_ms=25, fs=fs)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    sns.lineplot(
        x=m["t"], y=m["clean_triggered"], ax=ax1, color=COLORS["clean"], alpha=0.8
    )
    ax1.set_title(
        f"Input: Clean DI (Vpp = {m['vpp_in'] * 1000:.1f} mV)", fontweight="bold"
    )
    ax1.set_ylabel("Voltage (V)")
    ax1.set_ylim(-1.5, 1.5)
    ax1.grid(True, alpha=0.3)

    sns.lineplot(x=m["t"], y=m["dirty_triggered"], ax=ax2, color=COLORS["dirty"])
    ax2.set_title(f"Output: Red Llama (Vpp = {m['vpp_out']:.2f} V)", fontweight="bold")
    ax2.set_ylabel("Voltage (V)")
    ax2.set_ylim(-1.5, 1.5)
    ax2.grid(True, alpha=0.3)

    t_peak, y_peak = m["peak_coords"]
    ax2.annotate(
        f"MASSIVE GAIN (+{m['gain_db']:.1f} dB)",
        xy=(t_peak, y_peak),
        xytext=(0.05, 0.9),
        textcoords="axes fraction",
        ha="left",
        va="top",
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85),
        arrowprops=dict(arrowstyle="->", color="black", shrinkA=0, shrinkB=2),
    )
    plt.tight_layout()
    if savepath:
        save_pdf_svg(fig, savepath, bbox_inches="tight")
    if show:
        plt.show()


def plot_spectral_floor(
    sig_signal: np.ndarray,
    sig_noise: np.ndarray,
    fs: float,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Compares signal power spectrum against the instrument noise floor.

    Useful for validating SNR (Signal-to-Noise Ratio) in recordings.
    """
    freqs_sig, mags_sig = metrics.compute_spectrum_data(sig_signal, fs)
    freqs_noise, mags_noise = metrics.compute_spectrum_data(sig_noise, fs)

    fig = plt.figure(figsize=(12, 6))
    plt.semilogy(
        freqs_sig, mags_sig, color=COLORS["clean"], alpha=0.8, label="Signal (Clean E)"
    )
    plt.semilogy(
        freqs_noise,
        mags_noise,
        color=COLORS["noise"],
        alpha=0.9,
        linewidth=1.5,
        label="Noise Floor",
    )
    plt.fill_between(freqs_noise, 0, mags_noise, color=COLORS["noise"], alpha=0.2)

    plt.title("Signal vs. Instrument Noise Floor")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (Log Scale)")
    plt.xlim(0, 5000)
    plt.grid(True, which="both", alpha=0.3)
    plt.legend(loc="upper right")

    if savepath:
        save_pdf_svg(fig, savepath, bbox_inches="tight")
    if show:
        plt.show()


def plot_spectrum_normalized(
    sig_clean: np.ndarray,
    sig_dirty: np.ndarray,
    fs: float,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Compares harmonic content of two signals, normalized to Peak=1.0 (0dB).
    """
    data = metrics.compute_normalized_spectra(sig_clean, sig_dirty, fs)
    fig = plt.figure(figsize=(12, 6))

    plt.semilogy(
        data["freqs_d"],
        data["mags_d"],
        color=COLORS["dirty"],
        alpha=0.6,
        label="Red Llama",
    )
    plt.semilogy(
        data["freqs_c"],
        data["mags_c"],
        color=COLORS["clean"],
        alpha=0.9,
        label="Clean DI",
    )

    plt.title("Normalized Spectral Comparison: Shape vs. Shape")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Normalized Magnitude (Peak = 1.0)")
    plt.xlim(0, 4000)
    plt.ylim(1e-4, 1.5)
    plt.grid(True, which="both", alpha=0.3)
    plt.legend(loc="upper right")

    if savepath:
        save_pdf_svg(fig, savepath, bbox_inches="tight")
    if show:
        plt.show()


def analyze_harmonics_fixed(
    signal: np.ndarray,
    fs: float,
    fundamental_freq: float = 82.4,
    n_harmonics: int = 10,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Generates a bar chart of the first N harmonics.

    Prints the relative magnitudes of the first three harmonics to stdout
    for quick analysis of timbre (e.g., Even vs Odd harmonics).
    """
    df = metrics.extract_harmonics_list(signal, fs, fundamental_freq, n_harmonics)

    if df is None:
        print("⚠️ Could not find fundamental! Check frequency.")
        return

    # Print stats to stdout
    print("--- HARMONIC ANALYSIS ---")
    mags = df["Magnitude"].values
    if len(mags) >= 1:
        print(f"Fundamental (1f): {mags[0]:.2f}")
    if len(mags) >= 2:
        print(f"2nd Harmonic (2f): {mags[1]:.2f} (Octave - Warmth/Asymmetry)")
    if len(mags) >= 3:
        print(f"3rd Harmonic (3f): {mags[2]:.2f} (Fifth - Square/Symmetry)")

    fig = plt.figure(figsize=(10, 5))
    custom_palette = {"Odd": COLORS["odd"], "Even": COLORS["even"]}
    sns.barplot(
        data=df,
        x="Harmonic",
        y="Magnitude",
        hue="Type",
        palette=custom_palette,
        dodge=False,
    )

    plt.title("Harmonic Series Distribution (Normalized to Fundamental)")
    plt.ylabel("Relative Amplitude")
    plt.xlabel("Harmonic Order")
    plt.grid(axis="y", alpha=0.3)
    plt.legend(title="Harmonic Type")

    if savepath:
        save_pdf_svg(fig, savepath, bbox_inches="tight")
    if show:
        plt.show()


def plot_bode_response(
    sig_src: np.ndarray,
    sig_dut: np.ndarray,
    fs: float,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Plots the Deconvolved Linear Frequency Response and Impulse Response.

    Uses Farina's method (ESS Deconvolution) to separate linear response
    from harmonic distortion.
    """
    data = metrics.compute_bode_data(sig_src, sig_dut, fs)

    fig = plt.figure(figsize=(10, 8))
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])

    # --- Top Panel: Magnitude Response ---
    ax1 = plt.subplot(gs[0])
    ax1.semilogx(
        data["freqs"],
        data["gain_db"],
        color=COLORS["dirty"],
        linewidth=2,
        label="Linear Response (Deconvolved)",
    )

    ax1.set_title(
        "Deconvolved Frequency Response (Farina Method)", fontsize=14, fontweight="bold"
    )
    ax1.set_ylabel("Normalized Gain (dB)")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.set_xlim(20, 20000)
    ax1.set_ylim(-40, 5)  # Focus on the passband

    # Peak Annotation
    ax1.axhline(data["peak_db"], color="gray", linestyle="--", alpha=0.5)
    ax1.text(
        25,
        data["peak_db"] + 1,
        f"Peak Resonance: {data['peak_freq']:.0f} Hz",
        color=COLORS["dirty"],
        fontweight="bold",
    )
    ax1.legend(loc="lower right")

    # --- Bottom Panel: The Impulse Response ---
    ax2 = plt.subplot(gs[1])
    ir = data["ir_preview"]
    t_ir = data["ir_time_ms"]

    ax2.plot(t_ir, ir, color=COLORS["odd"], linewidth=1)
    ax2.set_title(
        "Extracted Impulse Response (Causal Window)", fontsize=10, fontweight="bold"
    )
    ax2.set_xlabel("Time relative to Linear Peak (ms)")
    ax2.set_xlim(min(t_ir), max(t_ir))
    ax2.set_yticks([])
    ax2.grid(True, alpha=0.3)
    # Mark the peak
    ax2.axvline(0, color=COLORS["dirty"], linestyle=":", alpha=0.6, label="Linear Peak")
    ax2.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    if savepath:
        save_pdf_svg(fig, savepath)
    if show:
        plt.show()


def plot_transfer_curve(
    sig_src: np.ndarray,
    sig_dut: np.ndarray,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Visualizes the Non-Linear Transfer Characteristic (Vin vs Vout).

    This "Soft Clipping Sigmoid" reveals the saturation behavior of the DUT.
    """
    x, y = metrics.prepare_transfer_curve(sig_src, sig_dut)
    fig = plt.figure(figsize=(8, 8))

    # Decimate for scatter performance
    step = max(1, len(x) // 5000)
    plt.scatter(x[::step], y[::step], c=x[::step], cmap="coolwarm", alpha=0.1, s=2)
    plt.plot(
        [-1, 1], [-1, 1], color="gray", linestyle="--", alpha=0.5, label="Linear Unity"
    )

    plt.title(
        "Non-Linear Transfer Characteristic (Soft Clipping)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Input Amplitude (Normalized)")
    plt.ylabel("Output Amplitude (Normalized)")
    plt.grid(True, alpha=0.3)
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)
    plt.text(
        -0.8, 0.9, "Hard Rail (Saturation)", color=COLORS["dirty"], fontweight="bold"
    )
    plt.text(0, 0.2, "Linear Region", ha="center", color=COLORS["odd"])

    if savepath:
        save_pdf_svg(fig, savepath)
    if show:
        plt.show()


def plot_thd_fingerprint(
    sig: np.ndarray,
    fs: float = 97812.0,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Visualizes the THD spectrum at 1kHz.

    Annotates the first few harmonics to identify the distortion profile
    (e.g., dominance of Even vs Odd harmonics).
    """
    thd_pct = dsp.calculate_selective_thd(sig, fs, fundamental_freq=1000.0)
    freqs, mags = dsp.compute_spectrum(sig, fs)

    # Normalize to fundamental
    fund_mask = (freqs > 900) & (freqs < 1100)
    mags_norm = mags / np.max(mags[fund_mask]) if np.any(fund_mask) else mags

    fig = plt.figure(figsize=(12, 5))
    plt.plot(freqs, mags_norm, color=COLORS["dirty"], alpha=0.9)
    plt.fill_between(freqs, 0, mags_norm, color=COLORS["dirty"], alpha=0.2)

    plt.title(
        f"Spectral Fingerprint (THD = {thd_pct:.2f}%)", fontsize=14, fontweight="bold"
    )
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Normalized Amplitude")
    plt.xlim(0, 10000)
    plt.ylim(0, 1.1)
    plt.grid(True, alpha=0.3)

    for h in [2, 3, 4, 5]:
        f_h = 1000 * h
        mask = (freqs > f_h - 100) & (freqs < f_h + 100)
        if np.any(mask):
            mag_h = np.max(mags_norm[mask])
            label = "Even" if h % 2 == 0 else "Odd"
            plt.text(f_h, mag_h + 0.05, f"{h}f\n({label})", ha="center", fontsize=9)

    if savepath:
        save_pdf_svg(fig, savepath)
    if show:
        plt.show()


def plot_final_report(
    sig_clean: np.ndarray,
    sig_dirty: np.ndarray,
    fs: float,
    duration_ms: float = 12,
    savepath: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Generates the composite Figure 1 (Waveform Morphology + Harmonic Analysis).

    Combines a time-domain phase-aligned plot with a bar chart of harmonic content.
    """
    fig = plt.figure(figsize=(16, 7))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1.2])

    # Panel A: Time Domain
    ax1 = plt.subplot(gs[0])
    samples = int((duration_ms / 1000) * fs)
    t = (np.arange(samples) / fs) * 1000
    norm_c = sig_clean / np.max(np.abs(sig_clean))
    norm_d = sig_dirty / np.max(np.abs(sig_dirty))
    aligned_c = dsp.smart_align(norm_d[: samples * 2], norm_c[: samples * 2])

    ax1.plot(
        t, aligned_c[:samples], color=COLORS["clean"], alpha=0.5, label="Clean Input"
    )
    ax1.plot(
        t, norm_d[:samples], color=COLORS["dirty"], linewidth=2.5, label="Red Llama"
    )
    ax1.set_title(
        "A. Topology: The 'Soft Knee' (Phase Locked)", fontweight="bold", fontsize=14
    )
    ax1.set_xlabel("Time (ms)")
    ax1.legend(loc="lower right")
    ax1.grid(True, alpha=0.3)

    # Panel B: Frequency Domain
    ax2 = plt.subplot(gs[1])
    df = metrics.compute_spectral_comparison(sig_clean, sig_dirty, fs)
    if df is not None:
        sns.barplot(
            data=df,
            x="Harmonic",
            y="Magnitude",
            hue="Signal",
            palette={"Clean Input": COLORS["clean"], "Red Llama": COLORS["dirty"]},
            ax=ax2,
        )
        ax2.set_title(
            "B. Harmonic Fingerprint (Input vs. Output)", fontweight="bold", fontsize=14
        )
        ax2.set_ylabel("Relative Amplitude (Fund. = 1.0)")
        ax2.grid(axis="y", alpha=0.3)
        ax2.text(
            0.2,
            0.8,
            "Tube Asymmetry\n(Octave Added)",
            transform=ax2.transAxes,
            ha="left",
            color=COLORS["dirty"],
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85),
        )

    plt.tight_layout()
    if savepath:
        save_pdf_svg(fig, savepath, bbox_inches="tight")
    if show:
        plt.show()


def plot_health_check(
    voltages: np.ndarray, fs: float, title: str, is_healthy: bool
) -> None:
    """
    Standard diagnostics plot for signal integrity verification.

    Shows the signal trace with overlay lines for voltage rails and virtual ground.
    """
    plt.figure(figsize=(12, 4))
    plt.plot(voltages, color="lime" if is_healthy else "orange", lw=0.7)

    # Safety Rails
    plt.axhline(config.V_REF, color="red", linestyle="--", alpha=0.5)
    plt.axhline(0.0, color="red", linestyle="--", alpha=0.5)
    plt.axhline(config.V_MID, color="cyan", linestyle=":", alpha=0.5, label="V_mid")

    plt.title(f"{title} (FS={fs:.0f}Hz)")
    plt.ylabel("Voltage (V)")
    plt.xlabel("Samples")
    plt.ylim(-0.1, config.V_REF + 0.1)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right")
    plt.show()


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_rgba(c0: str, c1: str, t: float) -> Tuple[float, float, float, float]:
    r0, g0, b0, a0 = to_rgba(c0)
    r1, g1, b1, a1 = to_rgba(c1)
    return (_lerp(r0, r1, t), _lerp(g0, g1, t), _lerp(b0, b1, t), _lerp(a0, a1, t))


def plot_joyplot_stacked(
    signal: np.ndarray,
    lines: int = 8,
    decimate: int = 7,
    x_zoom: int = 35,
    wave_scale: float = 20,
    output_file: str = "joyplot.pdf",
) -> None:
    """
    Renders a Ridgeline/Joyplot (stacked lines) from the signal.

    Originally from scripts/visualization/joyplot.py. Creates a vectorized
    PDF graphic suitable for scientific posters or cover art.

    Parameters
    ----------
    signal : np.ndarray
        Input audio signal.
    lines : int
        Number of stacked lines to generate.
    decimate : int
        Downsampling factor to reduce complexity.
    x_zoom : int
        Horizontal zoom factor.
    wave_scale : float
        Vertical scaling factor for the waves.
    output_file : str
        Filename for the saved output.
    """
    # 1. Pre-process
    sig_flat = signal.flatten()
    sig_flat = sig_flat[::decimate]

    sig_flat = sig_flat.astype(float)
    smin, smax = np.min(sig_flat), np.max(sig_flat)
    if smax == smin:
        print("Error: Signal is constant; cannot normalize.")
        return
    sig_flat = (sig_flat - smin) / (smax - smin)
    sig_flat = sig_flat - 0.5  # center around 0

    # 2. Slice into segments
    total_samples = len(sig_flat)
    samples_per_line = total_samples // lines
    line_spacing = 15

    # Gradient Configuration
    TOP_COLOR = "#3D3229"
    BOTTOM_COLOR = "#3D3229"
    TOP_ALPHA = 1.0
    BOTTOM_ALPHA = 1.0
    FILL_COLOR = "#FFFFFF"
    FILL_FOLLOWS_GRADIENT = False

    # 3. Setup Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # 4. Render Loop
    for i in range(lines):
        start = i * samples_per_line
        end = start + samples_per_line
        if end > total_samples:
            break

        segment = sig_flat[start:end]
        x = np.arange(len(segment))

        y_base = (lines - i) * line_spacing
        y_curve = (segment * wave_scale) + y_base

        if lines <= 1:
            t = 0.0
        else:
            t = i / (lines - 1)

        alpha = _lerp(TOP_ALPHA, BOTTOM_ALPHA, t)
        stroke_rgb = _lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
        stroke_color = (stroke_rgb[0], stroke_rgb[1], stroke_rgb[2], 1.0)

        if FILL_FOLLOWS_GRADIENT:
            fill_rgb = _lerp_rgba(TOP_COLOR, BOTTOM_COLOR, t)
            fill_color = (fill_rgb[0], fill_rgb[1], fill_rgb[2], 1.0)
            fill_alpha = alpha
        else:
            fill_color = to_rgba(FILL_COLOR)

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
        output_file, format="pdf", transparent=True, bbox_inches=None, pad_inches=0.0
    )
    print("Done.")


def plot_phase_portrait(
    signal: np.ndarray, delay: int, filename_base: str = "phase_portrait"
) -> None:
    """
    Renders a phase portrait (Time-Delay Embedding / Neon Torus).

    Plots x(t) vs x(t + delay) with time-mapped coloring to visualize
    chaos or periodicity in the signal.
    """
    print("🎨 Rendering Phase Portrait...")

    # 1. Create X and Y (Time-Delay Embedding)
    x = signal[:-delay]
    y = signal[delay:]

    # 2. Setup the "Neon" aesthetic
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 10))

    # 3. Create a colored line collection (Color by time/index)
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Create a color map based on time (0 to 1)
    norm = mcolors.Normalize(0, len(x))
    lc = LineCollection(
        list(segments), cmap="cool", norm=norm, alpha=0.3, linewidth=1.0
    )
    lc.set_array(np.arange(len(x)))

    ax.add_collection(lc)

    # 4. Styling
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")

    # 5. Save Logic
    save_dir = os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "..", "docs", "figures")
    )
    os.makedirs(save_dir, exist_ok=True)

    pdf_path = os.path.join(save_dir, f"{filename_base}.pdf")
    plt.savefig(pdf_path, bbox_inches="tight", pad_inches=0.0, facecolor="black")
    print(f"✨ Saved vector plots to: {pdf_path}")
    plt.show()


def plot_spectral_landscape(
    signal: np.ndarray,
    fs: float,
    slices: int = 70,
    overlap: float = 0.14,
    gamma: float = 0.8,
    res_factor: int = 10,
    filename_base: str = "harmonic_landscape",
) -> None:
    """
    Renders a 3D spectral landscape ("Joyplot" style in frequency domain).

    Visualizes how the frequency spectrum evolves over time by stacking
    successive FFT slices.

    Parameters
    ----------
    signal : np.ndarray
        Input audio signal.
    fs : float
        Sampling rate.
    slices : int
        Number of spectral slices to render.
    overlap : float
        Vertical overlap between slices.
    gamma : float
        Gamma correction for magnitude scaling.
    res_factor : int
        Smoothing resolution factor.
    filename_base : str
        Base filename for the saved PDF.
    """
    print(f"🎨 Rendering Landscape (Gamma={gamma})...")

    # Gradient Configuration
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
    HEIGHT_FACTOR = 0.8
    STACK_ORDER = "bottom_front"

    total_samples = len(signal)
    samples_per_slice = total_samples // slices

    # Setup Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Create Custom Colormap
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_theme", CUSTOM_PALETTE, N=256
    )

    # Iterate through slices
    for i in range(slices):
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
        f_smooth = np.linspace(f_raw.min(), f_raw.max(), len(f_raw) * res_factor)
        spl = make_interp_spline(f_raw, m_raw, k=3)
        m_smooth = spl(f_smooth)
        m_smooth = np.maximum(m_smooth, 0)  # Clip negatives

        # --- NORMALIZATION & COMPRESSION ---
        peak = np.max(m_smooth) if np.max(m_smooth) > 1e-4 else 1.0
        m_smooth = m_smooth / peak
        m_smooth = np.power(m_smooth, gamma)

        # 4. Perspective Math
        y_base = i * overlap
        y_curve = m_smooth * HEIGHT_FACTOR + y_base

        # 5. Z-Order Logic
        if STACK_ORDER == "bottom_front":
            z_base = (slices - i) * 2
        else:
            z_base = i * 2

        # 6. Color Logic
        vol_metric = np.max(np.abs(chunk))
        vol_metric = max(0.0, min(1.0, float(vol_metric)))
        color = cmap(vol_metric)

        # Draw
        ax.fill_between(
            f_smooth, y_base, y_curve, color=FILL_COLOR, alpha=1.0, zorder=z_base
        )
        ax.plot(f_smooth, y_curve, color=color, lw=LINE_WIDTH, zorder=z_base + 1)

    ax.axis("off")
    ax.set_xlim(0, 600)

    # Save
    save_dir = os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "..", "docs", "figures")
    )
    os.makedirs(save_dir, exist_ok=True)
    pdf_path = os.path.join(save_dir, f"{filename_base}.pdf")
    plt.savefig(pdf_path, bbox_inches="tight", pad_inches=0.0, transparent=True)

    print(f"✨ Saved to: {os.path.basename(pdf_path)}")
    plt.show()
