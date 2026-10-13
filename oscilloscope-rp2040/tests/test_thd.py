import numpy as np
import pytest
from sysaudio import dsp

FS = 97_800
N = 16_384
AMPS = {1: 1.0, 2: 0.21, 3: 0.24, 4: 0.18, 5: 0.06, 6: 0.12, 8: 0.09}
EXPECTED_PCT = 100 * np.sqrt(sum(a**2 for h, a in AMPS.items() if h > 1))


def _tone(f0: float) -> np.ndarray:
    t = np.arange(N) / FS
    rng = np.random.default_rng(0)
    sig = sum(a * np.sin(2 * np.pi * h * f0 * t + h) for h, a in AMPS.items())
    return sig + 1e-3 * rng.standard_normal(N)


@pytest.mark.parametrize("f_actual", [1000.0, 1003.0, 997.2])
def test_thd_tolerates_off_nominal_fundamental(f_actual: float) -> None:
    """Real tones drift from nominal (e.g. 1003 Hz); THD must not collapse."""
    thd = dsp.calculate_selective_thd(_tone(f_actual), FS, fundamental_freq=1000.0)
    assert thd == pytest.approx(EXPECTED_PCT, rel=0.03)


def test_thd_low_fundamental_off_nominal() -> None:
    """A slightly sharp low E (83.6 Hz vs 82.4 Hz nominal) at ~6 bins/cycle."""
    thd = dsp.calculate_selective_thd(_tone(83.6), FS, fundamental_freq=82.4)
    assert thd == pytest.approx(EXPECTED_PCT, rel=0.05)
