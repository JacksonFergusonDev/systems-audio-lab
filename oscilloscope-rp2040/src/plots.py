import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
from pathlib import Path
from typing import Optional, Union, Any
from . import dsp, metrics, config

# --- Style Configuration ---
COLORS = {
    "clean": "#2ecc71",  # Green (Input)
    "dirty": "#e74c3c",  # Red (Output)
    "noise": "#7f8c8d",  # Gray (Background)
    "even": "#e67e22",  # Orange
    "odd": "#3498db",  # Blue
}


def save_pdf_svg(fig: plt.Figure, savepath: Union[str, Path], **kwargs: Any) -> None:
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
    """Visualizes gain difference (Vpp)."""
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
    """Compares signal power spectrum against instrument noise floor."""
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
    """Compares harmonic content normalized to 0dB."""
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
    """Bar chart of first N harmonics (Legacy Phase 1 function)."""
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
    Plots the Deconvolved Linear Frequency Response and the extracted Impulse Response.
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
    """Visualizes Soft Clipping Sigmoid (Vin vs Vout)."""
    x, y = metrics.prepare_transfer_curve(sig_src, sig_dut)
    fig = plt.figure(figsize=(8, 8))

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
    """Visualizes 1kHz THD Spectrum."""
    thd_pct = dsp.calculate_selective_thd(sig, fs, fundamental_freq=1000.0)
    freqs, mags = dsp.compute_spectrum(sig, fs)

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
    """Generates composite Figure 1 (Morphology + Harmonics)."""
    fig = plt.figure(figsize=(16, 7))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1.2])

    # Panel A
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

    # Panel B
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


def plot_health_check(voltages: np.ndarray, fs: float, title: str, is_healthy: bool):
    """Standard verification plot."""
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
