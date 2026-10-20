# sunocleanser

**Language:** [Español](README.md) · [English](README.en.md)

Cleans Suno WAV exports with adaptive spectral denoise, phase-cancel verification, and two 24-bit output files.

Uses a process as posted in Reddit by u/Cookienomster45. May your god keep you in any kind of eternal feast of heroes.

**GUI** (tkinter) on Windows and **CLI** for scripts or automation. DSP lives in `process_suno_wav()`; the UI does not duplicate processing logic.

## Requirements

- Windows (GUI tested there; CLI on any OS with Python 3.11+)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda

## Installation

```powershell
cd D:\progs\sunocleanser
conda env create -f environment.yml
conda activate sunocleanser
```

After changes to `environment.yml`:

```powershell
conda env update -f environment.yml --prune
```

Optional, with the environment active:

```powershell
pip install -e .
```

This installs the `sunocleanser-gui` command (same as `python -m src.gui`).

## Quick start (GUI)

1. Create the `sunocleanser` environment (once).
2. Double-click **`sunocleanser-gui.bat`** at the project root.

The `.bat` runs `conda run -n sunocleanser` and opens the window. No manual `conda activate` needed.

Alternative:

```powershell
cd D:\progs\sunocleanser
conda activate sunocleanser
python -m src.gui
```

In the window: **Browse** → pick the WAV, set **title** if you want, **Process**. **Open out/** opens the output folder.

The GUI starts in **English**. Use the **Language** selector at the top of the window to switch between **English** and **Español** at any time.

## `out/` folder

All GUI outputs go to **`out/`** (relative to the directory you launch from). The repo only tracks `.gitkeep` there; WAVs and reports **are not pushed to Git** (`out/*` in `.gitignore`).

## Generated files

| File | Purpose |
|------|---------|
| `{title} - Phase Cancelled Clean.wav` | Clean version (use in your mix) |
| `{title} - Removed Noise.wav` | Subtracted content only (diagnostics) |
| `{stem}.report.json` | Parameters, peaks, phase verification |

JSON reports use **file names only**, not absolute paths on your machine.

## CLI

```powershell
conda activate sunocleanser
python -m src.cli "C:\path\to\song.wav" --out-dir out --title "My track"
```

Without `--out-dir`, WAVs are written next to the input file; see `python -m src.cli -h` for report placement.

## Tests

```powershell
conda activate sunocleanser
python -m pytest tests/ -q
```

## Documentation

- [docs/suno-denoise.en.md](docs/suno-denoise.en.md) — DSP method
- [docs/architecture.en.md](docs/architecture.en.md) — modules and GUI
