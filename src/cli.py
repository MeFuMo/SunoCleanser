from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.settings import load_settings
from src.suno.params import BUILTIN_PRESETS, DEFAULT_PRESET, PARAM_SPECS, ProcessingParams, preset_params
from src.suno.pipeline import process_suno_wav

# Short aliases kept from v1.
FLAG_ALIASES = {"hop_length": ["--hop"]}


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suno-clean",
        description="Suno adaptive spectral denoise with phase-cancel verification.",
    )
    parser.add_argument("input_wav", type=Path, nargs="*", help="Source audio file(s)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: same folder as input)",
    )
    parser.add_argument("--title", type=str, default=None, help="Song title for output filenames (single input only)")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON processing report to this path (single input only)",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        help="Built-in (%s) or a custom preset saved from the GUI. Flags below override it."
        % ", ".join(BUILTIN_PRESETS),
    )
    parser.add_argument("--list-presets", action="store_true", help="Print presets and exit")

    group = parser.add_argument_group("processing parameters (override the preset)")
    for spec in PARAM_SPECS:
        flags = [_flag(spec.name)] + FLAG_ALIASES.get(spec.name, [])
        default_value = getattr(ProcessingParams(), spec.name)
        kwargs: Dict[str, Any] = {"dest": spec.name, "default": None}
        if spec.choices is not None:
            kwargs["type"] = type(spec.choices[0])
            kwargs["choices"] = spec.choices
            kwargs["help"] = f"default {default_value}"
        else:
            kwargs["type"] = float
            kwargs["help"] = f"{spec.minimum:g}..{spec.maximum:g}, default {default_value:g}"
            if spec.name == "top_protect_hz":
                kwargs["help"] += " (0 = off)"
        group.add_argument(*flags, **kwargs)
    return parser


def resolve_params(args: argparse.Namespace, custom: Dict[str, Dict[str, Any]]) -> ProcessingParams:
    base = preset_params(args.preset, custom)
    overrides = {spec.name: getattr(args, spec.name) for spec in PARAM_SPECS}
    return ProcessingParams.from_dict(overrides, base=base).validate()


def _default_report(input_path: Path, out_dir: Optional[Path]) -> Path:
    folder = out_dir if out_dir is not None else input_path.parent
    return folder / f"{input_path.stem}.report.json"


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    custom = load_settings().get("custom_presets", {})

    if args.list_presets:
        for name, values in BUILTIN_PRESETS.items():
            print(f"{name}: {json.dumps(values)}")
        for name, values in custom.items():
            print(f"{name} (custom): {json.dumps(values)}")
        return 0

    inputs: List[Path] = args.input_wav
    if not inputs:
        parser.error("at least one input file is required")
    if len(inputs) > 1 and (args.title or args.report):
        parser.error("--title and --report only apply to a single input")

    try:
        params = resolve_params(args, custom)
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    exit_code = 0
    for input_path in inputs:
        if not input_path.is_file():
            print(f"Error: input file not found: {input_path}", file=sys.stderr)
            exit_code = exit_code or 1
            continue
        report_path = args.report or _default_report(input_path, args.out_dir)
        try:
            result = process_suno_wav(
                input_path=input_path,
                out_dir=args.out_dir,
                title=args.title,
                params=params,
                report_path=report_path,
            )
        except ImportError as exc:
            print(
                "Error: required audio libraries are not available. "
                "Activate conda env `sunocleanser` and install dependencies.",
                file=sys.stderr,
            )
            print(exc, file=sys.stderr)
            return 2
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            print(json.dumps({"report_path": str(report_path)}, indent=2))
            exit_code = exit_code or 3
            continue
        except Exception as exc:
            print(f"Processing failed for {input_path.name}: {exc}", file=sys.stderr)
            exit_code = exit_code or 4
            continue

        if len(inputs) == 1:
            print(json.dumps(result.report, indent=2))
        else:
            removal = ", ".join(f"{k} {v:+.2f}" for k, v in result.report["band_removal_db"].items())
            print(f"{input_path.name}: {removal} dB")
        print(f"Wrote: {result.clean_path}")
        print(f"Wrote: {result.noise_path}")
        print(f"Report: {report_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
