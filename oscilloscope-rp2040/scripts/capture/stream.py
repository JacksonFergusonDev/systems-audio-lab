"""
Entry point for continuous data streaming.

This script initiates an infinite capture loop, streaming data from the DAQ
to disk until interrupted by the user (Ctrl+C). It is useful for long-duration
logging or monitoring sessions.
"""

import os
import sys

# Ensure src is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sysaudio import experiments  # noqa: E402


def main() -> None:
    """
    Main execution entry point.

    Calls `experiments.capture_continuous_stream`, which handles the
    infinite loop, buffering, and graceful shutdown upon KeyboardInterrupt.
    """
    experiments.capture_continuous_stream()


if __name__ == "__main__":
    main()
