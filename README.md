# sunocleanser

CLI para limpiar WAV de Suno con denoise espectral adaptativo, cancelación de fase de verificación y dos exportaciones 24-bit.

## Conda (recomendado)

```powershell
cd D:\progs\sunocleanser
conda env create -f environment.yml
conda activate sunocleanser
```

Actualizar entorno tras cambios en `environment.yml`:

```powershell
conda env update -f environment.yml --prune
```

## Uso

```powershell
conda activate sunocleanser
python -m src.cli "C:\ruta\cancion.wav" --out-dir "C:\salida" --title "Mi tema"
```

Salidas:

- `Mi tema - Phase Cancelled Clean.wav`
- `Mi tema - Removed Noise.wav`
- `{stem}.report.json` (junto al WAV o en `--out-dir` si se indica carpeta)

## Tests

```powershell
conda activate sunocleanser
python -m pytest tests/ -q
```

## Documentación

- [docs/suno-denoise.md](docs/suno-denoise.md) — método DSP
- [docs/architecture.md](docs/architecture.md) — módulos
