import sys
import shutil
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter

from . import config, dsp, io


# --- DEPENDENCY CHECK ---
def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("\n\033[91m[ERROR] FFmpeg not found.\033[0m")
        print("Please install ffmpeg to render video.")
        sys.exit(1)


# --- EFFECT ENGINES ---
def _style_base(ax, samples, fs):
    t_max_ms = (samples / fs) * 1000
    ax.set_ylim(0, 3.3)
    ax.set_xlim(0, t_max_ms)
    ax.axis("off")
    ax.grid(True, which="major", color="#222222", linestyle="-", linewidth=1)
    ax.axhline(config.V_MID, color="#222222", linestyle="-", lw=1)
    return np.linspace(0, t_max_ms, samples)


def setup_clean(samples, fs, v_conf):
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)
    (line,) = ax.plot(x, np.zeros(samples), color="#00ff00", lw=1.5)

    return fig, ax, [line], lambda lines, data: lines[0].set_ydata(data)


def setup_crt_bloom(samples, fs, v_conf):
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)

    lines = []
    # Glow layers
    for i in range(3):
        lw = 4 + (i * 4)
        alpha = 0.1 / (i + 1)
        (l,) = ax.plot(x, np.zeros(samples), color="#32CD32", lw=lw, alpha=alpha)
        lines.append(l)
    (core,) = ax.plot(x, np.zeros(samples), color="#ccffcc", lw=1.2, alpha=1.0)
    lines.append(core)

    def update(lines, data):
        for line in lines:
            line.set_ydata(data)

    return fig, ax, lines, update


def setup_cyber_glitch(samples, fs, v_conf):
    plt.style.use("dark_background")
    fig = plt.figure(
        figsize=(v_conf["width"] / v_conf["dpi"], v_conf["height"] / v_conf["dpi"]),
        dpi=v_conf["dpi"],
    )
    ax = fig.add_subplot(111)
    x = _style_base(ax, samples, fs)

    colors = ["#ff0000", "#00ff00", "#0000ff"]
    lines = [ax.plot(x, np.zeros(samples), color=c, lw=2, alpha=0.6)[0] for c in colors]

    def update(lines, data):
        shift = int(samples * 0.005)
        r_data = np.roll(data, shift)
        b_data = np.roll(data, -shift)
        if np.random.rand() > 0.95:
            r_data = np.roll(r_data, shift * 4)

        lines[0].set_ydata(r_data)
        lines[1].set_ydata(data)
        lines[2].set_ydata(b_data)

    return fig, ax, lines, update


EFFECTS = {
    "1": ("Clean (Clinical)", setup_clean),
    "2": ("CRT Bloom (Phosphor)", setup_crt_bloom),
    "3": ("Cyber Glitch (Aberration)", setup_cyber_glitch),
}


# --- MAIN RENDER PIPELINE ---
def generate_video(filepath, output_path, effect_id, video_conf):
    print(f"--- INITIALIZING RENDER ENGINE ---\nSource: {filepath}")

    raw_data, fs = io.load_signal(filepath)
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

    # Pass video config to setup function
    fig, ax, lines, update_func = setup_func(window_size, fs, video_conf)

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
                stabilized = dsp.software_trigger(chunk)

                update_func(lines, stabilized)

                t = i / video_conf["fps"]
                time_text.set_text(f"{t:.2f}s")
                status_text.set_alpha(1.0 if (i % 60) < 30 else 0.3)

                writer.grab_frame()

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
