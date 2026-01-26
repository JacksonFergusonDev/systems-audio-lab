import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from . import config, dsp


def check_signal_health(voltages: np.ndarray):
    """
    Analyzes signal for clipping, silence, and bias drift.
    Returns: is_healthy (bool)
    """
    v_min = np.min(voltages)
    v_max = np.max(voltages)
    v_pp = v_max - v_min
    v_mean = np.mean(voltages)

    print("--- DIAGNOSTICS ---")
    print(f"DC Offset:   {v_mean:.3f} V  (Target: {config.V_MID} V)")
    print(f"Pk-Pk Swing: {v_pp:.3f} V")

    is_healthy = True

    # Check A: Clipping
    if v_min <= 0.02 or v_max >= (config.V_REF - 0.05):
        print("⚠️ WARNING: SIGNAL CLIPPING! Hitting voltage rails.")
        is_healthy = False

    # Check B: Silence
    elif v_pp < 0.05:
        print("⚠️ WARNING: WEAK SIGNAL. Barely above noise floor.")
        is_healthy = False

    # Check C: Bias Drift
    if not (1.5 < v_mean < 1.8):
        print("⚠️ NOTE: Bias drifting. Check V_mid connections.")

    return is_healthy


def analyze_spectrum_peaks(voltages: np.ndarray, fs: float):
    """
    Performs a frequency domain sanity check.
    Returns: (dominant_freq, harmonics_list)
    """
    # 1. AC Couple
    ac_signal = dsp.remove_dc(voltages)

    # 2. Compute Spectrum
    freqs, mags = dsp.compute_spectrum(ac_signal, fs)

    # 3. Find Peaks (Top 3)
    # Ignore tiny noise peaks (<10% of max) and enforce separation
    height_thresh = np.max(mags) * 0.1
    peaks_idx, props = find_peaks(mags, height=height_thresh, distance=50)

    # Sort by height (loudest first)
    sorted_indices = peaks_idx[np.argsort(props["peak_heights"])[::-1]]
    top_indices = sorted_indices[:5]
    top_freqs = freqs[top_indices]

    dominant_freq = top_freqs[0] if len(top_freqs) > 0 else 0.0

    # Print Report
    print(f"🎸 PITCH CHECK: {dominant_freq:.1f} Hz (Dominant)")
    if len(top_freqs) > 1:
        harmonics = ", ".join([f"{f:.1f}" for f in top_freqs[1:]])
        print(f"   Harmonics:  {harmonics} Hz")

    return dominant_freq, top_freqs


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
