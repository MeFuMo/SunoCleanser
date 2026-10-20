from __future__ import annotations

import numpy as np
from scipy import ndimage


MAX_ATTENUATION_DB = 7.0
MIN_GAIN = 10.0 ** (-MAX_ATTENUATION_DB / 20.0)


def band_strength(freqs: np.ndarray, bass_hz: float = 350.0) -> np.ndarray:
    """
    Frequency-dependent reduction strength in [0, 1].
    Below bass_hz: ~0 (minimal processing).
    Mid: conservative. High: stronger for radio-static band.
    """
    strength = np.zeros_like(freqs, dtype=np.float64)
    mid_lo = bass_hz
    mid_hi = 4000.0
    high_end = 16000.0

    mid_mask = (freqs >= mid_lo) & (freqs < mid_hi)
    high_mask = freqs >= mid_hi

    t_mid = (freqs[mid_mask] - mid_lo) / (mid_hi - mid_lo)
    strength[mid_mask] = 0.35 + 0.25 * t_mid

    if np.any(high_mask):
        t_high = np.clip((freqs[high_mask] - mid_hi) / (high_end - mid_hi), 0.0, 1.0)
        strength[high_mask] = 0.55 + 0.45 * t_high

    return strength


def raw_gain_mask(
    magnitude: np.ndarray,
    noise_profile: np.ndarray,
    freqs: np.ndarray,
    oversubtraction: float = 1.2,
    bass_hz: float = 350.0,
) -> np.ndarray:
    """
    Adaptive spectral subtraction gain per bin (freq, time).
    magnitude: mono-linked average magnitude used for mask construction.
    """
    strength = band_strength(freqs, bass_hz=bass_hz)[:, np.newaxis]
    noise = noise_profile[:, np.newaxis]
    signal_est = np.maximum(magnitude - oversubtraction * noise * strength, 0.0)
    ratio = signal_est / (magnitude + 1e-12)
    gain = np.clip(ratio, MIN_GAIN, 1.0)
    bass_mask = freqs < bass_hz
    gain[bass_mask, :] = 1.0
    return gain


def smooth_gain_mask(
    gain: np.ndarray,
    freq_sigma: float = 1.5,
    time_sigma: float = 1.0,
) -> np.ndarray:
    """Gaussian smooth across frequency and time to reduce musical noise."""
    smoothed = ndimage.gaussian_filter(gain, sigma=(freq_sigma, time_sigma), mode="nearest")
    return np.clip(smoothed, MIN_GAIN, 1.0)


def apply_gain_to_spectrum(spectrum: np.ndarray, gain: np.ndarray) -> np.ndarray:
    """Preserve original phase; scale magnitude by gain."""
    return spectrum * gain
