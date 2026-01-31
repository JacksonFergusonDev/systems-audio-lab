"""
Script to generate a continuous waveform and visualize it in real-time.

This script creates a software oscillator (sine, square, etc.), plays it
through the system audio, and streams the loopback/output capture from
the DAQ to a live oscilloscope window.
"""

from sysaudio import audio, daq, viz

# Configuration
SHAPE: str = "sine"  # Options: "sine", "triangle", "square", "saw"
FREQ_HZ: float = 440.0  # Frequency in Hz
AMPLITUDE: float = 0.5  # Peak amplitude (0.0 to 1.0)


def main() -> None:
    """
    Main execution entry point.

    Sets up the oscillator and the DAQ interface, then launches the
    live scope. The audio playback is triggered via the `on_launch`
    callback to ensure it starts only when the visualizer is ready.
    """
    print(f"Initializing {SHAPE} wave at {FREQ_HZ}Hz...")

    # 1. Init Audio (auto_start=False means it waits for the scope)
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
