import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import experiments

# --- USER CONFIGURATION ---
MODE = "sweep"


def main():
    if MODE == "sweep":
        experiments.capture_sweep_transfer(20.0, 20000.0, 5.0, 0.5)
    elif MODE == "steady":
        experiments.capture_steady_transfer("sine", 1000.0, 0.5)
    else:
        print(f"❌ Unknown MODE: {MODE}")


if __name__ == "__main__":
    main()
