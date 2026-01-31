import glob
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import numpy as np
import pandas as pd


def ensure_dir(directory: str) -> None:
    """Ensures that the specified directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)


def save_signal(
    signal: np.ndarray,
    fs: float,
    directory: str,
    prefix: str = "capture",
    **metadata: Any,
) -> str:
    """
    Saves signal, fs, and arbitrary metadata to a timestamped .npz file.

    Parameters
    ----------
    signal : np.ndarray
        The signal data array.
    fs : float
        Sampling frequency in Hz.
    directory : str
        Directory to save the file in.
    prefix : str, optional
        Prefix for the filename. Defaults to "capture".
    **metadata : Any
        Additional keyword arguments to be stored as metadata in the .npz file.

    Returns
    -------
    str
        The full path to the saved file.
    """
    ensure_dir(directory)

    # ISO 8601 Timestamp
    timestamp_str = datetime.now().isoformat()
    filename_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{prefix}_{filename_ts}.npz"
    path = os.path.join(directory, filename)

    # We combine core data with the optional metadata
    # 'utc_timestamp' is added automatically for provenance
    np.savez_compressed(path, signal=signal, fs=fs, timestamp=timestamp_str, **metadata)

    # Calculate size for user feedback
    size_mb = os.path.getsize(path) / (1024**2)
    print(f"💾 Saved {path} ({size_mb:.2f} MB)")
    print(f"   Metadata keys: {list(metadata.keys()) + ['timestamp']}")

    return path


def load_signal(filepath: Union[str, Path]) -> Tuple[np.ndarray, float]:
    """
    Robust loader for .npz files.

    Parameters
    ----------
    filepath : str
        Path to the .npz file.

    Returns
    -------
    Tuple[np.ndarray, float]
        (signal, fs) where signal is the data array and fs is the sampling rate.

    Raises
    ------
    SystemExit
        If the file is not found.
    KeyError
        If 'signal' or 'data' keys are missing in the archive.
    """
    try:
        with np.load(filepath) as archive:
            # Handle variable naming conventions from legacy versions
            if "signal" in archive:
                sig = archive["signal"]
            elif "data" in archive:
                sig = archive["data"]  # Handle stream.py legacy format
                # Flatten if it was a stacked array
                if sig.ndim > 1:
                    sig = sig.flatten()
            else:
                raise KeyError("No 'signal' or 'data' key found in archive.")

            # Load FS or default
            fs = float(archive["fs"]) if "fs" in archive else 97812.0

            return sig, fs
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        sys.exit(1)


def select_file_cli(directory: str) -> Optional[str]:
    """
    CLI menu to select a file from a directory.

    Parameters
    ----------
    directory : str
        The directory to list files from.

    Returns
    -------
    Optional[str]
        The full path of the selected file, or None if selection failed or canceled.
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return None

    files = sorted([f for f in os.listdir(directory) if f.endswith(".npz")])
    if not files:
        print("No recordings found.")
        return None

    print("\n--- RECORDINGS ---")
    for i, f in enumerate(files):
        print(f"[{i}] {f}")

    try:
        sel = int(input("Select ID: "))
        return os.path.join(directory, files[sel])
    except (ValueError, IndexError):
        return None


def scan_metadata(directory: str) -> pd.DataFrame:
    """
    Recursively scans a directory for .npz files and extracts their metadata.

    Parameters
    ----------
    directory : str
        Root directory to scan.

    Returns
    -------
    pd.DataFrame
        DataFrame containing metadata for all found files.
    """
    records = []
    # Walk through the data directory recursively
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            if not filename.endswith(".npz"):
                continue
            filepath = os.path.join(root, filename)
            try:
                with np.load(filepath) as archive:
                    # Start with the filename
                    row: dict[str, Any] = {"filename": filename}
                    # Loop through all keys in the file
                    for key in archive.files:
                        # Skip the heavy raw data
                        if key in ["signal", "data"]:
                            continue
                        # Extract the value
                        val = archive[key]
                        # Clean up NumPy types for display
                        if val.ndim == 0:
                            val = val.item()
                        elif isinstance(val, np.ndarray) and val.size == 1:
                            val = val.item()
                        # Format specific fields for readability
                        if key == "dominant_freq":
                            val = f"{val:.1f} Hz"
                        elif key == "peak_voltage":
                            val = f"{val:.3f} V"
                        elif key == "fs":
                            val = f"{val:.0f}"
                        row[key] = val
                    records.append(row)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return pd.DataFrame(records)


def load_latest_file(
    directory: str, pattern: str = "*.npz"
) -> Tuple[Optional[np.ndarray], Optional[float]]:
    """
    Finds and loads the most recent file matching a pattern.

    Parameters
    ----------
    directory : str
        Directory to search.
    pattern : str, optional
        Glob pattern for files. Defaults to "*.npz".

    Returns
    -------
    Tuple[Optional[np.ndarray], Optional[float]]
        (signal, fs) if found, else (None, None).
    """
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)
    if not files:
        return None, None

    latest_file = max(files, key=os.path.getmtime)
    print(f"📂 Loading: {os.path.basename(latest_file)}")
    return load_signal(latest_file)
