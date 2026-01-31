from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.signal as spsig

from . import dsp


def calculate_gain_metrics(
    sig_clean: np.ndarray, sig_dirty: np.ndarray, duration_ms: float, fs: float
) -> Dict[str, Any]:
    """
    Computes Vpp gain and identifies the peak gain region.

    Parameters
    ----------
    sig_clean : np.ndarray
        The input (reference) signal.
    sig_dirty : np.ndarray
        The output (distorted) signal.
    duration_ms : float
        Analysis window duration in milliseconds.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing time axis, triggered signals, Vpp measurements,
        calculated gain in dB, and peak coordinates.
    """
    samples = int((duration_ms / 1000) * fs)
    t = (np.arange(samples) / fs) * 1000

    # Align signals using software trigger
    trig_c = dsp.software_trigger(sig_clean, threshold=0)[:samples]
    trig_d = dsp.software_trigger(sig_dirty, threshold=0)[:samples]

    vpp_c = np.max(trig_c) - np.min(trig_c)
    vpp_d = np.max(trig_d) - np.min(trig_d)

    # Calculate Gain
    gain_linear = vpp_d / vpp_c if vpp_c > 1e-6 else 0.0
    gain_db = 20 * np.log10(gain_linear) if gain_linear > 0 else 0.0

    # Find Peak Gain coordinates (focus on 6ms +/- 1ms window)
    x0 = 6.0
    win_ms = 1.0
    mask = (t >= x0 - win_ms) & (t <= x0 + win_ms)

    if np.any(mask):
        i_peak = np.argmax(trig_d[mask])
        t_peak = float(t[mask][i_peak])
        y_peak = float(trig_d[mask][i_peak])
    else:
        t_peak, y_peak = 0.0, 0.0

    return {
        "t": t,
        "clean_triggered": trig_c,
        "dirty_triggered": trig_d,
        "vpp_in": float(vpp_c),
        "vpp_out": float(vpp_d),
        "gain_db": float(gain_db),
        "peak_coords": (t_peak, y_peak),
    }


