"""
Frequency response and harmonic analysis of log sweeps captured in stream mode.

Stream-mode captures are 1024-sample chunks separated by untimed USB dead time
(roughly 25% of wall-clock time is lost). Phase is not continuous across chunk
boundaries, so whole-signal methods like ESS deconvolution do not apply.

Each chunk, however, is gap-free and short enough that the sweep is
quasi-stationary within it. This module:

1. Recovers each chunk's position in the sweep by fitting a constant chunk
   period to the per-chunk dominant frequency.
2. Fits the exact log-sweep phase model (fundamental + harmonics) to each chunk
   by linear least squares.
3. Resamples the per-chunk amplitudes onto a common log-frequency grid so that
   source and DUT captures can be compared.
"""

from dataclasses import dataclass

import numpy as np

from . import config


@dataclass(frozen=True)
class SweepHarmonics:
    """
    Per-chunk harmonic amplitudes extracted from a chunked log sweep.

    Attributes
    ----------
    freqs : np.ndarray
        (M,) fundamental frequency at each valid chunk centre in Hz.
    amplitudes : np.ndarray
        (M, K) peak amplitude of harmonics 1..K in input units. NaN where the
        harmonic would exceed the analysis bandwidth.
    residual_rms : np.ndarray
        (M,) RMS of what the harmonic model failed to explain (noise + higher
        harmonics), in input units.
    chunk_period : float
        Fitted wall-clock time between chunk starts in seconds.
    """

    freqs: np.ndarray
    amplitudes: np.ndarray
    residual_rms: np.ndarray
    chunk_period: float


def _sweep_rate(f_start: float, f_end: float, duration: float) -> float:
    """Return the natural log of the per-second frequency ratio of the sweep."""
    return float(np.log(f_end / f_start) / duration)


def _peak_frequencies(
    chunks: np.ndarray, fs: float, n_fft: int = 1 << 15
) -> np.ndarray:
    """
    Estimate the dominant frequency of each chunk.

    Uses a Hann-windowed, zero-padded FFT with parabolic interpolation on the
    log magnitude around the peak bin.
    """
    n = chunks.shape[1]
    spec = np.abs(np.fft.rfft(chunks * np.hanning(n), n_fft, axis=1))
    k = np.clip(spec.argmax(axis=1), 1, spec.shape[1] - 2)
    rows = np.arange(len(k))

    a = np.log(spec[rows, k - 1] + 1e-12)
    b = np.log(spec[rows, k] + 1e-12)
    c = np.log(spec[rows, k + 1] + 1e-12)
    offset = 0.5 * (a - c) / (a - 2 * b + c)

    return (k + offset) * fs / n_fft  # type: ignore[no-any-return]


def estimate_chunk_frequencies(
    chunks: np.ndarray,
    fs: float,
    f_start: float,
    f_end: float,
    duration: float,
    fit_band: tuple[float, float] = (300.0, 15000.0),
) -> tuple[np.ndarray, float]:
    """
    Estimate the sweep frequency at the centre of every chunk.

    Chunks in `fit_band` with healthy signal level are used to robustly fit
    ``t_k = t0 + k * period``, where ``t_k`` is the sweep time implied by each
    chunk's measured frequency. The fit extrapolates to chunks where a direct
    estimate is unreliable (low frequencies, where a chunk holds few cycles).

    Parameters
    ----------
    chunks : np.ndarray
        (N, chunk_size) DC-removed chunks.
    fs : float
        Sampling rate in Hz.
    f_start, f_end, duration : float
        Parameters of the played log sweep.
    fit_band : tuple of float, optional
        Frequency band whose chunks anchor the timing fit.

    Returns
    -------
    Tuple[np.ndarray, float]
        (frequencies, chunk_period) where frequencies is (N,) in Hz.

    Raises
    ------
    ValueError
        If too few chunks fall in `fit_band` to fit the timing model.
    """
    lnr = _sweep_rate(f_start, f_end, duration)
    measured = _peak_frequencies(chunks, fs)
    idx = np.arange(len(chunks))
    t_implied = np.log(np.maximum(measured, 1e-6) / f_start) / lnr

    rms = chunks.std(axis=1)
    candidates = (
        (measured > fit_band[0])
        & (measured < fit_band[1])
        & (rms > 0.3 * np.median(rms))
    )
    if candidates.sum() < 10:
        raise ValueError("Too few chunks inside fit_band to recover sweep timing.")

    # Iteratively reweighted line fit; rejects chunks with misidentified peaks.
    inliers = candidates.copy()
    for _ in range(5):
        coeffs = np.polyfit(idx[inliers], t_implied[inliers], 1)
        resid = t_implied - np.polyval(coeffs, idx)
        spread = 1.5 * np.median(np.abs(resid[inliers]))
        inliers = candidates & (np.abs(resid) < max(3 * spread, 1e-4))

    predicted = f_start * np.exp(lnr * np.polyval(coeffs, idx))

    # Above fit_band[0] a chunk holds enough cycles that its own estimate beats
    # the timing model, which carries per-chunk USB jitter.
    trust_measured = (predicted > fit_band[0]) & (
        np.abs(measured / predicted - 1) < 0.05
    )
    freqs = np.where(trust_measured, measured, predicted)

    return freqs, float(coeffs[0])


