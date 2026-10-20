from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class StftConfig:
    n_fft: int = 2048
    hop_length: int = 512
    window: str = "hann"

    @property
    def window_array(self) -> np.ndarray:
        return signal.get_window(self.window, self.n_fft)


def stft_channel(
    channel: np.ndarray,
    sample_rate: int,
    config: StftConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Return complex STFT (freq_bins, frames) and frequency bin centers (Hz)."""
    freqs, _times, zxx = signal.stft(
        channel,
        fs=sample_rate,
        nperseg=config.n_fft,
        noverlap=config.n_fft - config.hop_length,
        window=config.window_array,
        boundary="zeros",
        padded=True,
        return_onesided=True,
    )
    return zxx, freqs


def istft_channel(
    zxx: np.ndarray,
    sample_rate: int,
    config: StftConfig,
    length: int,
) -> np.ndarray:
    """Reconstruct time-domain signal with exact sample length."""
    _, audio = signal.istft(
        zxx,
        fs=sample_rate,
        nperseg=config.n_fft,
        noverlap=config.n_fft - config.hop_length,
        window=config.window_array,
        boundary=True,
        time_axis=-1,
        freq_axis=0,
    )
    audio = np.asarray(audio, dtype=np.float64)
    if len(audio) < length:
        audio = np.pad(audio, (0, length - len(audio)))
    elif len(audio) > length:
        audio = audio[:length]
    return audio


def align_length(audio: np.ndarray, length: int) -> np.ndarray:
    if audio.shape[0] == length:
        return audio
    if audio.shape[0] < length:
        pad = length - audio.shape[0]
        return np.pad(audio, ((0, pad), (0, 0)))
    return audio[:length, :]
