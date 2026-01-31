"""
Orchestration script for capturing transfer function data.

This script serves as the primary entry point for capturing audio sweeps
or steady-state signals required for Bode plots and linearity analysis.
It delegates the actual acquisition logic to the `experiments` module.
"""

from sysaudio import experiments

# Configuration
# Options: 'sweep' (Log Sine Sweep) or 'steady' (Single Frequency Burst)
MODE: str = "sweep"


def main() -> None:
    """
    Main execution entry point.

    Selects the experiment mode based on the global MODE constant and
    calls the appropriate function from `src.experiments`.
    """
    if MODE == "sweep":
        # Capture a 20Hz-20kHz log sweep over 5 seconds at 50% amplitude
        experiments.capture_sweep_transfer(
            f_start=20.0, f_end=20000.0, duration=5.0, amp=0.5
        )
    elif MODE == "steady":
        # Capture a 1kHz sine wave burst
        experiments.capture_steady_transfer(shape="sine", freq=1000.0, amp=0.5)
    else:
        print(f"❌ Unknown MODE: {MODE}")


if __name__ == "__main__":
    main()
