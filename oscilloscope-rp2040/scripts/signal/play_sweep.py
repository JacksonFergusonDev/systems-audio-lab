"""
Script to play a logarithmic sine sweep and visualize it in real-time.

This script generates a log sine sweep audio buffer, plays it through the system
output, and simultaneously streams data from the DAQ to a live oscilloscope
window. This allows for visual verification of the transfer function measurement
setup before committing to a recording.
"""

import sounddevice as sd
from sysaudio import audio, daq, viz

# Configuration
F_START: float = 20.0  # Start Frequency (Hz)
F_END: float = 20000.0  # End Frequency (Hz)
DURATION: float = 5.0  # Seconds
AMPLITUDE: float = 0.5  # 0.0 to 1.0


def main() -> None:
    """
    Main execution entry point.

    Generates the sweep buffer, establishes the DAQ connection, and launches
    the live visualization. The audio playback is triggered via a callback
    once the visualization window is fully initialized to ensure synchronization.
    """
    print(f"Generating Log Sweep ({F_START:.0f}-{F_END:.0f}Hz)...")

    # 1. Generate Buffer
    fs_audio: int = 48000
    wave = audio.generate_log_sweep(F_START, F_END, DURATION, fs_audio, AMPLITUDE)

    # Define the play function
    def start_playback() -> None:
        print("🔊 Playing Sweep...")
        sd.play(wave, samplerate=fs_audio, blocking=False)

    # 2. Start Scope
    # on_launch triggers playback only when the window is visible
    with daq.DAQInterface() as device:
        viz.run_live_scope(
            device.stream_generator(),
            title="Transfer Function: Log Sine Sweep",
            stop_condition=lambda: not sd.get_stream().active,
            on_launch=start_playback,
        )

    print("Done.")


if __name__ == "__main__":
    main()
