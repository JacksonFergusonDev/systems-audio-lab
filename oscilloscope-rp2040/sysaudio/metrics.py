from typing import Any

import numpy as np
import pandas as pd
import scipy.signal as spsig

from . import dsp


def calculate_gain_metrics(
    sig_clean: np.ndarray, sig_dirty: np.ndarray, duration_ms: float, fs: float
) -> dict[str, Any]:
    """
    Compute Vpp gain and identify the peak gain region.

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
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute frequency spectrum data as a wrapper around dsp.compute_spectrum.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (freq_axis, magnitude)
    """
    return dsp.compute_spectrum(dsp.remove_dc(signal), fs)


def prepare_transfer_curve(
    sig_src: np.ndarray, sig_dut: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Normalize and phase-align signals for XY transfer curve plotting.

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
) -> pd.DataFrame | None:
    """
    Extract magnitude relative to fundamental for the first N harmonics.

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
) -> dict[str, np.ndarray]:
    """
    Compute spectra for two signals, normalized to Peak=1.0.

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
) -> pd.DataFrame | None:
    """
    Generate a comparative DataFrame of harmonic magnitudes for two signals.

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
    Generate the Inverse Filter for a Logarithmic Sine Sweep (Farina 2000).

    This filter corrects the -3dB/octave slope of the log sweep (Pink Noise profile)
    to a flat White Noise profile during deconvolution.

    ESS deconvolution requires a phase-continuous capture of the whole sweep.
    Stream-mode DAQ captures have gaps between chunks and are not suitable; use
    `chunked_sweep` for those.

    Returns
    -------
    np.ndarray
        The time-reversed, amplitude-weighted inverse sweep.
    """
    n = round(duration * fs)
    t = np.arange(n, dtype=np.float64) / fs

    # 1. Regenerate the ideal sweep
    r = (f_end / f_start) ** (1.0 / duration)
    b = 2.0 * np.pi * f_start / np.log(r)
    phase = b * (r**t - 1.0)
    sweep = np.sin(phase)

    # 2. Generate Amplitude Envelope (+6 dB/octave before reversal)
    # Instantaneous frequency is f_start * r**t, so weighting by r**t (i.e. f)
    # cancels the 1/f power spectrum shared by the sweep and its reversal.
    w = r**t

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
) -> tuple[np.ndarray, int]:
    """
    Perform deconvolution to extract the Linear Impulse Response (IR).

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
