# Suno Adaptive Spectral Denoise (v1)

**Language:** [Español](suno-denoise.md) · [English](suno-denoise.en.md)

## Goal

Reduce radio-style hiss and artificial saturation texture typical of Suno exports, while preserving transients, vocals, bass (&lt;350 Hz with minimal processing), and stereo imaging.

## Linked stereo

1. Independent STFT on L and R (same parameters).
2. Quiet-frame selection using energy of the **average of L/R magnitudes**, ignoring bins &lt;350 Hz.
3. One noise profile `N[f]` = spectral mean of the **quietest 12%** of frames.
4. One gain mask `G[f,t]` from linked mono magnitude.
5. The **same** `G` is applied to L and R complex spectra (original phase intact).

## Default parameters

- `n_fft=2048`, `hop=512`, Hann window
- Maximum attenuation ≈ **7 dB** per bin (`MIN_GAIN ≈ 0.447`)
- Gaussian mask smoothing: σ≈1.5 (frequency), σ≈1.0 (time)
- Subtraction with `oversubtraction=1.2` modulated per band

## Outputs

- `{title} - Phase Cancelled Clean.wav` — `Original + (−(Original − Denoised))`
- `{title} - Removed Noise.wav` — `Original − Denoised`
- JSON report: parameters, peaks, reconstruction error

## Verification

In double precision, the phase-cancel mix must match the denoised signal; the report includes max and RMS error in relative dB. Default threshold: −60 dB.

## Limits

- No EQ, compression, limiting, or normalization on export.
- Non-stationary noise strongly mixed with vocals may leave residual artifacts.
- Optional v2: independent L/R masks (more aggressive, worse imaging).

## Tuning

Try real Suno WAVs and adjust via CLI:

- `--quiet-fraction` if the noise profile is polluted by soft musical passages
- `--n-fft` / `--hop` for time–frequency resolution
