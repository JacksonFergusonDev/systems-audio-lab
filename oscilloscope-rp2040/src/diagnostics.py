from typing import Any, Dict, Tuple, cast

import numpy as np
from scipy.signal import find_peaks

from . import config, dsp


def check_signal_health(voltages: np.ndarray) -> bool:
    """
    Analyzes the signal for clipping, silence, and bias drift.

    Prints a diagnostic report to the console regarding DC offset,
    peak-to-peak swing, and potential health warnings.

    Parameters
    ----------
    voltages : np.ndarray
        (N,) array of signal voltages (float).

    Returns
    -------
    bool
        True if the signal is considered "healthy" (no clipping,
        adequate amplitude, valid bias). False otherwise.
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


def analyze_spectrum_peaks(voltages: np.ndarray, fs: float) -> Tuple[float, np.ndarray]:
    """
    Performs a frequency domain sanity check by identifying dominant peaks.

    Parameters
    ----------
    voltages : np.ndarray
        (N,) array of signal voltages.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    Tuple[float, np.ndarray]
        - dominant_freq: The frequency of the highest magnitude peak in Hz.
        - top_freqs: Array of the top 5 frequency peaks found, sorted by magnitude.
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
    props_dict = cast(Dict[str, Any], props)
    sorted_indices = peaks_idx[np.argsort(props_dict["peak_heights"])[::-1]]
    top_indices = sorted_indices[:5]
    top_freqs = freqs[top_indices]

    dominant_freq = float(top_freqs[0]) if len(top_freqs) > 0 else 0.0

    # Print Report
    print(f"🎸 PITCH CHECK: {dominant_freq:.1f} Hz (Dominant)")
    if len(top_freqs) > 1:
        harmonics = ", ".join([f"{f:.1f}" for f in top_freqs[1:]])
        print(f"   Harmonics:  {harmonics} Hz")

    return dominant_freq, top_freqs