def compute_spectrum_data(
    signal: np.ndarray, fs: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Wrapper for dsp.compute_spectrum to keep metrics generic.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (freq_axis, magnitude)
    """
    return dsp.compute_spectrum(dsp.remove_dc(signal), fs)


def compute_bode_data_broken(
    sig_src: np.ndarray, sig_dut: np.ndarray, fs: float
) -> Dict[str, Any]:
    """
    Derives the System Transfer Function H(f) using the H1 Estimator method.

    Calculates H1 = Pxy / Pxx (Cross-Spectral Density / Power Spectral Density).
    This method is robust against noise but sensitive to non-linearities.

    Parameters
    ----------
    sig_src : np.ndarray
        Source/Input signal.
    sig_dut : np.ndarray
        DUT/Output signal.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing frequencies, gain (dB), coherence, and peak metrics.
    """
    # 1. Alignment (Critical for phase correlation)
    # Normalize for correlation calculation
    norm_src = sig_src / np.max(np.abs(sig_src))
    norm_dut = sig_dut / np.max(np.abs(sig_dut))

    correlation = spsig.correlate(norm_dut, norm_src, mode="full")
    lags = spsig.correlation_lags(norm_dut.size, norm_src.size, mode="full")
    lag = lags[np.argmax(correlation)]

    # Shift DUT to match Source
    if lag > 0:
        sig_dut_aligned = sig_dut[lag:]
        sig_src_aligned = sig_src[: len(sig_dut_aligned)]
    else:
        sig_src_aligned = sig_src[-lag:]
        sig_dut_aligned = sig_dut[: len(sig_src_aligned)]

    # Truncate to matching length
    n = min(len(sig_src_aligned), len(sig_dut_aligned))
    x = sig_src_aligned[:n]
    y = sig_dut_aligned[:n]

    # 2. Compute Estimators (Welch's Method)
    # 4096 samples gives ~23Hz resolution at 96kHz
    nperseg = 4096

    # Pxx: Power Spectral Density of Input
    f, Pxx = spsig.welch(x, fs, nperseg=nperseg)
    # Pxy: Cross Spectral Density
    _, Pxy = spsig.csd(x, y, fs, nperseg=nperseg)
    # Cxy: Coherence (0 to 1 reliability metric)
    _, Cxy = spsig.coherence(x, y, fs, nperseg=nperseg)

    # 3. Calculate H1 Transfer Function
    H = Pxy / Pxx
    gain_db = 20 * np.log10(np.abs(H) + 1e-9)

    # 4. Smoothing
    window_size = 5
    gain_smooth = np.convolve(gain_db, np.ones(window_size) / window_size, mode="same")
    coherence_smooth = np.convolve(Cxy, np.ones(window_size) / window_size, mode="same")

    # Find Peak (valid frequencies > 20Hz only)
    valid_mask = (f > 20) & (f < 20000)
    max_idx = np.argmax(gain_smooth[valid_mask])
    # Adjust index relative to full array
    real_idx = np.where(valid_mask)[0][max_idx]

    return {
        "freqs": f,
        "gain_db": gain_smooth,
        "coherence": coherence_smooth,
        "peak_db": float(gain_smooth[real_idx]),
        "peak_freq": float(f[real_idx]),
    }


def prepare_transfer_curve(
    sig_src: np.ndarray, sig_dut: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Normalizes and phase-aligns signals for XY transfer curve plotting.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (aligned_source, aligned_dut) normalized to 1.0.
    """
    norm_src = sig_src / np.max(np.abs(sig_src))
    norm_dut = sig_dut / np.max(np.abs(sig_dut))
    aligned_src = dsp.smart_align(norm_dut, norm_src)
    n = min(len(aligned_src), len(norm_dut))
    return aligned_src[:n], norm_dut[:n]


def extract_harmonics_list(
    signal: np.ndarray, fs: float, fundamental_freq: float, n_harmonics: int = 10
) -> Optional[pd.DataFrame]:
    """
    Extracts magnitude relative to fundamental for the first N harmonics.

    Parameters
    ----------
    signal : np.ndarray
        Input signal.
    fs : float
        Sampling rate.
    fundamental_freq : float
        Base frequency to search for.
    n_harmonics : int
        Number of harmonics to extract.

    Returns
    -------
    Optional[pd.DataFrame]
        DataFrame with columns [Harmonic, Order, Magnitude, Type], or None if
        fundamental is missing.
    """
    freqs, mags = dsp.compute_spectrum(signal, fs)
    window = 10

    fund_mask = (freqs > fundamental_freq - window) & (
        freqs < fundamental_freq + window
    )
    if not np.any(fund_mask):
        return None

    fund_mag = np.max(mags[fund_mask])
    data = []

    for i in range(1, n_harmonics + 1):
        target_f = fundamental_freq * i
        mask = (freqs > target_f - window) & (freqs < target_f + window)
        mag = np.max(mags[mask]) if np.any(mask) else 0.0

        data.append(
            {
                "Harmonic": f"{i}f",
                "Order": int(i),
                "Magnitude": float(mag / fund_mag),
                "Type": "Even" if i % 2 == 0 else "Odd",
            }
        )

    return pd.DataFrame(data)


def compute_normalized_spectra(
    sig_clean: np.ndarray, sig_dirty: np.ndarray, fs: float
) -> Dict[str, np.ndarray]:
    """
    Computes spectra for two signals, normalized to Peak=1.0.

    Returns
    -------
    Dict[str, np.ndarray]
        Keys: 'freqs_c', 'mags_c', 'freqs_d', 'mags_d'
    """
    f_c, m_c = dsp.compute_spectrum(sig_clean, fs)
    f_d, m_d = dsp.compute_spectrum(sig_dirty, fs)

    return {
        "freqs_c": f_c,
        "mags_c": m_c / np.max(m_c),
        "freqs_d": f_d,
        "mags_d": m_d / np.max(m_d),
    }


def compute_spectral_comparison(
    sig_clean: np.ndarray, sig_dirty: np.ndarray, fs: float, fundamental: float = 82.4
) -> Optional[pd.DataFrame]:
    """
    Generates a comparative DataFrame of harmonic magnitudes for two signals.

    Returns
    -------
    Optional[pd.DataFrame]
        Combined DataFrame labeled by 'Signal' source, or None if extraction fails.
    """
    df_c = extract_harmonics_list(sig_clean, fs, fundamental, n_harmonics=6)
    df_d = extract_harmonics_list(sig_dirty, fs, fundamental, n_harmonics=6)

    if df_c is None or df_d is None:
        return None

    df_c["Signal"] = "Clean Input"
    df_d["Signal"] = "Red Llama"
    return pd.concat([df_c, df_d], ignore_index=True)


def generate_inverse_filter(
    f_start: float, f_end: float, duration: float, fs: float
) -> np.ndarray:
    """
    Generates the Inverse Filter for a Logarithmic Sine Sweep (Farina 2000).

    This filter corrects the -3dB/octave slope of the log sweep (Pink Noise profile)
    to a flat White Noise profile during deconvolution.

    Returns
    -------
    np.ndarray
        The time-reversed, amplitude-weighted inverse sweep.
    """
    n = int(round(duration * fs))
    t = np.arange(n, dtype=np.float64) / fs

    # 1. Regenerate the ideal sweep
    R = (f_end / f_start) ** (1.0 / duration)
    B = 2.0 * np.pi * f_start / np.log(R)
    phase = B * (R**t - 1.0)
    sweep = np.sin(phase)

    # 2. Generate Amplitude Envelope (Blue Noise Slope)
    # Corrects pink noise spectrum of log sweep.
    w = np.exp(t * np.log(R) / duration)

    # 3. Create Inverse
    # Time reverse the weighted sweep to place high frequencies at the start.
    inv_filter = np.flip(sweep * w)
    inv_filter /= np.max(np.abs(inv_filter))

    return inv_filter  # type: ignore[no-any-return]


def compute_impulse_response(
    sig_dut: np.ndarray,
    fs: float,
    f_start: float = 20.0,
    f_end: float = 20000.0,
    duration: float = 5.0,
) -> Tuple[np.ndarray, int]:
    """
    Performs Deconvolution to extract the Linear Impulse Response (IR).

    Uses FFT convolution with the analytic inverse of the log sine sweep.

    Returns
    -------
    Tuple[np.ndarray, int]
        (impulse_response, peak_index)
    """
    inv_filter = generate_inverse_filter(f_start, f_end, duration, fs)

    # FFT Convolution (faster than time domain)
    ir_raw = spsig.fftconvolve(sig_dut, inv_filter, mode="full")

    # Robust Peak Finding
    # Search second half to avoid initial transients/harmonic distortion.
    search_start = len(ir_raw) // 2
    peak_idx_local = np.argmax(np.abs(ir_raw[search_start:]))
    peak_idx = search_start + peak_idx_local

    return ir_raw, int(peak_idx)


def compute_bode_data(
    sig_src: np.ndarray, sig_dut: np.ndarray, fs: float
) -> Dict[str, Any]:
    """
    Derives the Linear Frequency Response using ESS Deconvolution.

    Applies Farina's method with asymmetric windowing to separate the linear
    impulse response from harmonic distortion products.

    Parameters
    ----------
    sig_src : np.ndarray
        Unused in this method (implied by sweep parameters), kept for API consistency.
    sig_dut : np.ndarray
        Recorded sweep response from DUT.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing frequency response, peak metrics, and IR preview.
    """
    F_START = 20.0
    F_END = 20000.0
    DURATION = 5.0

    # 1. Deconvolve
    ir, peak_idx = compute_impulse_response(sig_dut, fs, F_START, F_END, DURATION)

    # 2. Asymmetric Windowing (The "Farina Cut")
    # Pre-peak: Short (excludes harmonic pre-echoes)
    # Post-peak: Long (captures bass decay/room response)
    pre_window_ms = 2.0
    post_window_ms = 50.0

    pre_samples = int((pre_window_ms / 1000) * fs)
    post_samples = int((post_window_ms / 1000) * fs)

    start = max(0, peak_idx - pre_samples)
    end = min(len(ir), peak_idx + post_samples)

    ir_linear = ir[start:end]

    # Apply Tukey window to edges to prevent leakage
    win_len = len(ir_linear)
    window = spsig.windows.tukey(win_len, alpha=0.1)
    ir_windowed = ir_linear * window

    # 3. FFT
    freqs, mag_linear = dsp.compute_spectrum(ir_windowed, fs)

    # Filter valid band
    valid_mask = (freqs > F_START) & (freqs < F_END)
    f_axis = freqs[valid_mask]
    m_axis = mag_linear[valid_mask]

    # Normalize to 0dB
    if np.max(m_axis) > 0:
        gain_db = 20 * np.log10(m_axis / np.max(m_axis))
    else:
        gain_db = np.zeros_like(m_axis)

    # Smoothing
    win_smooth = 20
    gain_smooth = np.convolve(gain_db, np.ones(win_smooth) / win_smooth, mode="same")

    peak_db = np.max(gain_smooth)
    peak_freq = f_axis[np.argmax(gain_smooth)]

    # IR Time Axis (Relative to Peak)
    t_ir = (np.arange(len(ir_linear)) - pre_samples) / fs * 1000

    return {
        "freqs": f_axis,
        "gain_db": gain_smooth,
        "peak_db": float(peak_db),
        "peak_freq": float(peak_freq),
        "ir_preview": ir_linear,
        "ir_time_ms": t_ir,
    }
