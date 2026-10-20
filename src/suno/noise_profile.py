from __future__ import annotations

import numpy as np


def frame_quiet_scores(
    magnitude_l: np.ndarray,
    magnitude_r: np.ndarray,
    freqs: np.ndarray,
    bass_cut_hz: float = 350.0,
) -> np.ndarray:
    """
    Per-frame energy from mono-linked magnitudes, ignoring bins below bass_cut_hz
    so kick/bass do not dominate quiet-frame selection.
    """
    mono_mag = (magnitude_l + magnitude_r) * 0.5
    bass_mask = freqs < bass_cut_hz
    if np.all(bass_mask):
        band_mag = mono_mag
    else:
        band_mag = mono_mag[~bass_mask, :]
    return np.mean(band_mag**2, axis=0)


def estimate_noise_spectrum(
    magnitude_l: np.ndarray,
    magnitude_r: np.ndarray,
    freqs: np.ndarray,
    quiet_fraction: float = 0.12,
    bass_cut_hz: float = 350.0,
) -> tuple[np.ndarray, int]:
    """
    Average magnitude spectrum over the quietest fraction of frames (linked stereo).
    Returns noise profile (freq_bins,) and count of frames used.
    """
    scores = frame_quiet_scores(magnitude_l, magnitude_r, freqs, bass_cut_hz)
    n_frames = scores.shape[0]
    n_quiet = max(1, int(np.ceil(n_frames * quiet_fraction)))
    quiet_idx = np.argpartition(scores, n_quiet - 1)[:n_quiet]
    mono_mag = (magnitude_l + magnitude_r) * 0.5
    noise_profile = np.mean(mono_mag[:, quiet_idx], axis=1)
    noise_floor = np.max(noise_profile) * 1e-6 + 1e-12
    noise_profile = np.maximum(noise_profile, noise_floor)
    return noise_profile, n_quiet
