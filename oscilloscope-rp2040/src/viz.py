import time

import matplotlib.pyplot as plt
import numpy as np

from . import config, dsp


def init_scope_plot(samples=config.LIVE_SAMPLES, fs=config.FS_DEFAULT):
    """
    Sets up a dark-mode oscilloscope figure.
    Returns: (fig, ax, line, text_element)
    """
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 5))

    # Time axis in ms
    t_max = (samples / fs) * 1000
    x_axis = np.linspace(0, t_max, samples)

    (line,) = ax.plot(x_axis, np.zeros(samples), color="#00ff00", lw=1.5)

    ax.set_ylim(0, 3.3)
    ax.set_xlim(0, t_max)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (V)")
    ax.grid(True, alpha=0.2)

    # Reference lines
    ax.axhline(config.V_MID, color="cyan", alpha=0.3, linestyle=":")
    ax.axhline(config.V_REF, color="red", alpha=0.3, lw=1)

    text = ax.text(0.02, 0.95, "Ready", transform=ax.transAxes, color="white")

    return fig, ax, line, text


def run_live_scope(
    stream_generator, title="Live Scope", stop_condition=None, on_launch=None
):
    """
    Reusable oscilloscope loop.

    Args:
        on_launch: Optional function to call once the window is open and ready.
                   (Used to start audio playback in sync with the visualizer)
    """
    fig, ax, line, fps_text = init_scope_plot()
    ax.set_title(title)

    # 1. Render the empty plot first to establish the window
    plt.show(block=False)
    fig.canvas.draw()
    background = fig.canvas.copy_from_bbox(ax.bbox)

    # 2. Flush events to ensure the window is actually visible
    fig.canvas.flush_events()

    # 3. NOW start the external process (Audio)
    if on_launch:
        print("🚀 Scope Ready. Triggering Launch Callback...")
        on_launch()

    frame_count = 0
    last_fps_time = time.time()

    print(f"📊 Scope running: {title}")

    try:
        for raw_data in stream_generator:
            # Check external stop condition (e.g., audio finished)
            if stop_condition and stop_condition():
                break

            # Check if window closed by user
            if not plt.fignum_exists(fig.number):
                break

            # DSP Processing
            voltages = dsp.raw_to_volts(raw_data)
            stable_wave = dsp.software_trigger(voltages)

            # Blitting Update
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
        pass
    finally:
        plt.close(fig)
        print("Scope Closed.")


def run_playback_scope(
    data: np.ndarray,
    fs: float,
    samples_per_frame: int = config.LIVE_SAMPLES,
    title: str = "Playback",
):
    """
    Runs a scope visualization from a recorded array.
    Moved from scripts/visualization/playback_scope.py.
    """
    total_samples = data.size
    duration_sec = total_samples / fs
    total_frames = total_samples // samples_per_frame

    # Setup Plot
    fig, ax, line, status_text = init_scope_plot()
    ax.set_title(title)

    # Handle window close
    stop_flag = {"value": False}

    def on_close(event):
        stop_flag["value"] = True

    fig.canvas.mpl_connect("close_event", on_close)

    # Pre-calc background
    plt.show(block=False)
    fig.canvas.draw()
    background = fig.canvas.copy_from_bbox(ax.bbox)

    start_time = time.time()

    try:
        while not stop_flag["value"]:
            elapsed = time.time() - start_time

            # Determine frame
            current_frame_idx = int(elapsed * (fs / samples_per_frame))

            if current_frame_idx >= total_frames:
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

            # Sync check
            next_frame_time = (current_frame_idx + 1) * (samples_per_frame / fs)
            sleep_time = (start_time + next_frame_time) - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass
    finally:
        plt.close(fig)


def analyze_signal_plot(signal: np.ndarray, fs: float, title: str = "Signal Analysis"):
    """
    Static analysis plot for a captured signal file.
    Shows Time Domain and Frequency Spectrum.
    """
    # Prep analysis
    ac_signal = dsp.remove_dc(signal)
    freqs, mags = dsp.compute_spectrum(ac_signal, fs)
    fundamental = dsp.estimate_fundamental(freqs, mags)

    # Plotting
    t_axis = (np.arange(signal.size) / fs) * 1000

    plt.figure(figsize=(12, 8))

    plt.subplot(2, 1, 1)
    plt.plot(t_axis, signal, color="lime")
    plt.title(f"{title} | Pitch: {fundamental:.1f} Hz")
    plt.grid(True, alpha=0.3)
    plt.ylabel("Voltage (V)")
    plt.xlabel("Time (ms)")

    plt.subplot(2, 1, 2)
    plt.plot(freqs, mags, color="orange")
    plt.xlim(0, 2000)
    plt.grid(True, alpha=0.3)
    plt.ylabel("Magnitude")
    plt.xlabel("Frequency (Hz)")

    plt.tight_layout()
    plt.show()
