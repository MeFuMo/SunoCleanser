# Arquitectura — sunocleanser

**Idioma:** [Español](architecture.md) · [English](architecture.en.md)

## Módulos

| Módulo | Responsabilidad |
|--------|-----------------|
| `src/audio/io.py` | Lectura/escritura WAV (24-bit PCM), picos |
| `src/audio/stft.py` | STFT/iSTFT con longitud alineada al original |
| `src/suno/params.py` | `ProcessingParams`, validación, `PARAM_SPECS` (rangos compartidos por CLI y GUI), preajustes |
| `src/suno/noise_profile.py` | Frames quietos y perfil de ruido enlazado |
| `src/suno/gain_mask.py` | Curva de intensidad por banda, techo ajustable, protección de agudos, suavizado, mezcla |
| `src/suno/pipeline.py` | Orquestación, verificación fase, eliminación por banda, informe JSON, callback de progreso |
| `src/settings.py` | Ajustes de usuario persistentes (`~/.sunocleanser/settings.json`) |
| `src/cli.py` | Interfaz de línea de comandos; opciones generadas desde `PARAM_SPECS` |
| `src/gui/app.py` | Ventana tkinter; llama a `process_suno_wav()` |
| `src/gui/i18n.py` | Textos de la GUI en español e inglés |

## Dependencias

- Python 3.9+
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

- `sunocleanser-gui.bat` / `sunocleanser-gui.sh` — `python -m src.gui` (el `.sh` prefiere `venv/` o `.venv/` y si no usa `conda run`)
- O: activa tu entorno y `python -m src.gui`

Los controles se generan desde `PARAM_SPECS`: un parámetro nuevo necesita su entrada en la especificación y los textos `p.<nombre>` / `tip.<nombre>` en `i18n.py` (un test lo comprueba). El cambio de idioma reetiqueta en vivo los widgets registrados. Salida por defecto en `<proyecto>/out/`. El procesamiento corre en un hilo aparte e informa de las etapas mediante el callback `progress` del pipeline.
