# Firmware Architecture: RP2040 Data Acquisition Engine

This directory contains the MicroPython firmware (`main.py`) responsible for transforming the RP2040 into a high-speed, buffered Data Acquisition (DAQ) device. It serves as the bridge between the analog front end and the host-side analysis pipeline.

## System Overview

The firmware operates as a "store-and-forward" engine. Unlike typical streaming applications that push data continuously (and often suffer from jitter due to USB packetization or buffer underruns), this system prioritizes sample rate stability. It captures a precise burst of data into a pre-allocated ring buffer in RAM, then transmits the binary blob over USB Serial only after acquisition is complete.

This architecture was chosen to decouple the strict timing requirements of the ADC sampling loop from the non-deterministic latency of the USB-to-UART bridge.

## Operational Theory

The core of the firmware (`main.py`) implements a state machine that waits for single-byte commands from the host. Upon triggering, it enters a tight acquisition loop optimized for the RP2040's ARM Cortex-M0+ architecture.

### Memory Management Strategy
Dynamic memory allocation in Python is computationally expensive and non-deterministic. To guarantee consistent sampling intervals, the heap is locked down during initialization:

1.  **Static Allocation:** A single contiguous `array('H')` (unsigned short) of size $16,384$ is allocated at boot. This prevents heap fragmentation over long capture sessions.
2.  **Zero-Copy Transmission:** Data is sent to the host using `memoryview()` objects. This allows the USB driver to read directly from the ADC buffer memory without burning CPU cycles on intermediate copies.

### Acquisition Modes

The system supports two distinct capture topologies tailored for different stages of the analysis pipeline.

#### 1. Science Mode (Command: `s`)
Used for high-fidelity spectral analysis and recording.
* **Buffer Depth:** Full capacity ($16,384$ samples).
* **Garbage Collection:** Explicitly disabled (`gc.disable()`). The Python Garbage Collector (GC) is a "stop-the-world" event that can pause execution for milliseconds, destroying sample rate linearity. We sacrifice live interactivity to ensure the sampling loop runs without interruption.
* **Post-Processing:** A forced `gc.collect()` is triggered *after* transmission to reset the heap state.

#### 2. Video Mode (Command: `v`)
Used for real-time oscilloscope visualization (`live_scope.py`).
* **Buffer Depth:** Shallow burst ($1,024$ samples).
* **Latency Optimization:** GC is left enabled, as the capture duration is short enough ($<15$ ms) that the probability of a collection triggering is negligible.
* **Slicing:** The firmware transmits a slice of the main buffer (`buffer[:1024]`). Thanks to Python's buffer protocol, this slice is a pointer reference, not a copy, preserving throughput.

## Optimization: The Native Emitter

Standard MicroPython executes code by compiling it to bytecode, which is then interpreted by a virtual machine. While portable, the interpreter overhead adds significant delay between ADC reads.

To maximize throughput, the critical capture loop is decorated with `@micropython.native`.

```python
@micropython.native
def capture_burst(adc_obj, buf, size: int):
    for i in range(size):
        buf[i] = adc_obj.read_u16()
```

This instructs the compiler to emit **ARM Thumb machine code** directly for the Cortex-M0+. While the `read_u16()` call still incurs some method-lookup overhead, the loop mechanics (increment, compare, jump) become native CPU instructions. This optimization is critical for achieving the calibrated sample rate of $F_s \approx 97.8$ kHz.

## Deployment

### Prerequisites
* **Hardware:** RP2040 (Pico, Zero, or similar).
* **Firmware:** A recent build of MicroPython (v1.27 recommended).
* **I/O:** The device must be connected via USB Serial.

### Installation
1.  Flash the standard MicroPython `.uf2` image to your board.
2.  Copy `main.py` to the root of the device filesystem. I used [Thonny](https://thonny.org/) and would recommend it.

### Configuration
The default pin assignment matches the RP2040-Zero and Pico pinout standards:
* **ADC Input:** GPIO 28 (ADC2)

To modify the buffer sizes or pin assignments, edit the `CONFIGURATION` block in `main.py`. Note that `MAX_SAMPLES` is limited by the RP2040's available RAM (264kB total, though MicroPython uses a significant portion for the heap).

## Interface Protocol

The device listens on `stdin` for commands and writes raw binary data to `stdout`.

| Command | Hex | Function | Output Format |
| :--- | :--- | :--- | :--- |
| `s` | `0x73` | Science Burst | $32,768$ bytes (raw little-endian uint16) |
| `v` | `0x76` | Video Burst | $2,048$ bytes (raw little-endian uint16) |

**Note on Resolution:** The RP2040 ADC hardware is 12-bit ($0 \dots 4095$). MicroPython scales this to a 16-bit integer ($0 \dots 65535$). The host-side DSP pipeline handles the conversion to voltage.

## Future Development: DMA Implementation

While the current "native emitter" approach achieves respectable performance ($\approx 100$ kSps), the CPU is still tied up polling the ADC. The next architectural leap involves using the RP2040's **Direct Memory Access (DMA)** controller.

By configuring the ADC FIFO to trigger a DMA channel, samples can be moved directly to RAM without CPU intervention. This would theoretically allow for:
1.  Higher sample rates (up to 500 kSps).
2.  Zero jitter (derived strictly from the crystal oscillator).
3.  Simultaneous processing (CPU free during capture).

*Current status: The native polling loop provides sufficient bandwidth for audio-range spectral analysis (Nyquist $\approx 48$ kHz).*