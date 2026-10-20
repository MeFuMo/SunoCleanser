# Suno Adaptive Spectral Denoise (v1)

**Idioma:** [Español](suno-denoise.md) · [English](suno-denoise.en.md)

## Objetivo

Reducir estática tipo radio y textura de saturación artificial típica de exportaciones Suno, preservando ataque transitorio, voz, graves (&lt;350 Hz con procesado mínimo) e imagen estéreo.

## Estéreo enlazado

1. STFT independiente en L y R (mismos parámetros).
2. Selección de frames quietos con energía del **promedio de magnitudes L/R**, ignorando bins &lt;350 Hz.
3. Un perfil de ruido `N[f]` = media espectral del **12%** de frames más quietos.
4. Una máscara de ganancia `G[f,t]` a partir del magnitud mono enlazado.
5. La **misma** `G` se aplica a los espectros complejos de L y R (fase original intacta).

## Parámetros por defecto

- `n_fft=2048`, `hop=512`, ventana Hann
- Máxima atenuación ≈ **7 dB** por bin (`MIN_GAIN ≈ 0.447`)
- Suavizado gaussiano de la máscara: σ≈1.5 (frecuencia), σ≈1.0 (tiempo)
- Sustracción con factor `oversubtraction=1.2` modulado por banda

## Salidas

- `{title} - Phase Cancelled Clean.wav` — `Original + (−(Original − Denoised))`
- `{title} - Removed Noise.wav` — `Original − Denoised`
- Informe JSON: parámetros, picos, error de reconstrucción

## Verificación

En aritmética de doble precisión, la mezcla por cancelación de fase debe coincidir con la señal denoised; el informe incluye error máximo y RMS en dB relativo. Umbral por defecto: −60 dB.

## Límites

- No aplica EQ, compresión, limitación ni normalización en la exportación.
- Ruido no estacionario fuertemente mezclado con la voz puede dejar artefactos residuales.
- v2 opcional: máscaras L/R independientes (más agresivo, peor imagen).

## Afinado

Prueba con tus WAV reales Suno y ajusta en CLI:

- `--quiet-fraction` si el perfil de ruido se contamina con pasajes musicales suaves
- `--n-fft` / `--hop` para resolución tiempo-frecuencia
