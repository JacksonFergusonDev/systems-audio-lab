"""
Script to render high-quality video visualizations from captured signal data.

This script acts as a frontend for the `src.render` engine. It guides the user
through selecting a continuous recording file, choosing a visual effect style
(e.g., CRT Bloom, Cyber Glitch), and configuring output video parameters.
"""

import os
import sys
from typing import Any, Dict

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import config, io, render  # noqa: E402

# Configuration for video output
VIDEO_SETTINGS: Dict[str, Any] = {
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "dpi": 100,
    "bitrate": 8000,  # kbps
    "crf": 18,  # 0-51 (lower is better quality, 18 is visually lossless)
    # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    "preset": "slow",
}


def main() -> None:
    """
    Main execution entry point.

    Performs environment checks (FFmpeg), handles user input for file selection
    and effect choice, determines the output filename, and invokes the
    rendering engine.
    """
    # 1. Check Environment
    render.check_ffmpeg()

    # 2. Select File
    target_file = io.select_file_cli(config.DATA_DIR_CONTINUOUS)
    if not target_file:
        print("No file selected. Exiting.")
        return

    # 3. Select Visual Effect
    print("\n--- VISUAL STYLE ---")
    for key, (name, _) in render.EFFECTS.items():
        print(f"[{key}] {name}")

    effect_choice = input("Select Effect [Default: 2]: ").strip()
    if not effect_choice:
        effect_choice = "2"

    # 4. Define Output Path
    # Extract style name for filename tagging (e.g., "_crt.mp4")
    effect_name = render.EFFECTS.get(effect_choice, ("default",))[0]
    effect_tag = effect_name.split()[0].lower()

    filename = os.path.basename(target_file).replace(".npz", f"_{effect_tag}.mp4")
    out_path = os.path.join(os.path.dirname(target_file), filename)

    # 5. Execute Render
    # We pass the settings dict into the engine
    render.generate_video(target_file, out_path, effect_choice, VIDEO_SETTINGS)


if __name__ == "__main__":
    main()
