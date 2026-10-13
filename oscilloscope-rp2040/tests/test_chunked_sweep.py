import numpy as np
import pytest
import scipy.signal as spsig
from sysaudio import audio, chunked_sweep

FS = 97_800
F_START = 20.0
F_END = 20_000.0
DURATION = 5.0
CHUNK = 1024
PERIOD_S = 0.0139  # Wall-clock chunk period observed on the real DAQ
JITTER_S = 0.0015


def _stream_capture(signal: np.ndarray, seed: int = 0) -> np.ndarray:
    """Mimic stream mode: gap-free chunks separated by jittered dead time."""
    rng = np.random.default_rng(seed)
    period = PERIOD_S * FS
    starts = np.arange(0, len(signal) - CHUNK, period)
    starts = starts + rng.uniform(-1, 1, len(starts)) * JITTER_S * FS
    starts = np.clip(starts.astype(int), 0, len(signal) - CHUNK)
    return np.concatenate([signal[s : s + CHUNK] for s in starts])


@pytest.fixture(scope="module")
def sweep() -> np.ndarray:
    return audio.generate_log_sweep(F_START, F_END, DURATION, FS, 0.5).astype(
        np.float64
    )


@pytest.fixture(scope="module")
def src_result(sweep: np.ndarray) -> chunked_sweep.SweepHarmonics:
    return chunked_sweep.analyze_chunked_sweep(_stream_capture(sweep), FS)


def test_chunk_period_is_recovered(src_result: chunked_sweep.SweepHarmonics) -> None:
    assert src_result.chunk_period == pytest.approx(PERIOD_S, rel=0.01)


def test_clean_sweep_has_no_harmonics(
    src_result: chunked_sweep.SweepHarmonics,
) -> None:
    """The fit must not invent distortion on an ideal sweep."""
    dbc = 20 * np.log10(src_result.amplitudes[:, 1:] / src_result.amplitudes[:, :1])
    assert np.nanmax(dbc) < -60


def test_lowpass_magnitude_is_recovered(sweep: np.ndarray) -> None:
    sos = spsig.butter(1, 2000, "low", fs=FS, output="sos")
    dut = spsig.sosfilt(sos, sweep)

    result = chunked_sweep.compute_chunked_bode(
        _stream_capture(sweep, seed=1), _stream_capture(dut, seed=2), FS
    )

    _, h = spsig.sosfreqz(sos, worN=result["freqs"], fs=FS)
    expected_db = 20 * np.log10(np.abs(h))
    # Gain is reported relative to its peak, which sits at the lowest frequency.
    expected_db -= expected_db.max()

    valid = np.isfinite(result["gain_db"])
    assert valid.mean() > 0.95
    np.testing.assert_allclose(result["gain_db"][valid], expected_db[valid], atol=0.5)


def test_polynomial_distortion_is_recovered(sweep: np.ndarray) -> None:
    """A static y = x + a2*x^2 + a3*x^3 nonlinearity has analytic harmonics."""
    a2, a3 = 0.2, 0.1
    amp = np.max(np.abs(sweep))
    dut = sweep + a2 * sweep**2 + a3 * sweep**3

    result = chunked_sweep.compute_chunked_bode(
        _stream_capture(sweep, seed=3), _stream_capture(dut, seed=4), FS
    )

    fundamental = amp + 0.75 * a3 * amp**3
    h2_expected = 20 * np.log10(0.5 * a2 * amp**2 / fundamental)
    h3_expected = 20 * np.log10(0.25 * a3 * amp**3 / fundamental)

    band = (result["freqs"] > 200) & (result["freqs"] < 10_000)
    h2 = result["dut_harmonics_dbc"][band, 0]
    h3 = result["dut_harmonics_dbc"][band, 1]

    np.testing.assert_allclose(h2, h2_expected, atol=1.0)
    np.testing.assert_allclose(h3, h3_expected, atol=1.0)
