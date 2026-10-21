from __future__ import annotations

import numpy as np
from scipy import ndimage


MAX_ATTENUATION_DB = 7.0
MIN_GAIN = 10.0 ** (-MAX_ATTENUATION_DB / 20.0)

# Base strength curve (shape of the original v1 algorithm). The *_band_strength
# multipliers scale these; 1.0 reproduces v1 exactly.
LOW_MID_BASE = 0.35  # strength at bass_hz
MID_TOP_BASE = 0.60  # strength approaching mid_split_hz
HIGH_START_BASE = 0.55  # strength at mid_split_hz
HIGH_PEAK_BASE = 1.00  # strength at high_peak_hz and above

# Width of the fade below top_protect_hz, in octaves.
TOP_PROTECT_FADE_OCTAVES = 1.0 / 3.0


def min_gain_from_db(max_attenuation_db: float) -> float:
    return float(10.0 ** (-max_attenuation_db / 20.0))


def top_protection_taper(freqs: np.ndarray, top_protect_hz: float) -> np.ndarray:
    """
    1.0 below the fade, 0.0 at and above top_protect_hz, raised-cosine in between.
    top_protect_hz <= 0 disables protection (all ones).
    """
    taper = np.ones_like(freqs, dtype=np.float64)
    if top_protect_hz <= 0:
        return taper
    fade_start = top_protect_hz / (2.0 ** TOP_PROTECT_FADE_OCTAVES)
    above = freqs >= top_protect_hz
    fade = (freqs > fade_start) & ~above
    t = (freqs[fade] - fade_start) / (top_protect_hz - fade_start)
    taper[fade] = 0.5 * (1.0 + np.cos(np.pi * t))
    taper[above] = 0.0
    return taper


def band_strength(
    freqs: np.ndarray,
    bass_hz: float = 350.0,
    mid_split_hz: float = 4000.0,
    high_peak_hz: float = 16000.0,
    mid_band_strength: float = 1.0,
    high_band_strength: float = 1.0,
    top_protect_hz: float = 0.0,
) -> np.ndarray:
    """
    Frequency-dependent reduction strength.
    Below bass_hz: 0 (untouched). Mid band ramps 0.35 -> 0.60, high band ramps
    0.55 -> 1.0 up to high_peak_hz; each band is scaled by its multiplier.
    Optional top-end protection fades strength to 0 at top_protect_hz.
    """
    strength = np.zeros_like(freqs, dtype=np.float64)
    mid_lo = bass_hz
    mid_hi = max(mid_split_hz, mid_lo + 1.0)
    high_end = max(high_peak_hz, mid_hi + 1.0)

    mid_mask = (freqs >= mid_lo) & (freqs < mid_hi)
    high_mask = freqs >= mid_hi

    t_mid = (freqs[mid_mask] - mid_lo) / (mid_hi - mid_lo)
    strength[mid_mask] = (LOW_MID_BASE + (MID_TOP_BASE - LOW_MID_BASE) * t_mid) * mid_band_strength

    if np.any(high_mask):
        t_high = np.clip((freqs[high_mask] - mid_hi) / (high_end - mid_hi), 0.0, 1.0)
        base = HIGH_START_BASE + (HIGH_PEAK_BASE - HIGH_START_BASE) * t_high
        strength[high_mask] = base * high_band_strength

    return strength * top_protection_taper(freqs, top_protect_hz)


def raw_gain_mask(
    magnitude: np.ndarray,
    noise_profile: np.ndarray,
    freqs: np.ndarray,
    oversubtraction: float = 1.2,
    bass_hz: float = 350.0,
    min_gain: float = MIN_GAIN,
    strength: np.ndarray | None = None,
) -> np.ndarray:
    """
    Adaptive spectral subtraction gain per bin (freq, time).
    magnitude: mono-linked average magnitude used for mask construction.
    strength: per-bin strength curve; defaults to band_strength(freqs, bass_hz).
    """
    if strength is None:
        strength = band_strength(freqs, bass_hz=bass_hz)
    noise = noise_profile[:, np.newaxis]
    signal_est = np.maximum(magnitude - oversubtraction * noise * strength[:, np.newaxis], 0.0)
    ratio = signal_est / (magnitude + 1e-12)
    gain = np.clip(ratio, min_gain, 1.0)
    gain[freqs < bass_hz, :] = 1.0
    return gain


def smooth_gain_mask(
    gain: np.ndarray,
    freq_sigma: float = 1.5,
    time_sigma: float = 1.0,
    min_gain: float = MIN_GAIN,
) -> np.ndarray:
    """Gaussian smooth across frequency and time to reduce musical noise."""
    if freq_sigma > 0 or time_sigma > 0:
        gain = ndimage.gaussian_filter(gain, sigma=(freq_sigma, time_sigma), mode="nearest")
    return np.clip(gain, min_gain, 1.0)


def apply_mix(gain: np.ndarray, mix: float) -> np.ndarray:
    """Wet/dry in the gain domain: mix=1 full effect, mix=0 bypass."""
    if mix >= 1.0:
        return gain
    return 1.0 - mix * (1.0 - gain)


def protect_top(gain: np.ndarray, freqs: np.ndarray, top_protect_hz: float) -> np.ndarray:
    """Force unity gain at and above top_protect_hz (smoothing bleeds across the edge)."""
    if top_protect_hz <= 0:
        return gain
    gain = gain.copy()
    gain[freqs >= top_protect_hz, :] = 1.0
    return gain


def apply_gain_to_spectrum(spectrum: np.ndarray, gain: np.ndarray) -> np.ndarray:
    """Preserve original phase; scale magnitude by gain."""
    return spectrum * gain