def _sweep_basis(n: int, fs: float, f_centre: float, lnr: float, k: int) -> np.ndarray:
    """Build the [DC, cos(phi), sin(phi), ..., cos(k*phi), sin(k*phi)] matrix."""
    tau = (np.arange(n) - (n - 1) / 2) / fs
    phase = 2 * np.pi * f_centre * np.expm1(lnr * tau) / lnr
    cols = [np.ones(n)]
    for h in range(1, k + 1):
        cols += [np.cos(h * phase), np.sin(h * phase)]
    return np.stack(cols, axis=1)


def fit_chunk_harmonics(
    chunk: np.ndarray,
    fs: float,
    f_centre: float,
    lnr: float,
    n_harmonics: int,
    search: float = 0.03,
    n_search: int = 61,
) -> tuple[np.ndarray, float, float]:
    """
    Fit the log-sweep harmonic model to a single gap-free chunk.

    The centre frequency is first refined by minimising the fundamental-only
    residual over ``f_centre * (1 +/- search)``, then all harmonics are fitted
    jointly.

    Parameters
    ----------
    chunk : np.ndarray
        (n,) samples of one chunk.
    fs : float
        Sampling rate in Hz.
    f_centre : float
        Initial estimate of the fundamental at the chunk centre in Hz.
    lnr : float
        Natural log of the sweep's per-second frequency ratio.
    n_harmonics : int
        Number of harmonics (including the fundamental) to fit.
    search : float, optional
        Fractional half-width of the frequency refinement search.
    n_search : int, optional
        Number of candidate frequencies in the refinement search.

    Returns
    -------
    Tuple[np.ndarray, float, float]
        (amplitudes, refined_f_centre, residual_rms).
    """
    n = len(chunk)
    # Minimise residual rather than maximise amplitude: with only a few cycles
    # per chunk the basis is far from orthogonal, and the fitted amplitude can
    # inflate at the wrong frequency.
    best_f, best_ssr = f_centre, np.inf
    for f in f_centre * np.linspace(1 - search, 1 + search, n_search):
        _, ssr, *_ = np.linalg.lstsq(_sweep_basis(n, fs, f, lnr, 1), chunk, rcond=None)
        if ssr[0] < best_ssr:
            best_f, best_ssr = float(f), float(ssr[0])

    basis = _sweep_basis(n, fs, best_f, lnr, n_harmonics)
    coeffs, *_ = np.linalg.lstsq(basis, chunk, rcond=None)
    amps = np.hypot(coeffs[1::2], coeffs[2::2])
    resid = float(np.std(chunk - basis @ coeffs))

    return amps, best_f, resid


