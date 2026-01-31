"""
Script to launch a standalone live oscilloscope feed.

This script demonstrates how to manually construct a high-performance
matplotlib blitting loop to visualize data streaming from the DAQ.
It serves as the foundational example for real-time plotting in this project.
"""

import os
import sys
import time
from typing import Any, cast

import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import daq, dsp, viz  # noqa: E402


def main() -> None:
    """
    Main execution entry point.

    Initializes the scope window and runs the animation loop using
    background blitting for optimal frame rates.
    """
    # Setup Plot using the shared visualization library
    fig, ax, line, fps_text = viz.init_scope_plot()

    # Pre-calculate background for blitting (optimization)
    # This renders the static elements (grid, axes) once and caches them.
    plt.show(block=False)
    fig.canvas.draw()
    background = cast(Any, fig.canvas).copy_from_bbox(ax.bbox)

    frame_count: int = 0
    last_fps_time: float = time.time()

    print("Starting Live Feed...")

    try:
        # Connect to DAQ and stream data
        with daq.DAQInterface() as device:
            stream = device.stream_generator()

            for raw_data in stream:
                # 1. DSP Processing
                voltages = dsp.raw_to_volts(raw_data)
                stable_wave = dsp.software_trigger(voltages)

                # 2. Update Plot (Blitting)
                # Restore the clean background
                cast(Any, fig.canvas).restore_region(background)
                # Update line data
                line.set_ydata(stable_wave)
                # Redraw only the dynamic artists
                ax.draw_artist(line)

                # 3. FPS Calculation & Display
                frame_count += 1
                now = time.time()
                if now - last_fps_time >= 1.0:
                    fps = frame_count / (now - last_fps_time)
                    fps_text.set_text(f"FPS: {fps:.0f}")
                    frame_count = 0
                    last_fps_time = now

                ax.draw_artist(fps_text)

                # 4. Refresh Screen
                fig.canvas.blit(ax.bbox)
                fig.canvas.flush_events()

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
