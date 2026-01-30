import os
import sys
import time

import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import daq, dsp, viz


def run_oscilloscope():
    # Setup Plot
    fig, ax, line, fps_text = viz.init_scope_plot()

    # Pre-calculate background for blitting
    plt.show(block=False)
    fig.canvas.draw()
    background = fig.canvas.copy_from_bbox(ax.bbox)

    frame_count = 0
    last_fps_time = time.time()

    print("Starting Live Feed...")

    try:
        # Use the generator for streaming
        with daq.DAQInterface() as device:
            stream = device.stream_generator()

            for raw_data in stream:
                # Process
                voltages = dsp.raw_to_volts(raw_data)
                stable_wave = dsp.software_trigger(voltages)

                # Update Plot
                fig.canvas.restore_region(background)
                line.set_ydata(stable_wave)
                ax.draw_artist(line)

                # FPS Calculation
                frame_count += 1
                now = time.time()
                if now - last_fps_time >= 1.0:
                    fps = frame_count / (now - last_fps_time)
                    fps_text.set_text(f"FPS: {fps:.0f}")
                    frame_count = 0
                    last_fps_time = now

                ax.draw_artist(fps_text)
                fig.canvas.blit(ax.bbox)
                fig.canvas.flush_events()

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    run_oscilloscope()
