import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, dsp, io, viz


def visualize_recording():
    # 1. Select File
    filepath = io.select_file_cli(config.DATA_DIR_CONTINUOUS)
    if not filepath:
        return

    print(f"Loading {filepath}...")
    # Load signal (auto-flattens if needed)
    data, fs = io.load_signal(filepath)

    # 2. Normalize Data
    # If data is integer (raw ADC), convert to Volts for display
    if np.issubdtype(data.dtype, np.integer):
        print("Detected Raw ADC data. Converting to Volts...")
        data = dsp.raw_to_volts(data)

    total_samples = data.size
    duration_sec = total_samples / fs

    print(f"Duration: {duration_sec:.1f}s (@ {fs:.0f} Hz)")

    # 3. Setup Plot
    fig, ax, line, status_text = viz.init_scope_plot()
    ax.set_title(f"PLAYBACK: {os.path.basename(filepath)}")

    # Handle window close
    stop_flag = {"value": False}

    def on_close(event):
        stop_flag["value"] = True

    fig.canvas.mpl_connect("close_event", on_close)

    # 4. Playback Loop
    # We slice the long array into "frames" to mimic the oscilloscope refresh rate
    samples_per_frame = config.LIVE_SAMPLES
    total_frames = total_samples // samples_per_frame

    # Pre-calc background
    plt.show(block=False)
    fig.canvas.draw()
    background = fig.canvas.copy_from_bbox(ax.bbox)

    start_time = time.time()

    try:
        while not stop_flag["value"]:
            elapsed = time.time() - start_time

            # Determine which "frame" of the file we should be looking at
            current_frame_idx = int(elapsed * (fs / samples_per_frame))

            if current_frame_idx >= total_frames:
                print("End of recording.")
                break

            # Extract slice
            start_idx = current_frame_idx * samples_per_frame
            end_idx = start_idx + samples_per_frame
            voltages = data[start_idx:end_idx]

            # Triggering
            stabilized = dsp.software_trigger(voltages)

            # Update Plot
            fig.canvas.restore_region(background)
            line.set_ydata(stabilized)
            ax.draw_artist(line)

            # Update Text
            progress = (current_frame_idx / total_frames) * 100
            status_text.set_text(
                f"{elapsed:.1f}s / {duration_sec:.1f}s ({progress:.0f}%)"
            )
            ax.draw_artist(status_text)

            fig.canvas.blit(ax.bbox)
            fig.canvas.flush_events()

            # Sync check: If we are rendering faster than real-time, sleep
            next_frame_time = (current_frame_idx + 1) * (samples_per_frame / fs)
            sleep_time = (start_time + next_frame_time) - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    visualize_recording()
