# sunocleanser

**Idioma:** [Español](README.md) · [English](README.en.md)

Limpia exportaciones WAV de Suno con denoise espectral adaptativo, cancelación de fase de verificación y dos archivos de salida en 24-bit.

Usa una líea de proceso posteada en Reddit por u/Cookienomster45, a quien su dios guarda silla fija en el banquete de los héroes.

**GUI** (tkinter) para Windows y **CLI** para scripts o automatización. El DSP vive en `process_suno_wav()`; la interfaz no duplica lógica.

## Requisitos

- Windows (GUI probada ahí; CLI en cualquier OS con Python 3.11+)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o Anaconda

## Instalación

```powershell
cd D:\progs\sunocleanser
conda env create -f environment.yml
conda activate sunocleanser
```

Actualizar tras cambios en `environment.yml`:

```powershell
conda env update -f environment.yml --prune
```

Opcional, dentro del entorno activado:

```powershell
pip install -e .
```

Instala el comando `sunocleanser-gui` (equivalente a `python -m src.gui`).

## Uso rápido (GUI)

1. Crea el entorno `sunocleanser` (una vez).
2. Doble clic en **`sunocleanser-gui.bat`** en la raíz del proyecto.

El `.bat` hace `conda run -n sunocleanser` y abre la ventana. No hace falta `conda activate` manual.

Alternativa:

```powershell
cd D:\progs\sunocleanser
conda activate sunocleanser
python -m src.gui
```

En la ventana: **Examinar** → elige el WAV, ajusta el **título** si quieres, **Procesar**. **Abrir out/** abre la carpeta de salidas.

La GUI se inicia en **inglés**. Usa el selector **Language / Idioma** en la parte superior de la ventana para cambiar entre **English** y **Español** en cualquier momento.

## Carpeta `out/`

Todas las salidas de la GUI van a **`out/`** (relativa al directorio desde el que lanzas la app). Esa carpeta está en el repo solo con `.gitkeep`; WAV e informes **no se suben a Git** (`out/*` en `.gitignore`).

## Archivos que genera

| Archivo | Qué es |
|---------|--------|
| `{título} - Phase Cancelled Clean.wav` | Versión limpia (usar en el mix) |
| `{título} - Removed Noise.wav` | Solo lo restado (diagnóstico) |
| `{stem}.report.json` | Parámetros, picos, verificación de fase |

Los informes JSON usan **nombres de archivo**, no rutas absolutas de tu PC.

## CLI

```powershell
conda activate sunocleanser
python -m src.cli "C:\ruta\cancion.wav" --out-dir out --title "Mi tema"
```

Sin `--out-dir`, los WAV se escriben junto al archivo de entrada; el informe sigue la misma regla que en la ayuda (`python -m src.cli -h`).

## Tests

```powershell
conda activate sunocleanser
python -m pytest tests/ -q
```

## Documentación

- [docs/suno-denoise.md](docs/suno-denoise.md) — método DSP
- [docs/architecture.md](docs/architecture.md) — módulos y GUI

(English: [README.en.md](README.en.md), [suno-denoise.en.md](docs/suno-denoise.en.md), [architecture.en.md](docs/architecture.en.md))
