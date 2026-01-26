import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import daq, dsp, io, config


def main():
    print("Initializing Burst Capture...")

    try:
        with daq.DAQInterface() as device:
            print("Requesting capture...")
            raw_data = device.capture_burst()

            # Convert to Volts
            voltages = dsp.raw_to_volts(raw_data)

            # Save
            io.save_signal(
                voltages, config.FS_DEFAULT, config.DATA_DIR_BURST, prefix="burst"
            )

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
