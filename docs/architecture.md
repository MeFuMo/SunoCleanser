# Arquitectura — sunocleanser

**Idioma:** [Español](architecture.md) · [English](architecture.en.md)

## Módulos

| Módulo | Responsabilidad |
|--------|-----------------|
| `src/audio/io.py` | Lectura/escritura WAV (24-bit PCM), picos |
| `src/audio/stft.py` | STFT/iSTFT con longitud alineada al original |
| `src/suno/noise_profile.py` | Frames quietos (12%) y perfil de ruido enlazado |
| `src/suno/gain_mask.py` | Máscara adaptativa por bandas, techo 7 dB, suavizado |
| `src/suno/pipeline.py` | Orquestación, verificación fase, informe JSON |
| `src/cli.py` | Interfaz de línea de comandos |
| `src/gui/app.py` | Ventana tkinter; llama a `process_suno_wav()` |

## Dependencias

- Python 3.11+
- NumPy, SciPy (`signal.stft` / `istft`)
- soundfile + libsndfile (Conda: `environment.yml`)

## Entorno

```powershell
cd D:\progs\sunocleanser
conda env create -f environment.yml
conda activate sunocleanser
python -m src.cli path\to\song.wav
```

## GUI

- `sunocleanser-gui.bat` / `sunocleanser-gui.sh` — `conda run` + `python -m src.gui` (el `.sh` puede cargar `conda.sh` si conda no está en el PATH)
- O: `conda activate sunocleanser` y `python -m src.gui`

Salida por defecto en `out/`. Procesamiento en un hilo aparte para no bloquear la ventana.
