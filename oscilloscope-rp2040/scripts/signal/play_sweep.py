import os
import sys

import sounddevice as sd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import audio, daq, viz

# --- CONFIGURATION (EDIT ME) ---
F_START = 20.0  # Start Frequency (Hz)
F_END = 20000.0  # End Frequency (Hz)
DURATION = 5.0  # Seconds
AMPLITUDE = 0.5  # 0.0 to 1.0
# -------------------------------


def main():
    print(f"Generating Log Sweep ({F_START:.0f}-{F_END:.0f}Hz)...")

    # 1. Generate Buffer
    fs_audio = 48000
    wave = audio.generate_log_sweep(F_START, F_END, DURATION, fs_audio, AMPLITUDE)

    # Define the play function
    def start_playback():
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
