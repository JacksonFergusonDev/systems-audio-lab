import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd


def ensure_dir(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


def save_signal(
    signal: np.ndarray, fs: float, directory: str, prefix: str = "capture", **metadata
):
    """
    Saves signal, fs, and ANY extra metadata to a timestamped .npz file.

    Usage:
        save_signal(sig, fs, dir, v_ref=3.3, gain=1, notes="Bridge pickup")
    """
    ensure_dir(directory)

    # ISO 8601 Timestamp (The gold standard)
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


def load_signal(filepath: str):
    """
    Robust loader for .npz files.
    Returns: (signal, fs)
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


def select_file_cli(directory: str) -> str:
    """CLI menu to select a file from a directory."""
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
    Recursively scans a directory for .npz files and extracts their metadata
    into a Pandas DataFrame.
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
                    row = {"filename": filename}
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
