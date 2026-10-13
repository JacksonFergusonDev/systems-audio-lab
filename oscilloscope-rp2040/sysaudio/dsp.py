import numpy as np
import scipy.signal as spsig

from . import config


def raw_to_volts(raw_data: np.ndarray) -> np.ndarray:
    """
    Convert raw uint16 ADC values to float64 voltages.

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
    Subtract the mean (DC offset) from the signal.

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
    Stabilize a periodic waveform by aligning the first rising edge.

    Rolls the array to align the first rising edge crossing with index 0.

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


def compute_spectrum(signal: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the one-sided FFT magnitude spectrum using a Hann window.

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
    Find the frequency of the dominant peak within a specific band.

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


def _component_power(power: np.ndarray, df: float, f_target: float) -> float:
    """
    Noise-corrected energy of the spectral peak nearest `f_target`.

    Searches +/-3 bins for the peak, sums power over the Hann main lobe
    (+/-2 bins) so the result does not depend on where the tone falls between
    bins, and subtracts the local floor estimated 4-10 bins either side.
    """
    lobe, search, ring_lo, ring_hi = 2, 3, 4, 10
    k0 = round(f_target / df)
    lo, hi = max(k0 - search, 0), min(k0 + search + 1, len(power))
    if lo >= hi:
        return 0.0
    k = lo + int(np.argmax(power[lo:hi]))

    peak = power[max(k - lobe, 0) : k + lobe + 1]
    ring = np.concatenate(
        [
            power[max(k - ring_hi, 0) : max(k - ring_lo + 1, 0)],
            power[k + ring_lo : k + ring_hi + 1],
        ]
    )
    floor = float(np.mean(ring)) if ring.size else 0.0
    return max(0.0, float(np.sum(peak)) - floor * peak.size)


def harmonic_amplitudes(
    signal_arr: np.ndarray,
    fs: float,
    fundamental_freq: float,
    n_harmonics: int = 10,
) -> tuple[float, np.ndarray]:
    """
    Measure the fundamental and the amplitudes of its harmonics.

    The true fundamental is located within +/-10% of `fundamental_freq` (real
    tones drift from nominal, e.g. a sharp string or an uncalibrated sound
    card) and refined by parabolic interpolation. Each harmonic's energy is
    summed over its Hann main lobe with the local noise floor removed.

    Parameters
    ----------
    signal_arr : np.ndarray
        Time-domain signal array.
    fs : float
        Sampling rate in Hz.
    fundamental_freq : float
        Nominal fundamental frequency in Hz.
    n_harmonics : int, optional
        Number of harmonics to measure, including the fundamental.

    Returns
    -------
    Tuple[float, np.ndarray]
        (measured_fundamental_hz, amplitudes) where amplitudes is
        (n_harmonics,) relative to the fundamental (index 0 = 1.0). Harmonics
        above Nyquist are 0. Returns (0.0, zeros) if no fundamental is found.
    """
    freqs, mags = compute_spectrum(signal_arr, fs)
    df = freqs[1] - freqs[0]
    power = mags**2
    empty = (0.0, np.zeros(n_harmonics))

    band = (freqs > 0.9 * fundamental_freq) & (freqs < 1.1 * fundamental_freq)
    if not np.any(band):
        return empty
    k1 = int(np.flatnonzero(band)[np.argmax(mags[band])])
    if 0 < k1 < len(mags) - 1:
        a, b, c = np.log(mags[k1 - 1 : k1 + 2] + 1e-20)
        k1_frac = k1 + 0.5 * (a - c) / (a - 2 * b + c)
    else:
        k1_frac = float(k1)
    f1 = float(k1_frac * df)

    powers = np.array(
        [
            _component_power(power, df, h * f1) if h * f1 < freqs[-1] else 0.0
            for h in range(1, n_harmonics + 1)
        ]
    )
    if powers[0] <= 0:
        return empty

    return f1, np.sqrt(powers / powers[0])


def even_odd_energy_ratio(amplitudes: np.ndarray) -> float:
    """
    Ratio of even-order to odd-order harmonic energy (fundamental excluded).

    Parameters
    ----------
    amplitudes : np.ndarray
        Harmonic amplitudes, index 0 = fundamental (as from
        `harmonic_amplitudes`).

    Returns
    -------
    float
        sqrt(sum of H2, H4, ... squared) / sqrt(sum of H3, H5, ... squared).
        Above 1 means the even series carries more energy.
    """
    even = float(np.sum(amplitudes[1::2] ** 2))
    odd = float(np.sum(amplitudes[2::2] ** 2))
    return float(np.sqrt(even / odd)) if odd > 0 else float("inf")


def calculate_selective_thd(
    signal_arr: np.ndarray,
    fs: float,
    fundamental_freq: float = 82.4,
    n_harmonics: int = 10,
) -> float:
    """
    Calculate Total Harmonic Distortion (THD) from selective harmonics.

    Sums ONLY the energy at specific harmonic frequencies, ignoring the
    broad-band noise floor. See `harmonic_amplitudes` for how the fundamental
    and harmonics are measured.

    Parameters
    ----------
    signal_arr : np.ndarray
        Time-domain signal array.
    fs : float
        Sampling rate in Hz.
    fundamental_freq : float, optional
        Nominal fundamental frequency (e.g., 82.4 for low E).
    n_harmonics : int, optional
        Number of harmonics to include in the calculation.

    Returns
    -------
    float
        THD percentage (0.0 to 100.0+).
    """
    _, amps = harmonic_amplitudes(signal_arr, fs, fundamental_freq, n_harmonics)
    return float(100 * np.sqrt(np.sum(amps[1:] ** 2)))


def smart_align(sig_ref: np.ndarray, sig_target: np.ndarray) -> np.ndarray:
    """
    Align 'sig_target' to match the phase of 'sig_ref' using cross-correlation.

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
    return np.roll(sig_target, -lag)
