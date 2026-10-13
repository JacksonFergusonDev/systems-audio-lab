"""
Configuration constants for the Oscilloscope RP2040 interface.

This module acts as the central source of truth for hardware parameters,
serial connection settings, and file path definitions.
"""

import os

# Serial Settings
SERIAL_PORT: str = "/dev/tty.usbmodem101"
BAUD_RATE: int = 115200
TIMEOUT: float = 3.0  # seconds

# ADC / Hardware Params
ADC_BITS: int = 16
ADC_MAX_VAL: int = 65535
V_REF: float = 3.3
V_MID: float = 1.65  # Virtual ground / Bias voltage

# Acquisition Settings
# Measured against crystal-referenced sound-card tones (1 kHz sine, 100 Hz
# triangle), +/-0.01%; derived in Notebook 02, Section 5. Per-file `fs` values
# record what was assumed at capture time (97793.1 / 97859.6 Hz).
FS_DEFAULT: float = 97685.1  # Hz
BURST_SAMPLES: int = 16384
LIVE_SAMPLES: int = 1024  # For streaming/scope views

# Data Locations
PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")
CALIBRATION_FILE_PATH: str = os.path.join(DATA_DIR, "calibration.json")
DATA_DIR_CONTINUOUS: str = os.path.join(DATA_DIR, "continuous")
DATA_DIR_BURST: str = os.path.join(DATA_DIR, "burst")
