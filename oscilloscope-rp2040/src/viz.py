import time
from typing import Any, Callable, Iterable, Optional, Tuple, cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text

from . import config, dsp


def init_scope_plot(
    samples: int = config.LIVE_SAMPLES, fs: float = config.FS_DEFAULT
) -> Tuple[Figure, Axes, Line2D, Text]:
    """
    Sets up a dark-mode oscilloscope figure with reference lines.

    Parameters
    ----------
    samples : int
        Number of samples to display in the window.
    fs : float
        Sampling rate in Hz.

    Returns
    -------
    Tuple[Figure, Axes, Line2D, Text]
        The figure, axis, signal line object, and status text object.
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

    # Reference lines (Virtual Ground and 3.3V Rail)
    ax.axhline(config.V_MID, color="cyan", alpha=0.3, linestyle=":")
    ax.axhline(config.V_REF, color="red", alpha=0.3, lw=1)

    text = ax.text(0.02, 0.95, "Ready", transform=ax.transAxes, color="white")

    return fig, ax, line, text


def run_live_scope(
    stream_generator: Iterable[np.ndarray],
    title: str = "Live Scope",
    stop_condition: Optional[Callable[[], bool]] = None,
    on_launch: Optional[Callable[[], None]] = None,
) -> None:
    """
    Runs a reusable, high-performance oscilloscope loop using blitting.

    Parameters
    ----------
    stream_generator : Iterable[np.ndarray]
        Iterator yielding chunks of raw ADC data.
    title : str
        Window title.
    stop_condition : Optional[Callable[[], bool]]
        Function returning True when the loop should exit (e.g., audio finished).
    on_launch : Optional[Callable[[], None]]
        Callback executed once the window is rendered and ready.
        Useful for syncing audio playback start.
    """
    fig, ax, line, fps_text = init_scope_plot()
    ax.set_title(title)

    # 1. Render initial frame to establish window context
    plt.show(block=False)
    fig.canvas.draw()
    background = cast(Any, fig.canvas).copy_from_bbox(ax.bbox)

    # 2. Flush events to force window visibility before processing data
    fig.canvas.flush_events()

    # 3. Trigger external process (e.g., Audio) now that viz is ready
    if on_launch:
        print("🚀 Scope Ready. Triggering Launch Callback...")
        on_launch()

    frame_count = 0
    last_fps_time = time.time()

    print(f"📊 Scope running: {title}")

    try:
        for raw_data in stream_generator:
            # Check external stop condition
            if stop_condition and stop_condition():
                break

            # Check if window closed by user
            if not plt.fignum_exists(fig.number):
                break

            # DSP Processing & Stabilization
            voltages = dsp.raw_to_volts(raw_data)
            stable_wave = dsp.software_trigger(voltages)

            # Blitting Update (Redraw only the line, not the grid)
            cast(Any, fig.canvas).restore_region(background)
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
) -> None:
    """
    Simulates a live scope visualization from a recorded data array.

    Parameters
    ----------
    data : np.ndarray
        Full recording array (voltages).
    fs : float
        Sampling rate in Hz.
    samples_per_frame : int
        Number of samples to display per frame.
    title : str
        Window title.
    """
    total_samples = data.size
    duration_sec = total_samples / fs
    total_frames = total_samples // samples_per_frame

    # Setup Plot
    fig, ax, line, status_text = init_scope_plot()
    ax.set_title(title)

    # Handle window close event
    stop_flag = {"value": False}

    def on_close(event: Any) -> None:
        stop_flag["value"] = True

    fig.canvas.mpl_connect("close_event", on_close)

    # Pre-calc background for blitting
    plt.show(block=False)
    fig.canvas.draw()
    background = cast(Any, fig.canvas).copy_from_bbox(ax.bbox)

    start_time = time.time()

    try:
        while not stop_flag["value"]:
            elapsed = time.time() - start_time

            # Determine current frame based on real time
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
            cast(Any, fig.canvas).restore_region(background)
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

            # Sync check (Sleep if rendering is faster than real-time)
            next_frame_time = (current_frame_idx + 1) * (samples_per_frame / fs)
            sleep_time = (start_time + next_frame_time) - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass
    finally:
        plt.close(fig)


def analyze_signal_plot(
    signal: np.ndarray, fs: float, title: str = "Signal Analysis"
) -> None:
    """
    Generates a static analysis plot showing Time Domain and Frequency Spectrum.

    Parameters
    ----------
    signal : np.ndarray
        Signal voltage array.
    fs : float
        Sampling rate in Hz.
    title : str
        Plot title.
    """
    # Prep analysis
    ac_signal = dsp.remove_dc(signal)
    freqs, mags = dsp.compute_spectrum(ac_signal, fs)
    fundamental = dsp.estimate_fundamental(freqs, mags)

    # Plotting
    t_axis = (np.arange(signal.size) / fs) * 1000

    plt.figure(figsize=(12, 8))

    # Subplot 1: Time Domain
    plt.subplot(2, 1, 1)
    plt.plot(t_axis, signal, color="lime")
    plt.title(f"{title} | Pitch: {fundamental:.1f} Hz")
    plt.grid(True, alpha=0.3)
    plt.ylabel("Voltage (V)")
    plt.xlabel("Time (ms)")

    # Subplot 2: Frequency Domain
    plt.subplot(2, 1, 2)
    plt.plot(freqs, mags, color="orange")
    plt.xlim(0, 2000)
    plt.grid(True, alpha=0.3)
    plt.ylabel("Magnitude")
    plt.xlabel("Frequency (Hz)")

    plt.tight_layout()
    plt.show()