def analyze_chunked_sweep(
    signal: np.ndarray,
    fs: float,
    f_start: float = 20.0,
    f_end: float = 20000.0,
    duration: float = 5.0,
    chunk_size: int = config.LIVE_SAMPLES,
    n_harmonics: int = 5,
    max_harmonic_freq: float | None = None,
) -> SweepHarmonics:
    """
    Extract fundamental and harmonic amplitudes from a stream-mode sweep.

    Parameters
    ----------
    signal : np.ndarray
        Concatenated stream-mode capture (raw ADC counts or volts).
    fs : float
        Sampling rate in Hz.
    f_start, f_end, duration : float, optional
        Parameters of the played log sweep.
    chunk_size : int, optional
        Samples per gap-free chunk (the firmware's stream block size).
    n_harmonics : int, optional
        Number of harmonics (including the fundamental) to report.
    max_harmonic_freq : float, optional
        Harmonics above this frequency are not fitted. Defaults to 0.4 * fs.

    Returns
    -------
    SweepHarmonics
        Per-chunk results for chunks that hold at least one full cycle and lie
        inside the swept band.
    """
    if max_harmonic_freq is None:
        max_harmonic_freq = 0.4 * fs

    n_chunks = len(signal) // chunk_size
    chunks = signal[: n_chunks * chunk_size].astype(np.float64)
    chunks = chunks.reshape(n_chunks, chunk_size)
    chunks -= chunks.mean(axis=1, keepdims=True)

    lnr = _sweep_rate(f_start, f_end, duration)
    f_est, period = estimate_chunk_frequencies(chunks, fs, f_start, f_end, duration)

    freqs, amps, resids = [], [], []
    for chunk, f0 in zip(chunks, f_est, strict=True):
        # Below one cycle per chunk the fit is ill-conditioned against DC.
        if f0 < fs / chunk_size or f0 > f_end:
            continue
        k = int(np.clip(max_harmonic_freq // f0, 1, n_harmonics))
        a, f_ref, resid = fit_chunk_harmonics(chunk, fs, f0, lnr, k)
        freqs.append(f_ref)
        amps.append(np.pad(a, (0, n_harmonics - k), constant_values=np.nan))
        resids.append(resid)

    order = np.argsort(freqs)
    return SweepHarmonics(
        freqs=np.asarray(freqs)[order],
        amplitudes=np.asarray(amps)[order],
        residual_rms=np.asarray(resids)[order],
        chunk_period=period,
    )


def _resample_log(
    freqs: np.ndarray, values: np.ndarray, grid: np.ndarray, smooth: int
) -> np.ndarray:
    """Median-smooth `values` over `smooth` chunks, then interpolate in log-f."""
    valid = np.isfinite(values)
    f, v = freqs[valid], values[valid]
    if len(v) < 2:
        return np.full_like(grid, np.nan)

    half = smooth // 2
    v_smooth = np.array(
        [np.median(v[max(0, i - half) : i + half + 1]) for i in range(len(v))]
    )
    return np.interp(np.log(grid), np.log(f), v_smooth, left=np.nan, right=np.nan)  # type: ignore[no-any-return]


def compute_chunked_bode(
    sig_src: np.ndarray,
    sig_dut: np.ndarray,
    fs: float,
    f_start: float = 20.0,
    f_end: float = 20000.0,
    duration: float = 5.0,
    n_harmonics: int = 5,
    n_points: int = 200,
    smooth: int = 5,
) -> dict[str, np.ndarray]:
    """
    Compare source and DUT stream-mode sweeps on a common frequency grid.

    The DUT/source ratio of fundamental amplitudes cancels the response of the
    playback chain and the DAQ front end, leaving the DUT's own response.

    Parameters
    ----------
    sig_src : np.ndarray
        Sweep captured directly from the playback source (loopback).
    sig_dut : np.ndarray
        Sweep captured at the DUT output.
    fs : float
        Sampling rate in Hz.
    f_start, f_end, duration : float, optional
        Parameters of the played log sweep.
    n_harmonics : int, optional
        Number of harmonics (including the fundamental) to analyse.
    n_points : int, optional
        Number of log-spaced output frequencies.
    smooth : int, optional
        Running-median length (in chunks) applied before resampling.

    Returns
    -------
    Dict[str, np.ndarray]
        ``freqs`` (n_points,); ``gain_db`` (n_points,) normalised to 0 dB peak;
        ``dut_harmonics_dbc`` and ``src_harmonics_dbc`` (n_points, n_harmonics - 1)
        giving harmonics 2..K relative to each capture's own fundamental.
    """
    src = analyze_chunked_sweep(
        sig_src, fs, f_start, f_end, duration, n_harmonics=n_harmonics
    )
    dut = analyze_chunked_sweep(
        sig_dut, fs, f_start, f_end, duration, n_harmonics=n_harmonics
    )

    lo = max(src.freqs[0], dut.freqs[0])
    hi = min(src.freqs[-1], dut.freqs[-1])
    grid = np.geomspace(lo, hi, n_points)

    def dbc(result: SweepHarmonics) -> np.ndarray:
        rel = 20 * np.log10(result.amplitudes[:, 1:] / result.amplitudes[:, :1])
        return np.stack(
            [_resample_log(result.freqs, col, grid, smooth) for col in rel.T], axis=1
        )

    fund_src = _resample_log(src.freqs, src.amplitudes[:, 0], grid, smooth)
    fund_dut = _resample_log(dut.freqs, dut.amplitudes[:, 0], grid, smooth)
    gain_db = 20 * np.log10(fund_dut / fund_src)

    return {
        "freqs": grid,
        "gain_db": gain_db - np.nanmax(gain_db),
        "dut_harmonics_dbc": dbc(dut),
        "src_harmonics_dbc": dbc(src),
    }
