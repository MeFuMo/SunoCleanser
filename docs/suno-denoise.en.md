# Suno Adaptive Spectral Denoise (v2)

**Language:** [Español](suno-denoise.md) · [English](suno-denoise.en.md)

## Goal

Reduce radio-style hiss and artificial saturation texture typical of Suno exports, while preserving transients, vocals, bass (&lt;350 Hz with minimal processing), and stereo imaging.

## Linked stereo

1. Independent STFT on L and R (same parameters).
2. Quiet-frame selection using energy of the **average of L/R magnitudes**, ignoring bins &lt;350 Hz.
3. One noise profile `N[f]` = spectral mean of the **quietest 12%** of frames.
4. One gain mask `G[f,t]` from linked mono magnitude, shaped per band, capped at `max_attenuation_db`, smoothed, then blended by `mix`.
5. The **same** `G` is applied to L and R complex spectra (original phase intact).

## Parameters

All of these are in `ProcessingParams` (`src/suno/params.py`), exposed in the GUI and as CLI flags. Defaults reproduce v1 exactly.

| Parameter | Default | What it does |
|-----------|---------|--------------|
| `mix` | 1.0 | Wet/dry in the gain domain: `G' = 1 − mix·(1 − G)`. 0 = bypass |
| `max_attenuation_db` | 7 | Ceiling on reduction per bin (`MIN_GAIN = 10^(−dB/20)`) |
| `oversubtraction` | 1.2 | Multiplier on the noise profile before subtraction |
| `mid_band_strength` | 1.0 | Scales the mid-band strength curve (0.35 → 0.60 from `bass_cut_hz` to `mid_split_hz`) |
| `high_band_strength` | 1.0 | Scales the high-band curve (0.55 → 1.0 from `mid_split_hz` to `high_peak_hz`) |
| `top_protect_hz` | 0 (off) | Unity gain at and above this frequency, raised-cosine fade over 1/3 octave below |
| `bass_cut_hz` | 350 | Below: untouched and ignored for quiet-frame selection |
| `quiet_fraction` | 0.12 | Share of quietest frames averaged into the noise profile |
| `mid_split_hz` | 4000 | Mid/high band boundary |
| `high_peak_hz` | 16000 | Where the high band reaches full strength |
| `freq_smooth_sigma` / `time_smooth_sigma` | 1.5 / 1.0 | Gaussian mask smoothing (bins / frames); 0 disables |
| `n_fft` / `hop_length` / `window` | 2048 / 512 / hann | STFT; `hop_length ≤ n_fft/2` |

Invalid combinations (e.g. `high_peak_hz ≤ mid_split_hz`) are rejected before processing with a message listing every problem.

## Presets

Energy removed per band on a 4.5-minute, 48 kHz Suno track (from the report's `band_removal_db`):

| Preset | 350–2k | 2–4k | 4–8k | 8–12k | 12–16k | 16k+ |
|--------|-------:|-----:|-----:|------:|-------:|-----:|
| original | −0.98 | −0.95 | −0.90 | −1.14 | −1.39 | −1.68 |
| gentle | −0.80 | −0.78 | −0.44 | −0.55 | −0.68 | −0.84 |
| transparent | −0.47 | −0.46 | −0.34 | −0.42 | −0.28 | 0.00 |
| strong | −1.23 | −1.19 | −1.33 | −1.68 | −2.04 | −2.47 |

`original` removes progressively more above 8 kHz (a downward tilt); `gentle` is tuned so the highs lose no more than the mids. These are long-term averages: quiet passages are reduced more, up to `max_attenuation_db`.

## Outputs

- `{title} - Phase Cancelled Clean.wav` — `Original + (−(Original − Denoised))`
- `{title} - Removed Noise.wav` — `Original − Denoised`
- JSON report: parameters, per-band removal (`band_removal_db`), peaks, reconstruction error

## Verification

In double precision, the phase-cancel mix must match the denoised signal; the report includes max and RMS error in relative dB. Default threshold: −60 dB.

## Limits

- No EQ, compression, limiting, or normalization on export.
- Non-stationary noise strongly mixed with vocals may leave residual artifacts.
- Optional v2: independent L/R masks (more aggressive, worse imaging).

## Tuning

Every report includes `band_removal_db`, and the GUI prints it after each file, so you can compare settings by numbers as well as by ear. Tick **Add preset to file names** to keep A/B renders side by side.

- **Top end dull or sliced off:** lower `high_band_strength` (0.5–0.7), then `max_attenuation_db` (4–5 dB), or set `top_protect_hz` (15000–16000) to leave the air band alone.
- **Too much overall:** lower `mix` or `oversubtraction`.
- **Hiss still audible:** raise `oversubtraction` or `high_band_strength`; try the `strong` preset.
- **Chirpy / watery artifacts (“musical noise”):** raise `freq_smooth_sigma` / `time_smooth_sigma`, or lower `max_attenuation_db`.
- **Soft passages treated as noise:** lower `quiet_fraction`; for dense tracks with no quiet moments, raise it.
- **Time–frequency resolution:** `n_fft` / `hop_length`.
