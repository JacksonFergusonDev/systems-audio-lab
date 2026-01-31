"""
Simple script to capture a single burst of data from the DAQ.

This script connects to the RP2040, triggers a standard burst capture
(defined in config), converts the raw ADC values to voltages, and saves
the result to the burst data directory.
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sysaudio import config, daq, dsp, io  # noqa: E402


def main() -> None:
    """
    Main execution entry point.

    Connects to the DAQ, captures a single burst of samples,
    converts them to voltages, and saves the file to disk.
    """
    print("Initializing Burst Capture...")

    try:
        with daq.DAQInterface() as device:
            print("Requesting capture...")
            raw_data = device.capture_burst()

            # Scale raw ADC values to voltages
            voltages = dsp.raw_to_volts(raw_data)

            # Save to disk
            io.save_signal(
                voltages, config.FS_DEFAULT, config.DATA_DIR_BURST, prefix="burst"
            )

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
