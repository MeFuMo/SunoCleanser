from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class WavInfo:
    sample_rate: int
    channels: int
    subtype: str
    frames: int


def load_wav(path: Path) -> tuple[np.ndarray, WavInfo]:
    """Load WAV as float64, shape (frames, channels). Preserves channel layout."""
    data, sample_rate = sf.read(path, dtype="float64", always_2d=True)
    with sf.SoundFile(path) as f:
        info = WavInfo(
            sample_rate=int(sample_rate),
            channels=int(f.channels),
            subtype=str(f.subtype),
            frames=int(len(f)),
        )
    return data, info


def write_wav_24bit(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    """Write PCM_24 WAV without normalization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sample_rate, subtype="PCM_24")


def peak_levels(audio: np.ndarray) -> dict[str, float]:
    peaks = np.max(np.abs(audio), axis=0)
    if peaks.size == 1:
        return {"peak_l": float(peaks[0]), "peak_r": float(peaks[0])}
    return {"peak_l": float(peaks[0]), "peak_r": float(peaks[1])}
