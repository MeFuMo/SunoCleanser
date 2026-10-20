from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from src.audio.io import load_wav, peak_levels, write_wav_24bit
from src.audio.stft import StftConfig, align_length, istft_channel, stft_channel
from src.suno.gain_mask import (
    MAX_ATTENUATION_DB,
    apply_gain_to_spectrum,
    raw_gain_mask,
    smooth_gain_mask,
)
from src.suno.noise_profile import estimate_noise_spectrum


@dataclass(frozen=True)
class ProcessingParams:
    n_fft: int = 2048
    hop_length: int = 512
    window: str = "hann"
    quiet_fraction: float = 0.12
    bass_cut_hz: float = 350.0
    oversubtraction: float = 1.2
    freq_smooth_sigma: float = 1.5
    time_smooth_sigma: float = 1.0
    reconstruction_threshold_db: float = -60.0


@dataclass
class ProcessingResult:
    clean_path: Path
    noise_path: Path
    report: dict


def reconstruction_error(clean: np.ndarray, denoised: np.ndarray) -> dict[str, float]:
    diff = clean - denoised
    max_abs = float(np.max(np.abs(diff)))
    rms = float(np.sqrt(np.mean(diff**2)))
    ref = float(np.max(np.abs(denoised))) + 1e-12
    max_rel = max_abs / ref
    rms_rel = rms / ref
    max_db = 20.0 * np.log10(max_rel + 1e-15)
    rms_db = 20.0 * np.log10(rms_rel + 1e-15)
    return {
        "max_abs_error": max_abs,
        "rms_error": rms,
        "max_relative_error": max_rel,
        "rms_relative_error": rms_rel,
        "max_error_db": float(max_db),
        "rms_error_db": float(rms_db),
    }


def process_suno_wav(
    input_path: Path,
    out_dir: Path | None,
    title: str | None,
    params: ProcessingParams | None = None,
    report_path: Path | None = None,
) -> ProcessingResult:
    params = params or ProcessingParams()
    stft_config = StftConfig(
        n_fft=params.n_fft,
        hop_length=params.hop_length,
        window=params.window,
    )

    original, info = load_wav(input_path)
    n_frames = original.shape[0]
    sample_rate = info.sample_rate

    if original.shape[1] == 1:
        left = original[:, 0]
        right = original[:, 0]
    else:
        left = original[:, 0]
        right = original[:, 1]

    spec_l, freqs = stft_channel(left, sample_rate, stft_config)
    spec_r, _ = stft_channel(right, sample_rate, stft_config)

    mag_l = np.abs(spec_l)
    mag_r = np.abs(spec_r)
    mono_mag = (mag_l + mag_r) * 0.5

    noise_profile, n_quiet_frames = estimate_noise_spectrum(
        mag_l,
        mag_r,
        freqs,
        quiet_fraction=params.quiet_fraction,
        bass_cut_hz=params.bass_cut_hz,
    )

    gain = raw_gain_mask(
        mono_mag,
        noise_profile,
        freqs,
        oversubtraction=params.oversubtraction,
        bass_hz=params.bass_cut_hz,
    )
    gain = smooth_gain_mask(
        gain,
        freq_sigma=params.freq_smooth_sigma,
        time_sigma=params.time_smooth_sigma,
    )

    den_spec_l = apply_gain_to_spectrum(spec_l, gain)
    den_spec_r = apply_gain_to_spectrum(spec_r, gain)

    den_left = istft_channel(den_spec_l, sample_rate, stft_config, n_frames)
    den_right = istft_channel(den_spec_r, sample_rate, stft_config, n_frames)

    if original.shape[1] == 1:
        denoised = den_left[:, np.newaxis]
    else:
        denoised = np.column_stack([den_left, den_right])

    denoised = align_length(denoised, n_frames)
    original = align_length(original, n_frames)

    noise_track = original - denoised
    phase_cancelled_clean = original + (-noise_track)

    err = reconstruction_error(phase_cancelled_clean, denoised)
    passed = err["max_error_db"] <= params.reconstruction_threshold_db

    song_title = title or input_path.stem
    destination = out_dir if out_dir is not None else input_path.parent
    destination.mkdir(parents=True, exist_ok=True)

    clean_name = f"{song_title} - Phase Cancelled Clean.wav"
    noise_name = f"{song_title} - Removed Noise.wav"
    clean_path = destination / clean_name
    noise_path = destination / noise_name

    write_wav_24bit(clean_path, phase_cancelled_clean, sample_rate)
    write_wav_24bit(noise_path, noise_track, sample_rate)

    peaks_clean = peak_levels(phase_cancelled_clean)
    peaks_noise = peak_levels(noise_track)
    clip_warning = (
        peaks_clean["peak_l"] > 1.0
        or peaks_clean["peak_r"] > 1.0
        or peaks_noise["peak_l"] > 1.0
        or peaks_noise["peak_r"] > 1.0
    )

    report = {
        "input": input_path.name,
        "sample_rate": sample_rate,
        "channels": info.channels,
        "duration_seconds": n_frames / sample_rate,
        "processing_parameters": {
            **asdict(params),
            "max_attenuation_db": MAX_ATTENUATION_DB,
            "stereo_mode": "linked_noise_profile_shared_gain",
            "quiet_frames_used": n_quiet_frames,
            "quiet_fraction": params.quiet_fraction,
        },
        "output_peaks": {
            "phase_cancelled_clean": peaks_clean,
            "removed_noise": peaks_noise,
        },
        "reconstruction": err,
        "reconstruction_passed": passed,
        "reconstruction_threshold_db": params.reconstruction_threshold_db,
        "clip_warning": clip_warning,
        "outputs": {
            "phase_cancelled_clean": clean_path.name,
            "removed_noise": noise_path.name,
        },
    }

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not passed:
        raise RuntimeError(
            "Phase-cancel verification failed: "
            f"max_error_db={err['max_error_db']:.2f} "
            f"(threshold {params.reconstruction_threshold_db} dB). "
            "Outputs were written for inspection."
        )

    return ProcessingResult(clean_path=clean_path, noise_path=noise_path, report=report)
