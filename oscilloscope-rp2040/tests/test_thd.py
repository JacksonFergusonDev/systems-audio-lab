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
    """THD must not depend on where the tone falls relative to FFT bins."""
    thd = dsp.calculate_selective_thd(_tone(f_actual), FS, fundamental_freq=1000.0)
    assert thd == pytest.approx(EXPECTED_PCT, rel=0.03)


def test_thd_low_fundamental_off_nominal() -> None:
    """A low fundamental, off nominal, spanning only ~14 FFT bins."""
    thd = dsp.calculate_selective_thd(_tone(83.6), FS, fundamental_freq=82.4)
    assert thd == pytest.approx(EXPECTED_PCT, rel=0.05)


def test_harmonic_amplitudes_recovers_each_harmonic() -> None:
    f1, amps = dsp.harmonic_amplitudes(_tone(1003.0), FS, 1000.0, n_harmonics=8)

    assert f1 == pytest.approx(1003.0, abs=0.5)
    expected = np.array([AMPS.get(h, 0.0) for h in range(1, 9)])
    np.testing.assert_allclose(amps, expected, atol=0.01)


def test_even_odd_energy_ratio() -> None:
    amps = np.array([1.0, 0.3, 0.1, 0.4, 0.0])
    assert dsp.even_odd_energy_ratio(amps) == pytest.approx(5.0)
