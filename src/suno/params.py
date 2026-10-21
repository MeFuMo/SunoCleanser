"""
Processing parameters, their valid ranges, and presets.

PARAM_SPECS is the single source of truth for ranges/steps; the CLI and GUI
both build their controls from it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProcessingParams:
    # STFT
    n_fft: int = 2048
    hop_length: int = 512
    window: str = "hann"
    # Noise profile
    quiet_fraction: float = 0.12
    bass_cut_hz: float = 350.0
    # Gain mask
    oversubtraction: float = 1.2
    max_attenuation_db: float = 7.0
    mid_band_strength: float = 1.0
    high_band_strength: float = 1.0
    mid_split_hz: float = 4000.0
    high_peak_hz: float = 16000.0
    top_protect_hz: float = 0.0  # 0 = off
    mix: float = 1.0
    freq_smooth_sigma: float = 1.5
    time_smooth_sigma: float = 1.0
    # Verification
    reconstruction_threshold_db: float = -60.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base: Optional["ProcessingParams"] = None) -> "ProcessingParams":
        """Build from a (possibly partial) dict; unknown keys are ignored, values coerced."""
        base = base or cls()
        known = {f.name: f for f in fields(cls)}
        updates: Dict[str, Any] = {}
        for key, value in data.items():
            if key not in known or value is None:
                continue
            default = getattr(base, key)
            if isinstance(default, bool):
                updates[key] = bool(value)
            elif isinstance(default, int):
                updates[key] = int(round(float(value)))
            elif isinstance(default, float):
                updates[key] = float(value)
            else:
                updates[key] = str(value)
        return replace(base, **updates)

    def validate(self) -> "ProcessingParams":
        """Raise ValueError listing every problem; returns self for chaining."""
        problems: List[str] = []
        for spec in PARAM_SPECS:
            value = getattr(self, spec.name)
            if spec.choices is not None:
                if value not in spec.choices:
                    problems.append(f"{spec.name}={value} must be one of {list(spec.choices)}")
            elif not (spec.minimum <= value <= spec.maximum):
                problems.append(f"{spec.name}={value} outside [{spec.minimum}, {spec.maximum}]")
        if self.hop_length > self.n_fft // 2:
            problems.append(f"hop_length={self.hop_length} must be <= n_fft/2 ({self.n_fft // 2})")
        if self.high_peak_hz <= self.mid_split_hz:
            problems.append("high_peak_hz must be greater than mid_split_hz")
        if self.mid_split_hz <= self.bass_cut_hz:
            problems.append("mid_split_hz must be greater than bass_cut_hz")
        if 0 < self.top_protect_hz <= self.bass_cut_hz:
            problems.append("top_protect_hz must be 0 (off) or greater than bass_cut_hz")
        if problems:
            raise ValueError("Invalid processing parameters: " + "; ".join(problems))
        return self


@dataclass(frozen=True)
class ParamSpec:
    name: str
    minimum: float = 0.0
    maximum: float = 1.0
    step: float = 0.01
    choices: Optional[Tuple[Any, ...]] = None
    unit: str = ""
    advanced: bool = False
    gui: bool = True


PARAM_SPECS: Tuple[ParamSpec, ...] = (
    ParamSpec("mix", 0.0, 1.0, 0.01, unit="%"),
    ParamSpec("max_attenuation_db", 0.5, 24.0, 0.5, unit="dB"),
    ParamSpec("oversubtraction", 0.0, 4.0, 0.05),
    ParamSpec("high_band_strength", 0.0, 2.0, 0.05),
    ParamSpec("mid_band_strength", 0.0, 2.0, 0.05),
    ParamSpec("top_protect_hz", 0.0, 24000.0, 250.0, unit="Hz"),
    ParamSpec("bass_cut_hz", 0.0, 2000.0, 10.0, unit="Hz"),
    ParamSpec("quiet_fraction", 0.01, 0.5, 0.01, unit="%", advanced=True),
    ParamSpec("mid_split_hz", 500.0, 12000.0, 100.0, unit="Hz", advanced=True),
    ParamSpec("high_peak_hz", 2000.0, 24000.0, 250.0, unit="Hz", advanced=True),
    ParamSpec("freq_smooth_sigma", 0.0, 10.0, 0.1, advanced=True),
    ParamSpec("time_smooth_sigma", 0.0, 10.0, 0.1, advanced=True),
    ParamSpec("n_fft", choices=(512, 1024, 2048, 4096, 8192), advanced=True),
    ParamSpec("hop_length", choices=(128, 256, 512, 1024, 2048, 4096), advanced=True),
    ParamSpec("window", choices=("hann", "hamming", "blackman"), advanced=True, gui=False),
    ParamSpec("reconstruction_threshold_db", -200.0, 0.0, 1.0, unit="dB", advanced=True, gui=False),
)

SPEC_BY_NAME: Dict[str, ParamSpec] = {s.name: s for s in PARAM_SPECS}


# Built-in presets: partial overrides on top of the defaults.
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    # v1 behaviour, unchanged.
    "original": {},
    # Same character, lighter touch, no downward tilt: highs lose no more than mids.
    "gentle": {
        "oversubtraction": 1.0,
        "max_attenuation_db": 5.0,
        "high_band_strength": 0.55,
    },
    # Barely-there cleanup; top octave left alone.
    "transparent": {
        "oversubtraction": 0.9,
        "max_attenuation_db": 4.0,
        "high_band_strength": 0.6,
        "mid_band_strength": 0.8,
        "top_protect_hz": 15000.0,
        "mix": 0.8,
    },
    # Harder on hiss for very fizzy generations.
    "strong": {
        "oversubtraction": 1.5,
        "max_attenuation_db": 10.0,
        "high_band_strength": 1.2,
    },
}

DEFAULT_PRESET = "original"


def preset_params(name: str, custom: Optional[Dict[str, Dict[str, Any]]] = None) -> ProcessingParams:
    """Resolve a built-in or custom preset name to full params."""
    if name in BUILTIN_PRESETS:
        return ProcessingParams.from_dict(BUILTIN_PRESETS[name])
    if custom and name in custom:
        return ProcessingParams.from_dict(custom[name])
    raise KeyError(f"Unknown preset: {name}")
