import os

# Serial Settings
SERIAL_PORT = "/dev/tty.usbmodem101"
BAUD_RATE = 115200
TIMEOUT = 3  # seconds

# ADC / Hardware Params
ADC_BITS = 16
ADC_MAX_VAL = 65535
V_REF = 3.3
V_MID = 1.65  # Virtual ground / Bias voltage

# Acquisition Settings
FS_DEFAULT = 97793.1  # Hz
BURST_SAMPLES = 16384
LIVE_SAMPLES = 1024  # For streaming/scope views

# Data Locations
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CALIBRATION_FILE_PATH = os.path.join(DATA_DIR, "calibration.json")
DATA_DIR_CONTINUOUS = os.path.join(DATA_DIR, "continuous")
DATA_DIR_BURST = os.path.join(DATA_DIR, "burst")
