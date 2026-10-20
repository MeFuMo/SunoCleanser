from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.suno.pipeline import ProcessingParams, process_suno_wav


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suno-clean",
        description="Suno adaptive spectral denoise with phase-cancel verification.",
    )
    parser.add_argument("input_wav", type=Path, help="Source WAV file")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: same folder as input)",
    )
    parser.add_argument("--title", type=str, default=None, help="Song title for output filenames")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON processing report to this path",
    )
    parser.add_argument("--n-fft", type=int, default=2048)
    parser.add_argument("--hop", type=int, default=512)
    parser.add_argument("--quiet-fraction", type=float, default=0.12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path: Path = args.input_wav

    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    report_path = args.report
    if report_path is None and args.out_dir is not None:
        report_path = args.out_dir / f"{input_path.stem}.report.json"
    elif report_path is None:
        report_path = input_path.parent / f"{input_path.stem}.report.json"

    params = ProcessingParams(
        n_fft=args.n_fft,
        hop_length=args.hop,
        quiet_fraction=args.quiet_fraction,
    )

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
        return 3
    except Exception as exc:
        print(f"Processing failed: {exc}", file=sys.stderr)
        return 4

    print(json.dumps(result.report, indent=2))
    print(f"Wrote: {result.clean_path}")
    print(f"Wrote: {result.noise_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
