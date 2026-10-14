from pathlib import Path

import numpy as np
import pytest
from sysaudio import config, io

STORED_FS = 97_859.6


@pytest.fixture
def capture(tmp_path: Path) -> str:
    return io.save_signal(
        np.arange(8, dtype=np.uint16), STORED_FS, str(tmp_path), prefix="t", note="x"
    )


def test_load_defaults_to_measured_rate(capture: str) -> None:
    sig, fs = io.load_signal(capture)

    np.testing.assert_array_equal(sig, np.arange(8))
    assert sig.dtype == np.uint16
    assert fs == config.FS_DEFAULT


def test_load_rate_precedence(capture: str) -> None:
    assert io.load_signal(capture, use_stored_fs=True)[1] == STORED_FS
    assert io.load_signal(capture, 50_000.0, use_stored_fs=True)[1] == 50_000.0


def test_load_legacy_data_key(tmp_path: Path) -> None:
    path = tmp_path / "legacy.npz"
    np.savez(path, data=np.ones((2, 3)))

    sig, fs = io.load_signal(path)

    assert sig.shape == (6,)
    assert fs == config.FS_DEFAULT


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        io.load_signal(tmp_path / "missing.npz")


def test_scan_metadata_skips_signal(capture: str, tmp_path: Path) -> None:
    df = io.scan_metadata(str(tmp_path))

    assert list(df["note"]) == ["x"]
    assert "signal" not in df.columns
