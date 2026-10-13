import numpy as np
import pytest
from sysaudio import calibration, dsp

N = 16_384


def _tone(f: float, fs: float, noise: float = 1e-3, harmonics: int = 1) -> np.ndarray:
    t = np.arange(N) / fs
    rng = np.random.default_rng(1)
    sig = sum(
        0.5 / h * np.sin(2 * np.pi * h * f * t + h) for h in range(1, harmonics + 1)
    )
    return 1.65 + sig + noise * rng.standard_normal(N)


@pytest.mark.parametrize("f_true", [1000.0, 1001.1245, 100.1067])
def test_tone_frequency_resolves_far_below_one_bin(f_true: float) -> None:
    """Bins are ~6 Hz wide; a clean tone must be located to ~1 mHz."""
    f_hat, std = dsp.estimate_tone_frequency(_tone(f_true, 97_793.1), 97_793.1, f_true)
    assert f_hat == pytest.approx(f_true, abs=0.002)
    assert std < 0.002


def test_tone_frequency_with_harmonics() -> None:
    f_hat, _ = dsp.estimate_tone_frequency(
        _tone(1000.3, 97_793.1, harmonics=5), 97_793.1, 1000.0, n_harmonics=5
    )
    assert f_hat == pytest.approx(1000.3, abs=0.002)


def test_fs_from_reference_tone_recovers_true_rate() -> None:
    """Captured at the true rate but analysed with a 0.11% high assumption."""
    fs_true, fs_assumed = 97_686.0, 97_793.1
    capture = _tone(1000.0, fs_true)

    fs_hat, std = calibration.fs_from_reference_tone(capture, fs_assumed, 1000.0)

    assert fs_hat == pytest.approx(fs_true, abs=1.0)
    assert std < 1.0
