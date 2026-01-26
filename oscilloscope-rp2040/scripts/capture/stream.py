import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import daq, io, config


def record_stream():
    frames = []
    start_time = time.time()

    # Calculate approx data rate for user info
    bytes_per_sec = config.LIVE_SAMPLES * 2 * (config.FS_DEFAULT / config.LIVE_SAMPLES)
    mb_per_min = (bytes_per_sec * 60) / (1024 * 1024)

    print("🔴 RECORDING STREAM... Press Ctrl+C to stop.")
    print(f"   (Approx Data Rate: ~{mb_per_min:.2f} MB/min)")

    try:
        with daq.DAQInterface() as device:
            # We iterate over the generator. It yields chunks indefinitely.
            for chunk_u16 in device.stream_generator():
                frames.append(chunk_u16)

                # Feedback every 100 frames
                if len(frames) % 100 == 0:
                    duration = time.time() - start_time
                    print(f"   Captured {len(frames)} frames ({duration:.1f}s)...")

    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

    if not frames:
        print("No data captured.")
        return

    print("Processing...")
    # Stack and flatten to create a single continuous timeline
    full_array = np.concatenate(frames)

    # We save as raw uint16 to preserve space
    # The io module handles the saving
    io.save_signal(
        full_array, config.FS_DEFAULT, config.DATA_DIR_CONTINUOUS, prefix="session"
    )


if __name__ == "__main__":
    record_stream()
