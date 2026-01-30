import array
import gc
import sys

import machine
import micropython
import uselect

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
ADC_PIN_NUM = 28  # KEPT YOUR CORRECT PIN
MAX_SAMPLES = 16384  # Science Mode Buffer
LIVE_SAMPLES = 1024  # Video Mode Buffer

# Setup ADC
adc = machine.ADC(machine.Pin(ADC_PIN_NUM))
# Allocate max memory once to avoid fragmentation
adc_buffer = array.array("H", [0] * MAX_SAMPLES)


# Pre-compile the capture function (Your optimization)
@micropython.native
def capture_burst(adc_obj, buf, size: int):
    for i in range(size):
        buf[i] = adc_obj.read_u16()


def main():
    poll_obj = uselect.poll()
    poll_obj.register(sys.stdin, uselect.POLLIN)

    while True:
        if not poll_obj.poll(100):
            continue

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
