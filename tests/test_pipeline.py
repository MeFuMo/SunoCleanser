from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from src.suno.pipeline import ProcessingParams, process_suno_wav


def test_phase_cancel_matches_denoised(tmp_path: Path) -> None:
    sample_rate = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = 0.4 * np.sin(2 * np.pi * 440 * t)
    noise = 0.05 * np.random.default_rng(0).standard_normal(t.shape)
    stereo = np.column_stack([tone + noise, tone * 0.9 + noise])

    input_wav = tmp_path / "test_input.wav"
    sf.write(input_wav, stereo, sample_rate, subtype="PCM_24")

    result = process_suno_wav(
        input_path=input_wav,
        out_dir=tmp_path,
        title="Test",
        params=ProcessingParams(reconstruction_threshold_db=-40.0),
        report_path=tmp_path / "test.report.json",
    )

    assert result.clean_path.is_file()
    assert result.noise_path.is_file()
    assert result.report["reconstruction_passed"] is True
