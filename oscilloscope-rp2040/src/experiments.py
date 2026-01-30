import time

import numpy as np
import sounddevice as sd

from . import audio, config, daq, diagnostics, dsp, io, plots


def capture_sweep_transfer(
    f_start, f_end, duration, amp, fs_audio=48000, prefix="sweep", notes=""
):
    """
    Orchestrates a Transfer Function Sweep.
    Saves RAW uint16 data to save space, but calculates Voltage metadata.
    """
    print(f"🔹 Generating Sweep ({f_start}-{f_end}Hz, {duration}s)...")
    wave = audio.generate_log_sweep(f_start, f_end, duration, fs_audio, amp)

    frames = []

    print("🔴 Starting Capture...")
    with daq.DAQInterface() as device:
        # Start Audio (Non-blocking)
        sd.play(wave, samplerate=fs_audio, blocking=False)
        start_time = time.time()

        # Capture loop (Continuous Stream)
        for chunk in device.stream_generator():
            frames.append(chunk)

            if not sd.get_stream().active:
                break

            if (time.time() - start_time) > (duration + 2.0):
                print("⚠️ Timeout reached.")
                break

    print("💾 Saving Capture...")
    full_array_raw = np.concatenate(frames)

    # --- METRICS CALCULATION ---
    # Convert to volts temporarily for stats (RAM efficient enough for <10s clips)
    volts = dsp.raw_to_volts(full_array_raw)
    v_mean = np.mean(volts)
    v_max = np.max(volts)
    v_min = np.min(volts)
    peak_amp = np.max(np.abs(volts - v_mean))

    # Check saturation (clipping)
    is_healthy = diagnostics.check_signal_health(volts)

    return io.save_signal(
        full_array_raw,
        config.FS_DEFAULT,
        config.DATA_DIR_CONTINUOUS,
        prefix=prefix,
        # Experiment Config
        audio_type="sweep",
        f_start=f_start,
        f_end=f_end,
        duration=duration,
        amp=amp,
        # Rich Metadata
        v_ref=config.V_REF,
        adc_bits=config.ADC_BITS,
        v_min=v_min,
        v_max=v_max,
        dc_offset=v_mean,
        clipped=(not is_healthy),
        peak_voltage=peak_amp,
        user_notes=notes,
    )


def capture_steady_transfer(
    shape, freq, amp, duration_buffer=0.5, prefix="steady", notes=""
):
    """
    Orchestrates a Steady-State Transfer Capture with Sanity Checks.
    Saves FLOAT voltage data (standard for bursts).
    """
    print(f"🔹 Starting Oscillator ({shape} @ {freq}Hz)...")

    with audio.ContinuousOscillator(shape, freq, amp) as _:
        time.sleep(duration_buffer)

        print("📸 Capturing Burst...")
        with daq.DAQInterface() as device:
            raw = device.capture_burst()
            volts = dsp.raw_to_volts(raw)

            # --- DIAGNOSTICS & METRICS ---
            is_healthy = diagnostics.check_signal_health(volts)
            dom_freq, _ = diagnostics.analyze_spectrum_peaks(volts, config.FS_DEFAULT)

            v_mean = np.mean(volts)
            v_max = np.max(volts)
            v_min = np.min(volts)
            peak_amp = np.max(np.abs(volts - v_mean))

            # Save
            path = io.save_signal(
                volts,
                config.FS_DEFAULT,
                config.DATA_DIR_BURST,
                prefix=prefix,
                # Experiment Config
                audio_type="steady",
                shape=shape,
                freq=freq,
                amp=amp,
                # Rich Metadata
                measured_freq=dom_freq,
                v_ref=config.V_REF,
                adc_bits=config.ADC_BITS,
                v_min=v_min,
                v_max=v_max,
                dc_offset=v_mean,
                clipped=(not is_healthy),
                peak_voltage=peak_amp,
                user_notes=notes,
            )

            # Plot
            title = f"{prefix} (Meas: {dom_freq:.1f}Hz)"
            plots.plot_health_check(volts, config.FS_DEFAULT, title, is_healthy)
            return path


def capture_instrument_clip(filename, notes=""):
    """
    Manual instrument capture (Guitar, Bass, etc) for Notebook 01.
    """
    print(f"🔴 Recording Instrument: '{filename}' ...")

    with daq.DAQInterface() as device:
        raw = device.capture_burst()
        volts = dsp.raw_to_volts(raw)

        # --- DIAGNOSTICS & METRICS ---
        is_healthy = diagnostics.check_signal_health(volts)
        dom_freq, harmonics = diagnostics.analyze_spectrum_peaks(
            volts, config.FS_DEFAULT
        )

        v_mean = np.mean(volts)
        peak_amp = np.max(np.abs(volts - v_mean))

        # --- SAVE ---
        path = io.save_signal(
            volts,
            config.FS_DEFAULT,
            config.DATA_DIR_BURST,
            prefix=filename,
            v_ref=config.V_REF,
            adc_bits=config.ADC_BITS,
            v_min=np.min(volts),
            v_max=np.max(volts),
            dc_offset=v_mean,
            clipped=(not is_healthy),
            peak_voltage=peak_amp,
            dominant_freq=dom_freq,
            user_notes=notes,
        )

        # --- PLOT ---
        title = f"{filename} (Pitch: {dom_freq:.1f} Hz)"
        diagnostics.plot_health_check(volts, config.FS_DEFAULT, title, is_healthy)

        return path


def capture_continuous_stream(prefix="session"):
    """
    Captures data indefinitely until KeyboardInterrupt.
    Moved from scripts/capture/stream.py.
    """
    frames = []
    start_time = time.time()

    # Calculate approx data rate for user info
    bytes_per_sec = config.LIVE_SAMPLES * 2 * (config.FS_DEFAULT / config.LIVE_SAMPLES)
    mb_per_min = (bytes_per_sec * 60) / (1024 * 1024)

    print("🔴 RECORDING STREAM... Press Ctrl+C to stop.")
    print(f"   (Approx Data Rate: ~{mb_per_min:.2f} MB/min)")

    try:
        with daq.DAQInterface() as device:
            # We iterate over the generator. It yields chunks indefinitely.
            for chunk_u16 in device.stream_generator():
                frames.append(chunk_u16)

                # Feedback every 100 frames
                if len(frames) % 100 == 0:
                    duration = time.time() - start_time
                    print(f"   Captured {len(frames)} frames ({duration:.1f}s)...")

    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

    if not frames:
        print("No data captured.")
        return

    print("Processing...")
    full_array = np.concatenate(frames)

    io.save_signal(
        full_array, config.FS_DEFAULT, config.DATA_DIR_CONTINUOUS, prefix=prefix
    )
