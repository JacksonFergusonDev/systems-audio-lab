# pyright: reportMissingImports=false

import array
import gc
import sys

import machine
import micropython
import uselect

# Configuration
ADC_PIN_NUM = 28
MAX_SAMPLES = 16384  # Science Mode Buffer
LIVE_SAMPLES = 1024  # Video Mode Buffer

# Setup ADC
adc = machine.ADC(machine.Pin(ADC_PIN_NUM))
# Allocate max memory once to avoid fragmentation
adc_buffer = array.array("H", [0] * MAX_SAMPLES)


# Pre-compile the capture function to arm machine code
@micropython.native
def capture_burst(adc_obj, buf, size: int):
    """
    Reads a burst of analog values into a buffer using native code generation.

    This function is decorated with @micropython.native for speed. It avoids
    memory allocation during the loop to maintain deterministic timing.

    Parameters
    ----------
    adc_obj : machine.ADC
        The configured ADC instance to read from.
    buf : array.array
        The pre-allocated buffer (array of unsigned short 'H') to store data.
    size : int
        The number of samples to capture. Must be <= len(buf).
    """
    for i in range(size):
        buf[i] = adc_obj.read_u16()


def main():
    """
    Main firmware loop.

    Listens for single-character commands over USB Serial (stdin):
    - 's': Science Mode (High Res). Captures MAX_SAMPLES, with GC disabled
           during capture for stability. Sends full buffer.
    - 'v': Video Mode (Low Latency). Captures LIVE_SAMPLES. Sends partial
           buffer immediately. No GC manipulation for higher frame rates.
    """
    poll_obj = uselect.poll()
    poll_obj.register(sys.stdin, uselect.POLLIN)

    while True:
        # Poll with a 100ms timeout to allow other background tasks if necessary
        if not poll_obj.poll(100):
            continue

        # Read 1 byte from stdin
        cmd = sys.stdin.read(1)

        # 's' = SCIENCE MODE (High Res, Deep Buffer)
        if cmd == "s":
            gc.disable()
            capture_burst(adc, adc_buffer, MAX_SAMPLES)
            gc.enable()
            # Send FULL buffer
            sys.stdout.buffer.write(memoryview(adc_buffer))
            gc.collect()

        # 'v' = VIDEO MODE (Low Latency, Short Buffer)
        elif cmd == "v":
            # No need to disable GC for short bursts, keeps it snappy
            capture_burst(adc, adc_buffer, LIVE_SAMPLES)

            # Send ONLY the first 1024 samples
            # This slicing [:LIVE_SAMPLES] is very fast (no copying)
            sys.stdout.buffer.write(memoryview(adc_buffer)[:LIVE_SAMPLES])

            # Note: We don't GC here to keep frame rate high


if __name__ == "__main__":
    main()
