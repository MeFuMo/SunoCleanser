# Architecture — sunocleanser

**Language:** [Español](architecture.md) · [English](architecture.en.md)

## Modules

| Module | Responsibility |
|--------|----------------|
| `src/audio/io.py` | WAV read/write (24-bit PCM), peaks |
| `src/audio/stft.py` | STFT/iSTFT with length aligned to the original |
| `src/suno/noise_profile.py` | Quiet frames (12%) and linked noise profile |
| `src/suno/gain_mask.py` | Adaptive band mask, 7 dB ceiling, smoothing |
| `src/suno/pipeline.py` | Orchestration, phase check, JSON report |
| `src/cli.py` | Command-line interface |
| `src/gui/app.py` | tkinter window; calls `process_suno_wav()` |

## Dependencies

- Python 3.11+
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

- `sunocleanser-gui.bat` / `sunocleanser-gui.sh` — `conda run` + `python -m src.gui` (`.sh` may `source conda.sh` if conda is not on PATH)
- Or: `conda activate sunocleanser` and `python -m src.gui`

Default output in `out/`. Processing runs on a background thread so the window stays responsive.
