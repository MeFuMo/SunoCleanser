# Suno Adaptive Spectral Denoise (v2)

**Idioma:** [Español](suno-denoise.md) · [English](suno-denoise.en.md)

## Objetivo

Reducir estática tipo radio y textura de saturación artificial típica de exportaciones Suno, preservando ataque transitorio, voz, graves (&lt;350 Hz con procesado mínimo) e imagen estéreo.

## Estéreo enlazado

1. STFT independiente en L y R (mismos parámetros).
2. Selección de frames quietos con energía del **promedio de magnitudes L/R**, ignorando bins &lt;350 Hz.
3. Un perfil de ruido `N[f]` = media espectral del **12%** de frames más quietos.
4. Una máscara de ganancia `G[f,t]` a partir de la magnitud mono enlazada, modulada por banda, limitada a `max_attenuation_db`, suavizada y mezclada según `mix`.
5. La **misma** `G` se aplica a los espectros complejos de L y R (fase original intacta).

## Parámetros

Todos están en `ProcessingParams` (`src/suno/params.py`) y se exponen en la GUI y como opciones de la CLI. Los valores por defecto reproducen la v1 exactamente.

| Parámetro | Defecto | Qué hace |
|-----------|---------|----------|
| `mix` | 1.0 | Mezcla seco/procesado en la ganancia: `G' = 1 − mix·(1 − G)`. 0 = sin efecto |
| `max_attenuation_db` | 7 | Techo de reducción por bin (`MIN_GAIN = 10^(−dB/20)`) |
| `oversubtraction` | 1.2 | Multiplicador del perfil de ruido antes de restar |
| `mid_band_strength` | 1.0 | Escala la curva de la banda media (0,35 → 0,60 entre `bass_cut_hz` y `mid_split_hz`) |
| `high_band_strength` | 1.0 | Escala la curva de la banda alta (0,55 → 1,0 entre `mid_split_hz` y `high_peak_hz`) |
| `top_protect_hz` | 0 (desactivado) | Ganancia unidad a partir de esta frecuencia, con transición coseno de 1/3 de octava por debajo |
| `bass_cut_hz` | 350 | Por debajo: intacto e ignorado al elegir frames quietos |
| `quiet_fraction` | 0.12 | Proporción de frames más quietos promediados en el perfil de ruido |
| `mid_split_hz` | 4000 | Límite entre banda media y alta |
| `high_peak_hz` | 16000 | Donde la banda alta alcanza su máxima intensidad |
| `freq_smooth_sigma` / `time_smooth_sigma` | 1.5 / 1.0 | Suavizado gaussiano de la máscara (bins / frames); 0 lo desactiva |
| `n_fft` / `hop_length` / `window` | 2048 / 512 / hann | STFT; `hop_length ≤ n_fft/2` |

Las combinaciones inválidas (p. ej. `high_peak_hz ≤ mid_split_hz`) se rechazan antes de procesar con un mensaje que lista todos los problemas.

## Preajustes

Energía eliminada por banda en una pista Suno de 4,5 minutos a 48 kHz (campo `band_removal_db` del informe):

| Preajuste | 350–2k | 2–4k | 4–8k | 8–12k | 12–16k | 16k+ |
|-----------|-------:|-----:|-----:|------:|-------:|-----:|
| original | −0,98 | −0,95 | −0,90 | −1,14 | −1,39 | −1,68 |
| gentle | −0,80 | −0,78 | −0,44 | −0,55 | −0,68 | −0,84 |
| transparent | −0,47 | −0,46 | −0,34 | −0,42 | −0,28 | 0,00 |
| strong | −1,23 | −1,19 | −1,33 | −1,68 | −2,04 | −2,47 |

`original` elimina cada vez más por encima de 8 kHz (inclinación hacia abajo); `gentle` está ajustado para que los agudos no pierdan más que los medios. Son promedios de toda la pista: los pasajes quietos se reducen más, hasta `max_attenuation_db`.

## Salidas

- `{title} - Phase Cancelled Clean.wav` — `Original + (−(Original − Denoised))`
- `{title} - Removed Noise.wav` — `Original − Denoised`
- Informe JSON: parámetros, eliminación por banda (`band_removal_db`), picos, error de reconstrucción

## Verificación

En aritmética de doble precisión, la mezcla por cancelación de fase debe coincidir con la señal denoised; el informe incluye error máximo y RMS en dB relativo. Umbral por defecto: −60 dB.

## Límites

- No aplica EQ, compresión, limitación ni normalización en la exportación.
- Ruido no estacionario fuertemente mezclado con la voz puede dejar artefactos residuales.
- v2 opcional: máscaras L/R independientes (más agresivo, peor imagen).

## Afinado

Cada informe incluye `band_removal_db` y la GUI lo muestra tras cada archivo, así que puedes comparar ajustes con números además de con el oído. Marca **Añadir preajuste al nombre** para conservar versiones A/B lado a lado.

- **Agudos apagados o recortados:** baja `high_band_strength` (0,5–0,7), luego `max_attenuation_db` (4–5 dB), o fija `top_protect_hz` (15000–16000) para no tocar la banda de aire.
- **Demasiado en general:** baja `mix` u `oversubtraction`.
- **Sigue habiendo siseo:** sube `oversubtraction` o `high_band_strength`; prueba el preajuste `strong`.
- **Artefactos tipo “ruido musical”:** sube `freq_smooth_sigma` / `time_smooth_sigma` o baja `max_attenuation_db`.
- **Pasajes suaves tratados como ruido:** baja `quiet_fraction`; en pistas densas sin momentos quietos, súbelo.
- **Resolución tiempo-frecuencia:** `n_fft` / `hop_length`.
