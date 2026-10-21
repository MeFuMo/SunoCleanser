# Architecture — sunocleanser

**Language:** [Español](architecture.md) · [English](architecture.en.md)

## Modules

| Module | Responsibility |
|--------|----------------|
| `src/audio/io.py` | WAV read/write (24-bit PCM), peaks |
| `src/audio/stft.py` | STFT/iSTFT with length aligned to the original |
| `src/suno/params.py` | `ProcessingParams`, validation, `PARAM_SPECS` (ranges shared by CLI and GUI), presets |
| `src/suno/noise_profile.py` | Quiet frames and linked noise profile |
| `src/suno/gain_mask.py` | Band strength curve, adjustable ceiling, top-end protection, smoothing, mix |
| `src/suno/pipeline.py` | Orchestration, phase check, per-band removal, JSON report, progress callback |
| `src/settings.py` | Persisted user settings (`~/.sunocleanser/settings.json`) |
| `src/cli.py` | Command-line interface; flags generated from `PARAM_SPECS` |
| `src/gui/app.py` | tkinter window; calls `process_suno_wav()` |
| `src/gui/i18n.py` | GUI strings, English and Spanish |

## Dependencies

- Python 3.9+
- NumPy, SciPy (`signal.stft` / `istft`)
- soundfile + libsndfile (Conda: `environment.yml`)

## Environment

```powershell
cd D:\progs\sunocleanser
conda env create -f environment.yml
conda activate sunocleanser
python -m src.cli path\to\song.wav
```

## GUI

- `sunocleanser-gui.bat` / `sunocleanser-gui.sh` — `python -m src.gui` (`.sh` prefers `venv/` or `.venv/`, then `conda run`)
- Or: activate your environment and `python -m src.gui`

Controls are built from `PARAM_SPECS`, so a new parameter needs a spec entry plus `p.<name>` / `tip.<name>` strings in `i18n.py` (a test enforces this). Language switches live by relabelling registered widgets. Default output in `<project>/out/`. Processing runs on a background thread, reporting stages through the pipeline's `progress` callback.
