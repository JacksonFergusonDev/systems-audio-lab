import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, daq, viz

# Configuration
SHAPE = "sine"  # "sine", "triangle", "square", "saw"
FREQ_HZ = 440.0  # Frequency
AMPLITUDE = 0.5  # 0.0 to 1.0 (Watch your volume!)


def main():
    print(f"Initializing {SHAPE} wave at {FREQ_HZ}Hz...")

    # 1. Init Audio (auto_start=False means it waits)
    with audio.ContinuousOscillator(SHAPE, FREQ_HZ, AMPLITUDE, auto_start=False) as osc:
        # 2. Start Scope
        with daq.DAQInterface() as device:
            viz.run_live_scope(
                device.stream_generator(),
                title=f"Generator: {SHAPE.title()} @ {FREQ_HZ}Hz",
                on_launch=osc.play,
            )


if __name__ == "__main__":
    main()
