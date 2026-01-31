import time

import numpy as np
import sounddevice as sd

from . import audio, config, daq, diagnostics, dsp, io, plots


def capture_sweep_transfer(
    f_start: float,
    f_end: float,
    duration: float,
    amp: float,
    fs_audio: int = 48000,
    prefix: str = "sweep",
    notes: str = "",
) -> str:
    """
    Orchestrates a Transfer Function Sweep experiment.

    Generates a logarithmic sine sweep, plays it via the system audio output,
    and simultaneously captures the response via the DAQ. It automatically
    calculates signal metrics and saves the raw data to disk.

    Parameters
    ----------
    f_start : float
        Starting frequency in Hz.
    f_end : float
        Ending frequency in Hz.
    duration : float
        Duration of the sweep in seconds.
    amp : float
        Amplitude of the output sweep (0.0 to 1.0).
    fs_audio : int, optional
        Sample rate for the audio output (default 48000).
    prefix : str, optional
        Filename prefix for the saved data.
    notes : str, optional
        User notes to attach to the metadata.

    Returns
    -------
    str
        The file path of the saved dataset.
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
        v_min=float(v_min),
        v_max=float(v_max),
        dc_offset=float(v_mean),
        clipped=(not is_healthy),
        peak_voltage=float(peak_amp),
        user_notes=notes,
    )


def capture_steady_transfer(
    shape: str,
    freq: float,
    amp: float,
    duration_buffer: float = 0.5,
    prefix: str = "steady",
    notes: str = "",
) -> str:
    """
    Orchestrates a Steady-State Transfer Capture with sanity checks.

    Plays a continuous tone (oscillator) and captures a fixed-length burst
    from the DAQ. Performs immediate spectral analysis and plotting.

    Parameters
    ----------
    shape : str
        Waveform shape ('sine', 'square', etc.).
    freq : float
        Frequency of the oscillator in Hz.
    amp : float
        Amplitude of the oscillator (0.0 to 1.0).
    duration_buffer : float, optional
        Time in seconds to wait before capturing to allow signal stabilization.
    prefix : str, optional
        Filename prefix for saved data.
    notes : str, optional
        User notes to attach to metadata.

    Returns
    -------
    str
        The file path of the saved dataset.
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
                v_min=float(v_min),
                v_max=float(v_max),
                dc_offset=float(v_mean),
                clipped=(not is_healthy),
                peak_voltage=float(peak_amp),
                user_notes=notes,
            )

            # Plot
            title = f"{prefix} (Meas: {dom_freq:.1f}Hz)"
            plots.plot_health_check(volts, config.FS_DEFAULT, title, is_healthy)
            return path


def capture_instrument_clip(filename: str, notes: str = "") -> str:
    """
    Captures a manual instrument input (e.g., Guitar, Bass).

    Parameters
    ----------
    filename : str
        The specific filename/prefix to use for saving.
    notes : str, optional
        User notes to attach to metadata.

    Returns
    -------
    str
        The file path of the saved dataset.
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
            v_min=float(np.min(volts)),
            v_max=float(np.max(volts)),
            dc_offset=float(v_mean),
            clipped=(not is_healthy),
            peak_voltage=float(peak_amp),
            dominant_freq=dom_freq,
            user_notes=notes,
        )

        # --- PLOT ---
        title = f"{filename} (Pitch: {dom_freq:.1f} Hz)"
        # Fixed: Usage of diagnostics.plot_health_check -> plots.plot_health_check
        plots.plot_health_check(volts, config.FS_DEFAULT, title, is_healthy)

        return path


def capture_continuous_stream(prefix: str = "session") -> None:
    """
    Captures data indefinitely until KeyboardInterrupt.

    Designed for long-running captures. Data is accumulated in memory
    and saved only upon stopping the stream via Ctrl+C.

    Parameters
    ----------
    prefix : str, optional
        Filename prefix for the saved data.
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
