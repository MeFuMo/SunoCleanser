# sunocleanser

**Language:** [Español](README.md) · [English](README.en.md)

Cleans Suno WAV exports with adaptive spectral denoise, phase-cancel verification, and two 24-bit output files.

Uses a process as posted in Reddit by u/Cookienomster45. May your god keep you in any kind of eternal feast of heroes.

**GUI** (tkinter, English/Spanish) and **CLI** for scripts or automation. DSP lives in `process_suno_wav()`; the UI does not duplicate processing logic.

## Requirements

- Windows, macOS or Linux with Python 3.9+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)/Anaconda, **or** a plain venv:
  `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
- **macOS:** the GUI needs Tk 8.6+. Apple's built-in `/usr/bin/python3` has Tk 8.5 (blank gray window, “Tk deprecated” warning); don't build the venv from it. `./sunocleanser-gui.sh` skips it automatically and uses your conda env or a python.org/Homebrew Python instead.

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
2. Windows: double-click **`sunocleanser-gui.bat`**. Linux/macOS: `./sunocleanser-gui.sh` (`chmod +x sunocleanser-gui.sh` if needed).

The `.sh` launcher picks the first Python with Tk 8.6+ and the audio libraries (`venv/`, `.venv/`, the conda env `sunocleanser`, then python.org/Homebrew installs), and lists what it checked if none qualifies. Force one with `SUNOCLEANSER_PYTHON=/path/to/python`.

Alternative:

```powershell
cd D:\progs\sunocleanser
conda activate sunocleanser
python -m src.gui
```

In the window:

1. **EN / ES** (top right) switches the interface language instantly.
2. **Browse** → pick one or more files (WAV, FLAC, AIFF, OGG, MP3). With several files, each output uses its own file name.
3. Optionally set the **title**, tick **Add preset to file names** to A/B different settings side by side, and choose the **output folder**.
4. Pick a **preset** and adjust the sliders (hover any label for an explanation). **Show advanced settings** reveals the rest.
5. **Process**. The log shows how much energy was removed in each frequency band, so you can see at a glance whether the top end is being cut.

### Settings and presets

| Preset | Character |
|--------|-----------|
| Original (v1) | The original algorithm, bit-identical to v1 |
| Gentle | Same approach, lighter; highs lose no more than mids |
| Transparent | Very light; the top end above 15 kHz is left alone |
| Strong | Harder on hiss for very fizzy generations |

Changing any slider marks the preset **(modified)**. **Save as…** stores your settings as a custom preset (★), **Reset** returns to the selected preset, **Delete** removes a custom preset. Language, last settings, custom presets and output folder are remembered in `~/.sunocleanser/settings.json` (override with the `SUNOCLEANSER_SETTINGS` environment variable).

**Top end sounding dull?** In order: lower **High band strength**, lower **Max reduction**, or turn on **Protect top end above** (e.g. 15–16 kHz). **Effect amount** backs everything off at once. See [docs/suno-denoise.en.md](docs/suno-denoise.en.md#tuning) for what each control does.

The GUI starts in **English**. Use the **Language** selector at the top of the window to switch between **English** and **Español** at any time.

## `out/` folder

By default outputs go to **`out/`** inside the project folder (wherever you launch from); pick any other folder in the GUI or with `--out-dir`. The repo only tracks `.gitkeep` there; WAVs and reports **are not pushed to Git** (`out/*` in `.gitignore`).

## Generated files

| File | Purpose |
|------|---------|
| `{title} - Phase Cancelled Clean.wav` | Clean version (use in your mix) |
| `{title} - Removed Noise.wav` | Subtracted content only (diagnostics) |
| `{title}.report.json` | Parameters, per-band removal, peaks, phase verification |

JSON reports use **file names only**, not absolute paths on your machine.

## CLI

```powershell
conda activate sunocleanser
python -m src.cli "C:\path\to\song.wav" --out-dir out --title "My track"
```

Without `--out-dir`, WAVs are written next to the input file; see `python -m src.cli -h` for report placement.

Every setting has a flag, applied on top of `--preset` (default `original`). Custom presets saved in the GUI work here too:

```bash
python -m src.cli song.wav --preset gentle --top-protect-hz 16000
python -m src.cli *.wav --out-dir out --high-band-strength 0.5 --max-attenuation-db 4
python -m src.cli --list-presets
```

## Tests

```powershell
conda activate sunocleanser
python -m pytest tests/ -q
```

## Documentation

- [docs/suno-denoise.en.md](docs/suno-denoise.en.md) — DSP method
- [docs/architecture.en.md](docs/architecture.en.md) — modules and GUI
