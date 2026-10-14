# Firmware Architecture: RP2040 Data Acquisition Engine

This directory contains the MicroPython firmware (`main.py`) that turns the RP2040 into a buffered data acquisition (DAQ) device. It reads the analog front end through the ADC and sends the samples to the laptop for analysis.

## System Overview

The firmware works as "store-and-forward": it captures a burst of samples into a buffer allocated in RAM at boot, and only sends the data over USB serial once the capture is complete. Streaming samples while capturing would let USB delays disturb the sample timing; capturing first keeps the sample rate steady.

The cost is that each capture is limited to what fits in RAM, and continuous recordings (made by repeating short bursts) have gaps between bursts.

## Operational Theory

`main.py` waits for one-byte commands from the host. When one arrives, it runs a tight sampling loop compiled for the RP2040's ARM Cortex-M0+ processor.

### Memory Management Strategy

Allocating memory in MicroPython is slow and takes an unpredictable amount of time. To keep sampling intervals consistent, all memory is allocated once at startup:

1. **Static Allocation:** A single contiguous `array('H')` (unsigned short) of size $16,384$ is allocated at boot. This prevents heap fragmentation over long capture sessions.
1. **Zero-Copy Transmission:** Data is sent to the host through `memoryview()` objects, so the USB driver reads the sample buffer directly instead of copying it first.

### Acquisition Modes

The firmware has two capture modes.

#### 1. Science Mode (Command: `s`)

Used for spectrum analysis and recordings.

- **Buffer Depth:** Full capacity ($16,384$ samples).
- **Garbage Collection:** Disabled during the capture (`gc.disable()`). MicroPython's garbage collector (GC) pauses the program while it runs, which can take milliseconds and would leave a gap in the samples. With it off, the sampling loop runs without interruption.
- **Post-Processing:** `gc.collect()` runs after the data has been sent, to clean up memory.

#### 2. Video Mode (Command: `v`)

Used for real-time oscilloscope visualization (`live_scope.py`).

- **Buffer Depth:** Shallow burst ($1,024$ samples).
- **Garbage Collection:** Left enabled. The capture is short enough ($<15$ ms) that a collection is unlikely to run during it.
- **Slicing:** The firmware sends the first 1,024 samples of the main buffer through a `memoryview` slice, which refers to the same memory rather than copying it.

## Optimization: The Native Emitter

MicroPython normally compiles code to bytecode and runs it in an interpreter. The interpreter adds delay between ADC reads.

To reduce that delay, the capture loop is decorated with `@micropython.native`.

```python
@micropython.native
def capture_burst(adc_obj, buf, size: int):
    for i in range(size):
        buf[i] = adc_obj.read_u16()
```

This tells the compiler to emit ARM Thumb machine code for the Cortex-M0+. The `read_u16()` call still has some method-lookup overhead, but the loop itself (increment, compare, jump) becomes native CPU instructions. This is what lets the loop reach the measured sample rate of $F_s = 97.69$ kHz.

## Deployment

### Prerequisites

- **Hardware:** RP2040 (Pico, Zero, or similar).
- **Firmware:** A recent build of MicroPython (v1.27 recommended).
- **I/O:** The device must be connected via USB Serial.

### Installation

1. Flash the standard MicroPython `.uf2` image to your board.
1. Copy `main.py` to the root of the device filesystem. I used [Thonny](https://thonny.org/), which works well for this.

### Configuration

The default pin assignment matches the RP2040-Zero and Pico pinout standards:

- **ADC Input:** GPIO 28 (ADC2)

To change the buffer size or pin assignment, edit the `CONFIGURATION` block in `main.py`. `MAX_SAMPLES` is limited by the RP2040's RAM (264kB in total, much of it used by MicroPython itself).

## Interface Protocol

The device listens on `stdin` for commands and writes raw binary data to `stdout`.

| Command | Hex | Function | Output Format |
| :--- | :--- | :--- | :--- |
| `s` | `0x73` | Science Burst | $32,768$ bytes (raw little-endian uint16) |
| `v` | `0x76` | Video Burst | $2,048$ bytes (raw little-endian uint16) |

**Note on Resolution:** The RP2040 ADC hardware is 12-bit ($0 \dots 4095$). MicroPython scales this to a 16-bit integer ($0 \dots 65535$). The host-side DSP pipeline handles the conversion to voltage.

## Future Development: DMA Implementation

The native-code loop reaches about 98 kSps, but the CPU is busy reading the ADC the whole time. The next step would be the RP2040's direct memory access (DMA) controller.

With the ADC's FIFO triggering a DMA channel, samples move to RAM without the CPU. In principle this allows:

1. Higher sample rates (up to 500 kSps).
1. Sample timing set by the crystal oscillator rather than by software.
1. Simultaneous processing (CPU free during capture).

*Current status: The native loop is fast enough for audio-range analysis (Nyquist $\approx 48$ kHz). The firmware for this v0 prototype is frozen; DMA is planned for the v1.0 hardware instead.*
