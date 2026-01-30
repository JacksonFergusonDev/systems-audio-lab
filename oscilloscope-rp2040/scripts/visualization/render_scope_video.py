import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, io, render

# --- RENDER CONFIGURATION (User Editable) ---
# Adjust these to change the output video quality/format
VIDEO_SETTINGS = {
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "dpi": 100,
    "bitrate": 8000,  # kbps
    "crf": 18,  # 0-51 (lower is better quality, 18 is visually lossless)
    # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    "preset": "slow",
}


def main():
    # 1. Check Env
    render.check_ffmpeg()

    # 2. Select File
    target_file = io.select_file_cli(config.DATA_DIR_CONTINUOUS)
    if not target_file:
        print("No file selected. Exiting.")
        return

    # 3. Select Effect
    print("\n--- VISUAL STYLE ---")
    for key, (name, _) in render.EFFECTS.items():
        print(f"[{key}] {name}")

    effect_choice = input("Select Effect [Default: 2]: ").strip()
    if not effect_choice:
        effect_choice = "2"

    # 4. Define Output
    effect_tag = render.EFFECTS.get(effect_choice, ("default",))[0].split()[0].lower()
    filename = os.path.basename(target_file).replace(".npz", f"_{effect_tag}.mp4")
    out_path = os.path.join(os.path.dirname(target_file), filename)

    # 5. Execute
    # We pass the settings dict into the engine
    render.generate_video(target_file, out_path, effect_choice, VIDEO_SETTINGS)


if __name__ == "__main__":
    main()
