import numpy as np
import pytest
from sysaudio import diagnostics, dsp

FS = 97_685.1
N = 16_384


@pytest.mark.parametrize("amp", [1.0, 0.0961e-3])
def test_spectrum_reads_peak_amplitude(amp: float) -> None:
    """A bin-centred sine of amplitude A must read A, not A/2."""
    f = 200 * FS / N
    t = np.arange(N) / FS
    _, mags = dsp.compute_spectrum(amp * np.sin(2 * np.pi * f * t), FS)

    assert mags.max() == pytest.approx(amp, rel=1e-3)


def test_to_volts_converts_only_raw_counts() -> None:
    raw = np.array([0, 65535], dtype=np.uint16)
    volts = np.array([1.2, 2.3])

    np.testing.assert_allclose(dsp.to_volts(raw), [0.0, 3.3])
    assert dsp.to_volts(volts) is volts


def test_weak_signal_is_unhealthy_but_not_clipped() -> None:
    """The clean low-E capture case: 49 mVpp around the bias, far from the rails."""
    t = np.arange(N) / FS
    weak = 1.615 + 0.0245 * np.sin(2 * np.pi * 82.4 * t)

    assert not diagnostics.check_signal_health(weak)
    assert not diagnostics.detect_clipping(weak)


def test_rail_hit_is_clipped() -> None:
    sig = np.array([1.6, 3.29, 1.6, 0.4])
    assert diagnostics.detect_clipping(sig)


def test_peak_check_separates_low_e_harmonics() -> None:
    t = np.arange(N) / FS
    sig = np.sin(2 * np.pi * 82.4 * t) + 0.8 * np.sin(2 * np.pi * 164.8 * t)

    dominant, top = diagnostics.analyze_spectrum_peaks(sig, FS)

    assert dominant == pytest.approx(82.4, abs=FS / N)
    assert np.min(np.abs(top - 164.8)) < FS / N
