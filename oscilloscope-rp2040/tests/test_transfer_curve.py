import numpy as np
from sysaudio import metrics


def test_transfer_curve_removes_bias_and_aligns() -> None:
    """Biased, delayed captures must yield a centred, phase-aligned XY curve."""
    fs, f0, delay = 97_800, 100.0, 37
    t = np.arange(16_384) / fs
    src = 0.4 * np.sin(2 * np.pi * f0 * t)
    dut = np.tanh(3 * src)

    # Mimic raw captures: both sit on the 1.65 V bias, DUT lags by `delay`.
    src_raw = 1.65 + src
    dut_raw = 1.65 + np.concatenate([np.zeros(delay), dut[:-delay]])

    x, y = metrics.prepare_transfer_curve(src_raw, dut_raw)

    assert len(x) == len(y)
    assert np.min(x) < -0.9
    assert np.max(x) > 0.9
    # Aligned and memoryless: the XY points must trace the known curve.
    expected = np.tanh(1.2 * x) / np.tanh(1.2)
    assert np.max(np.abs(y - expected)) < 0.05
