import shutil
import sys
from typing import Any, Callable, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from . import config, dsp, io


# --- DEPENDENCY CHECK ---
def check_ffmpeg() -> None:
    """
    Verifies that FFmpeg is installed and accessible in the system PATH.
    Exits the program if not found.
    """
    if shutil.which("ffmpeg") is None:
        print("\n\033[91m[ERROR] FFmpeg not found.\033[0m")
        print("Please install ffmpeg to render video.")
        sys.exit(1)


# --- EFFECT ENGINES ---
def _style_base(ax: Axes, samples: int, fs: float) -> np.ndarray:
    """
    Applies common styling to the plot axis (grid, limits, removing spines).

    Returns
    -------
    np.ndarray
        The time axis array for plotting.
    """
    t_max_ms = (samples / fs) * 1000
    ax.set_ylim(0, 3.3)
    ax.set_xlim(0, t_max_ms)
    ax.axis("off")
    ax.grid(True, which="major", color="#222222", linestyle="-", linewidth=1)
    ax.axhline(config.V_MID, color="#222222", linestyle="-", lw=1)
    return np.linspace(0, t_max_ms, samples)


def setup_clean(
    samples: int, fs: float, v_conf: Dict[str, Any]
) -> Tuple[Figure, Axes, List[Line2D], Callable[[List[Line2D], np.ndarray], None]]:
    """
    Sets up the 'Clean' visualization style (clinical, green line).
    """
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)
    (line,) = ax.plot(x, np.zeros(samples), color="#00ff00", lw=1.5)

    def update(lines: List[Line2D], data: np.ndarray) -> None:
        lines[0].set_ydata(data)

    return fig, ax, [line], update


def setup_crt_bloom(
    samples: int, fs: float, v_conf: Dict[str, Any]
) -> Tuple[Figure, Axes, List[Line2D], Callable[[List[Line2D], np.ndarray], None]]:
    """
    Sets up the 'CRT Bloom' visualization style (stacked glowing lines).
    """
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)

    lines = []
    # Glow layers (simulating phosphor persistence/bloom)
    for i in range(3):
        lw = 4 + (i * 4)
        alpha = 0.1 / (i + 1)
        (glow_line,) = ax.plot(
            x, np.zeros(samples), color="#32CD32", lw=lw, alpha=alpha
        )
        lines.append(glow_line)
    # Bright core
    (core,) = ax.plot(x, np.zeros(samples), color="#ccffcc", lw=1.2, alpha=1.0)
    lines.append(core)

    def update(lines: List[Line2D], data: np.ndarray) -> None:
        for line in lines:
            line.set_ydata(data)

    return fig, ax, lines, update


def setup_cyber_glitch(
    samples: int, fs: float, v_conf: Dict[str, Any]
) -> Tuple[Figure, Axes, List[Line2D], Callable[[List[Line2D], np.ndarray], None]]:
    """
    Sets up the 'Cyber Glitch' visualization style (RGB separation + jitter).
    """
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)

    colors = ["#ff0000", "#00ff00", "#0000ff"]
    lines = [ax.plot(x, np.zeros(samples), color=c, lw=2, alpha=0.6)[0] for c in colors]

    def update(lines: List[Line2D], data: np.ndarray) -> None:
        # Simulate chromatic aberration by rolling channels
        shift = int(samples * 0.005)
        r_data = np.roll(data, shift)
        b_data = np.roll(data, -shift)

        # Occasional glitch jump
        if np.random.rand() > 0.95:
            r_data = np.roll(r_data, shift * 4)

        lines[0].set_ydata(r_data)
        lines[1].set_ydata(data)
        lines[2].set_ydata(b_data)

    return fig, ax, lines, update


# Registry of available effects
EFFECTS: Dict[str, Tuple[str, Callable]] = {
    "1": ("Clean (Clinical)", setup_clean),
    "2": ("CRT Bloom (Phosphor)", setup_crt_bloom),
    "3": ("Cyber Glitch (Aberration)", setup_cyber_glitch),
}


# --- MAIN RENDER PIPELINE ---
def generate_video(
    filepath: str, output_path: str, effect_id: str, video_conf: Dict[str, Any]
) -> None:
    """
    Renders an oscilloscope visualization video from a data file.

    Loads the signal, applies the selected visual effect, stabilizes the
    waveform using a software trigger, and encodes the output via FFmpeg.

    Parameters
    ----------
    filepath : str
        Path to the source .npz data file.
    output_path : str
        Path for the output video file (e.g., .mp4).
    effect_id : str
        Key corresponding to the desired effect in the EFFECTS dict.
    video_conf : Dict[str, Any]
        Dictionary containing video settings (width, height, fps, bitrate, etc.).
    """
    print(f"--- INITIALIZING RENDER ENGINE ---\nSource: {filepath}")

    raw_data, fs = io.load_signal(filepath)
    # Ensure float voltage for rendering
    data = (
        dsp.raw_to_volts(raw_data)
        if np.issubdtype(raw_data.dtype, np.integer)
        else raw_data
    )

    total_samples = data.size
    duration = total_samples / fs
    total_frames = int(duration * video_conf["fps"])
    samples_per_step = fs / video_conf["fps"]
    window_size = config.LIVE_SAMPLES

    if effect_id not in EFFECTS:
        effect_id = "2"
    effect_name, setup_func = EFFECTS[effect_id]

    # Initialize Plot
    fig, ax, lines, update_func = setup_func(window_size, fs, video_conf)

    # UI Overlays
    status_text = ax.text(
        0.02,
        0.95,
        "REC",
        transform=ax.transAxes,
        color="#cc0000",
        fontsize=14,
        family="monospace",
        weight="bold",
    )
    time_text = ax.text(
        0.98,
        0.05,
        "00:00.00",
        transform=ax.transAxes,
        color="white",
        fontsize=12,
        family="monospace",
        ha="right",
        alpha=0.7,
    )

    # Encoder Setup
    writer = FFMpegWriter(
        fps=video_conf["fps"],
        bitrate=video_conf["bitrate"],
        extra_args=[
            "-vcodec",
            "libx264",
            "-preset",
            video_conf["preset"],
            "-crf",
            str(video_conf["crf"]),
        ],
    )

    print(
        f"Config: {video_conf['width']}x{video_conf['height']} @ {video_conf['fps']}fps"
    )
    print(f"Encoding to: {output_path}...")

    try:
        with writer.saving(fig, output_path, dpi=video_conf["dpi"]):
            for i in range(total_frames):
                center_idx = int(i * samples_per_step)
                if center_idx + window_size >= total_samples:
                    break

                chunk = data[center_idx : center_idx + window_size]

                # Stabilize waveform for visual continuity
                stabilized = dsp.software_trigger(chunk)

                update_func(lines, stabilized)

                # Update UI
                t = i / video_conf["fps"]
                time_text.set_text(f"{t:.2f}s")
                status_text.set_alpha(1.0 if (i % 60) < 30 else 0.3)  # Blink effect

                writer.grab_frame()

                # Progress Bar
                if i % 60 == 0:
                    pct = i / total_frames * 100
                    sys.stdout.write(
                        f"\rRendering: [{pct:.1f}%] Frame {i}/{total_frames}"
                    )
                    sys.stdout.flush()

        print(f"\n\nSUCCESS: Render saved to {output_path}")

    except KeyboardInterrupt:
        print("\n\n[WARN] Render cancelled by user.")
    finally:
        plt.close(fig)
