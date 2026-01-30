import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src import experiments


def main():
    experiments.capture_continuous_stream()


if __name__ == "__main__":
    main()
