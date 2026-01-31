from typing import Tuple

import numpy as np
import scipy.signal as spsig

from . import config


def raw_to_volts(raw_data: np.ndarray) -> np.ndarray:
    """
    Converts raw uint16 ADC values to float64 voltages.

    Parameters
    ----------
    raw_data : np.ndarray
        Array of raw ADC integer values (0 to config.ADC_MAX_VAL).

    Returns
    -------
    np.ndarray
        Array of voltage values scaled to config.V_REF.
    """
    return (raw_data / config.ADC_MAX_VAL) * config.V_REF


def remove_dc(signal: np.ndarray) -> np.ndarray:
    """
    Subtracts the mean (DC offset) from the signal.

    Parameters
    ----------
    signal : np.ndarray
        Input signal array.

    Returns
    -------
    np.ndarray
        The signal centered around 0.0.
    """
    return signal - np.mean(signal)  # type: ignore[no-any-return]


def software_trigger(signal: np.ndarray, threshold: float = config.V_MID) -> np.ndarray:
    """
    Stabilizes a periodic waveform by rolling the array to align
    the first rising edge crossing with index 0.

    Parameters
    ----------
    signal : np.ndarray
        Input signal array.
    threshold : float, optional
        Voltage level to define the trigger crossing. Defaults to config.V_MID.

    Returns
    -------
    np.ndarray
        A cyclically shifted copy of the signal starting at the first rising edge.
        Returns the original signal if no crossing is found.
    """
    # Boolean mask: (Current < Thresh) AND (Next >= Thresh)
    crossings = np.where((signal[:-1] < threshold) & (signal[1:] >= threshold))[0]

    if crossings.size > 0:
        return np.roll(signal, -crossings[0])
    return signal


def compute_spectrum(signal: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes the one-sided FFT magnitude spectrum using a Hann window.

    Parameters
    ----------
    signal : np.ndarray
        (N,) Input time-domain signal.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    freq_axis : np.ndarray
        (N/2 + 1,) Array of frequency bins in Hz.
    fft_mag : np.ndarray
        (N/2 + 1,) Array of magnitude values (normalized).
    """
    n = signal.size
    # Apply window to reduce spectral leakage
    windowed = signal * spsig.windows.hann(n)

    # FFT
    fft_complex = np.fft.rfft(windowed)
    fft_mag = (2.0 / n) * np.abs(fft_complex)

    # Frequency axis
    freq_axis = np.fft.rfftfreq(n, d=1.0 / fs)

    return freq_axis, fft_mag


def estimate_fundamental(
    freqs: np.ndarray, mags: np.ndarray, fmin: float = 20.0, fmax: float = 2000.0
) -> float:
    """
    Finds the frequency of the dominant peak within a specific band.

    Parameters
    ----------
    freqs : np.ndarray
        Array of frequency bins.
    mags : np.ndarray
        Array of magnitudes corresponding to freqs.
    fmin : float, optional
        Minimum frequency to consider. Defaults to 20.0.
    fmax : float, optional
        Maximum frequency to consider. Defaults to 2000.0.

    Returns
    -------
    float
        The frequency in Hz of the largest peak within [fmin, fmax].
        Returns 0.0 if no peak is found or arrays are empty.
    """
    if freqs.size == 0:
        return 0.0

    mask = (freqs >= fmin) & (freqs <= fmax)
    if not np.any(mask):
        return 0.0

    f_subset = freqs[mask]
    m_subset = mags[mask]

    # Simple peak finding
    idx = np.argmax(m_subset)
    return float(f_subset[idx])


def calculate_selective_thd(
    signal_arr: np.ndarray,
    fs: float,
    fundamental_freq: float = 82.4,
    n_harmonics: int = 10,
) -> float:
    """
    Calculates Total Harmonic Distortion (THD) by summing ONLY the energy
    at specific harmonic frequencies, ignoring the broad-band noise floor.

    Parameters
    ----------
    signal_arr : np.ndarray
        Time-domain signal array.
    fs : float
        Sampling rate in Hz.
    fundamental_freq : float, optional
        The fundamental frequency of the signal (e.g., 82.4 for low E).
    n_harmonics : int, optional
        Number of harmonics to include in the calculation.

    Returns
    -------
    float
        THD percentage (0.0 to 100.0+).
    """
    # Use internal compute_spectrum function
    freqs, mags = compute_spectrum(signal_arr, fs)

    # 1. Get Fundamental Magnitude
    window = 5  # Narrow window to exclude nearby noise
    fund_mask = (freqs > fundamental_freq - window) & (
        freqs < fundamental_freq + window
    )

    if not np.any(fund_mask):
        return 0.0

    fund_mag = np.max(mags[fund_mask])

    # 2. Sum ONLY the Harmonic Peaks (Selective)
    harmonic_sum_sq = 0.0

    for i in range(2, n_harmonics + 1):
        target_f = fundamental_freq * i

        # Look for a peak at exactly this frequency
        mask = (freqs > target_f - window) & (freqs < target_f + window)

        if np.any(mask):
            # We subtract the estimated noise floor from the peak to be extra safe
            # Estimate local noise by looking just outside the window
            noise_mask = (
                (freqs > target_f - window * 3)
                & (freqs < target_f + window * 3)
                & (~mask)
            )
            local_noise = np.mean(mags[noise_mask]) if np.any(noise_mask) else 0

            # Get peak and subtract noise (soft floor at 0)
            h_mag = max(0.0, np.max(mags[mask]) - local_noise)

            if h_mag > 0:
                harmonic_sum_sq += h_mag**2

    # 3. Calculate Selective THD
    thd_pct = (np.sqrt(harmonic_sum_sq) / fund_mag) * 100
    return float(thd_pct)


def smart_align(sig_ref: np.ndarray, sig_target: np.ndarray) -> np.ndarray:
    """
    Aligns 'sig_target' to match the phase of 'sig_ref' using Cross-Correlation.

    Parameters
    ----------
    sig_ref : np.ndarray
        The reference signal (stationary).
    sig_target : np.ndarray
        The signal to be shifted.

    Returns
    -------
    np.ndarray
        The shifted version of sig_target that aligns best with sig_ref.
    """
    # 1. Compute Cross-Correlation
    correlation = spsig.correlate(sig_target, sig_ref, mode="full")
    lags = spsig.correlation_lags(sig_target.size, sig_ref.size, mode="full")

    # 2. Find the lag that maximizes correlation
    lag = lags[np.argmax(correlation)]

    # 3. Shift the target signal
    if lag > 0:
        # Target is ahead, roll it back
        aligned = np.roll(sig_target, -lag)
    else:
        # Target is behind, roll it forward
        aligned = np.roll(sig_target, -lag)

    return aligned
