import numpy as np
import scipy.signal as spsig

from . import config


def raw_to_volts(raw_data: np.ndarray) -> np.ndarray:
    """Converts raw uint16 ADC values to float64 voltages."""
    return (raw_data / config.ADC_MAX_VAL) * config.V_REF


def remove_dc(signal: np.ndarray) -> np.ndarray:
    """Subtracts the mean (DC offset) from the signal."""
    return signal - np.mean(signal)


def software_trigger(signal: np.ndarray, threshold: float = config.V_MID) -> np.ndarray:
    """
    Stabilizes a periodic waveform by rolling the array to align
    the first rising edge crossing with index 0.
    """
    # Boolean mask: (Current < Thresh) AND (Next >= Thresh)
    crossings = np.where((signal[:-1] < threshold) & (signal[1:] >= threshold))[0]

    if crossings.size > 0:
        return np.roll(signal, -crossings[0])
    return signal


def compute_spectrum(signal: np.ndarray, fs: float):
    """
    Computes the one-sided FFT magnitude spectrum.
    Returns: (freq_axis, magnitude)
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


def estimate_fundamental(freqs, mags, fmin=20.0, fmax=2000.0) -> float:
    """Finds the frequency of the dominant peak within a band."""
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


def calculate_selective_thd(signal_arr, fs, fundamental_freq=82.4, n_harmonics=10):
    """
    Calculates THD by summing ONLY the energy at specific harmonic frequencies,
    ignoring the broad-band noise floor.
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
    harmonic_sum_sq = 0

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
            h_mag = max(0, np.max(mags[mask]) - local_noise)

            if h_mag > 0:
                harmonic_sum_sq += h_mag**2

    # 3. Calculate Selective THD
    thd_pct = (np.sqrt(harmonic_sum_sq) / fund_mag) * 100
    return thd_pct


def smart_align(sig_ref, sig_target):
    """
    Aligns 'sig_target' to match the phase of 'sig_ref' using Cross-Correlation.
    Returns the shifted target signal.
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
