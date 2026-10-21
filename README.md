# sunocleanser

**Idioma:** [Español](README.md) · [English](README.en.md)

Limpia exportaciones WAV de Suno con denoise espectral adaptativo, cancelación de fase de verificación y dos archivos de salida en 24-bit.

Usa una líea de proceso posteada en Reddit por u/Cookienomster45, a quien su dios guarda silla fija en el banquete de los héroes.

**GUI** (tkinter, español/inglés) y **CLI** para scripts o automatización. El DSP vive en `process_suno_wav()`; la interfaz no duplica lógica.

## Requisitos

- Windows, macOS o Linux con Python 3.9+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)/Anaconda, **o** un venv normal:
  `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
- **macOS:** la GUI necesita Tk 8.6+. El `/usr/bin/python3` de Apple trae Tk 8.5 (ventana gris vacía, aviso “Tk deprecated”); no crees el venv con él. `./sunocleanser-gui.sh` lo descarta automáticamente y usa tu entorno conda o un Python de python.org/Homebrew.

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
2. Windows: doble clic en **`sunocleanser-gui.bat`**. Linux/macOS: `./sunocleanser-gui.sh` (`chmod +x sunocleanser-gui.sh` si hace falta).

El lanzador `.sh` elige el primer Python con Tk 8.6+ y las librerías de audio (`venv/`, `.venv/`, el entorno conda `sunocleanser` y luego instalaciones de python.org/Homebrew), y si ninguno sirve muestra lo que comprobó. Para forzar uno: `SUNOCLEANSER_PYTHON=/ruta/a/python`.

Alternativa:

```powershell
cd D:\progs\sunocleanser
conda activate sunocleanser
python -m src.gui
```

En la ventana:

1. **EN / ES** (arriba a la derecha) cambia el idioma de la interfaz al instante.
2. **Examinar** → elige uno o varios archivos (WAV, FLAC, AIFF, OGG, MP3). Con varios, cada salida usa el nombre de su archivo.
3. Opcional: ajusta el **título**, marca **Añadir preajuste al nombre** para comparar ajustes lado a lado y elige la **carpeta de salida**.
4. Elige un **preajuste** y mueve los deslizadores (pasa el ratón sobre cada etiqueta para ver una explicación). **Mostrar ajustes avanzados** muestra el resto.
5. **Procesar**. El registro muestra cuánta energía se eliminó en cada banda de frecuencia, para ver de un vistazo si se están recortando los agudos.

### Ajustes y preajustes

| Preajuste | Carácter |
|-----------|----------|
| Original (v1) | El algoritmo original, idéntico bit a bit a la v1 |
| Suave | Mismo enfoque, más ligero; los agudos no pierden más que los medios |
| Transparente | Muy ligero; por encima de 15 kHz no se toca |
| Fuerte | Más agresivo con el siseo en generaciones muy “efervescentes” |

Al mover cualquier deslizador el preajuste se marca **(modificado)**. **Guardar como…** guarda tus ajustes como preajuste propio (★), **Restablecer** vuelve al preajuste elegido y **Eliminar** borra un preajuste propio. El idioma, los últimos ajustes, los preajustes propios y la carpeta de salida se recuerdan en `~/.sunocleanser/settings.json` (se puede cambiar con la variable de entorno `SUNOCLEANSER_SETTINGS`).

**¿Agudos apagados?** Por orden: baja **Intensidad en agudos**, baja **Reducción máxima** o activa **Proteger agudos por encima de** (p. ej. 15–16 kHz). **Intensidad del efecto** lo suaviza todo a la vez. Ver [docs/suno-denoise.md](docs/suno-denoise.md#afinado) para el detalle de cada control.

La GUI se inicia en **inglés**. Usa el selector **Language / Idioma** en la parte superior de la ventana para cambiar entre **English** y **Español** en cualquier momento.

## Carpeta `out/`

Por defecto las salidas van a **`out/`** dentro de la carpeta del proyecto (da igual desde dónde lances la app); puedes elegir otra en la GUI o con `--out-dir`. Esa carpeta está en el repo solo con `.gitkeep`; WAV e informes **no se suben a Git** (`out/*` en `.gitignore`).

## Archivos que genera

| Archivo | Qué es |
|---------|--------|
| `{título} - Phase Cancelled Clean.wav` | Versión limpia (usar en el mix) |
| `{título} - Removed Noise.wav` | Solo lo restado (diagnóstico) |
| `{título}.report.json` | Parámetros, eliminación por banda, picos, verificación de fase |

Los informes JSON usan **nombres de archivo**, no rutas absolutas de tu PC.

## CLI

```powershell
conda activate sunocleanser
python -m src.cli "C:\ruta\cancion.wav" --out-dir out --title "Mi tema"
```

Sin `--out-dir`, los WAV se escriben junto al archivo de entrada; el informe sigue la misma regla que en la ayuda (`python -m src.cli -h`).

Cada ajuste tiene su opción, aplicada sobre `--preset` (por defecto `original`). Los preajustes propios guardados en la GUI también funcionan aquí:

```bash
python -m src.cli cancion.wav --preset gentle --top-protect-hz 16000
python -m src.cli *.wav --out-dir out --high-band-strength 0.5 --max-attenuation-db 4
python -m src.cli --list-presets
```

## Tests

```powershell
conda activate sunocleanser
python -m pytest tests/ -q
```

## Documentación

- [docs/suno-denoise.md](docs/suno-denoise.md) — método DSP
- [docs/architecture.md](docs/architecture.md) — módulos y GUI

(English: [README.en.md](README.en.md), [suno-denoise.en.md](docs/suno-denoise.en.md), [architecture.en.md](docs/architecture.en.md))
