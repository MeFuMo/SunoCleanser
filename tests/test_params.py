from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.cli import build_parser, resolve_params
from src.gui.i18n import STRINGS
from src.settings import load_settings, save_settings
from src.suno.gain_mask import band_strength
from src.suno.params import BUILTIN_PRESETS, PARAM_SPECS, ProcessingParams, preset_params
from src.suno.pipeline import process_suno_wav


def _noisy_stereo(path: Path, seconds: float = 2.0, sr: int = 44100) -> Path:
    t = np.arange(int(sr * seconds)) / sr
    rng = np.random.default_rng(1)
    tone = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 9000 * t)
    hiss = 0.03 * rng.standard_normal((t.size, 2))
    sf.write(path, np.column_stack([tone, tone]) + hiss, sr, subtype="PCM_24")
    return path


def test_all_presets_valid() -> None:
    for name in BUILTIN_PRESETS:
        preset_params(name).validate()


def test_defaults_match_v1() -> None:
    p = ProcessingParams()
    assert (p.n_fft, p.hop_length, p.quiet_fraction, p.bass_cut_hz) == (2048, 512, 0.12, 350.0)
    assert (p.oversubtraction, p.max_attenuation_db, p.mix, p.top_protect_hz) == (1.2, 7.0, 1.0, 0.0)


def test_validation_rejects_bad_values() -> None:
    with pytest.raises(ValueError, match="hop_length"):
        ProcessingParams(n_fft=1024, hop_length=1024).validate()
    with pytest.raises(ValueError, match="mix"):
        ProcessingParams(mix=1.5).validate()
    with pytest.raises(ValueError, match="high_peak_hz"):
        ProcessingParams(mid_split_hz=9000, high_peak_hz=8000).validate()


def test_from_dict_ignores_unknown_and_coerces() -> None:
    p = ProcessingParams.from_dict({"n_fft": "4096", "mix": "0.5", "bogus": 1})
    assert p.n_fft == 4096 and p.mix == 0.5


def test_band_strength_multipliers_and_top_protection() -> None:
    freqs = np.linspace(0, 22050, 1025)
    base = band_strength(freqs)
    half_high = band_strength(freqs, high_band_strength=0.5)
    hi = freqs >= 4000
    assert np.allclose(half_high[hi], base[hi] * 0.5)
    assert np.allclose(half_high[~hi], base[~hi])
    protected = band_strength(freqs, top_protect_hz=12000)
    assert np.all(protected[freqs >= 12000] == 0)
    assert np.allclose(protected[freqs < 9000], base[freqs < 9000])


def test_mix_zero_is_bypass(tmp_path: Path) -> None:
    wav = _noisy_stereo(tmp_path / "in.wav")
    result = process_suno_wav(wav, tmp_path, "bypass", ProcessingParams(mix=0.0))
    original, _ = sf.read(wav)
    clean, _ = sf.read(result.clean_path)
    assert np.max(np.abs(original - clean)) < 1e-5
    assert all(v == 0.0 for v in result.report["band_removal_db"].values())


def test_top_protection_keeps_highs(tmp_path: Path) -> None:
    wav = _noisy_stereo(tmp_path / "in.wav")
    full = process_suno_wav(wav, tmp_path, "full", ProcessingParams())
    kept = process_suno_wav(wav, tmp_path, "kept", ProcessingParams(top_protect_hz=12000))
    assert full.report["band_removal_db"]["16k+"] < -0.5
    assert kept.report["band_removal_db"]["16k+"] == 0.0


def test_gentler_presets_remove_less_top_end(tmp_path: Path) -> None:
    wav = _noisy_stereo(tmp_path / "in.wav")
    top = {}
    for name in ("strong", "original", "gentle", "transparent"):
        top[name] = process_suno_wav(wav, tmp_path, name, preset_params(name)).report["band_removal_db"]["12k-16k"]
    assert top["strong"] < top["original"] < top["gentle"] < top["transparent"] <= 0.0


def test_cli_flags_override_preset() -> None:
    args = build_parser().parse_args(["x.wav", "--preset", "gentle", "--high-band-strength", "0.3", "--hop", "256"])
    p = resolve_params(args, {})
    assert p.high_band_strength == 0.3 and p.hop_length == 256
    assert p.max_attenuation_db == BUILTIN_PRESETS["gentle"]["max_attenuation_db"]


def test_every_param_has_cli_flag() -> None:
    parser = build_parser()
    dests = {a.dest for a in parser._actions}
    assert {s.name for s in PARAM_SPECS} <= dests


def test_i18n_keys_match() -> None:
    assert set(STRINGS["en"]) == set(STRINGS["es"])
    for spec in PARAM_SPECS:
        if spec.gui:
            assert "p." + spec.name in STRINGS["en"]
            assert "tip." + spec.name in STRINGS["en"]
    for name in BUILTIN_PRESETS:
        assert "preset." + name in STRINGS["en"]


def test_settings_roundtrip_and_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    data = load_settings(path)
    data.update(language="es", custom_presets={"mine": {"mix": 0.4}})
    assert save_settings(data, path)
    again = load_settings(path)
    assert again["language"] == "es" and again["custom_presets"]["mine"]["mix"] == 0.4
    path.write_text("{not json", encoding="utf-8")
    assert load_settings(path)["preset"] == "original"
