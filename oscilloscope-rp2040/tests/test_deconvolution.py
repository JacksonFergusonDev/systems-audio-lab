import numpy as np
import pytest
import scipy.signal as spsig
from sysaudio import audio, metrics

FS = 97_800
F_START = 20.0
F_END = 20_000.0
DURATION = 5.0
N_FFT = 1 << 16


@pytest.fixture(scope="module")
def sweep() -> np.ndarray:
    """Ideal log sweep matching the capture parameters."""
    return audio.generate_log_sweep(F_START, F_END, DURATION, FS, 1.0).astype(
        np.float64
    )


def _linear_response(sig: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """Deconvolve, window the linear IR, and return (freqs, magnitude, peak)."""
    ir, peak = metrics.compute_impulse_response(sig, FS, F_START, F_END, DURATION)
    segment = ir[peak - int(0.002 * FS) : peak + int(0.05 * FS)]
    mag = np.abs(np.fft.rfft(segment, N_FFT))
    freqs = np.fft.rfftfreq(N_FFT, 1 / FS)
    return freqs, mag, peak


def test_loopback_is_flat(sweep: np.ndarray) -> None:
    """A perfect wire must deconvolve to a flat magnitude response."""
    freqs, mag, _ = _linear_response(sweep)

    band = (freqs >= 40) & (freqs <= 15_000)
    gain_db = 20 * np.log10(mag[band] / np.median(mag[band]))

    assert np.max(np.abs(gain_db)) < 1.0


def test_known_lowpass_is_recovered(sweep: np.ndarray) -> None:
    """A 1st-order 1 kHz low-pass must show its analytic magnitude response."""
    sos = spsig.butter(1, 1000, "low", fs=FS, output="sos")
    freqs, mag_ref, _ = _linear_response(sweep)
    _, mag_dut, _ = _linear_response(spsig.sosfilt(sos, sweep))

    _, h = spsig.sosfreqz(sos, worN=freqs, fs=FS)
    for f_test in (100.0, 1000.0, 10_000.0):
        i = np.argmin(np.abs(freqs - f_test))
        measured_db = 20 * np.log10(mag_dut[i] / mag_ref[i])
        expected_db = 20 * np.log10(np.abs(h[i]))
        assert measured_db == pytest.approx(expected_db, abs=0.5)


def test_delay_shifts_peak(sweep: np.ndarray) -> None:
    """Pure latency must move the IR peak by exactly that many samples."""
    delay = 500
    _, _, peak_ref = _linear_response(sweep)
    _, _, peak_delayed = _linear_response(np.concatenate([np.zeros(delay), sweep]))

    assert peak_ref == len(sweep) - 1
    assert peak_delayed - peak_ref == delay
