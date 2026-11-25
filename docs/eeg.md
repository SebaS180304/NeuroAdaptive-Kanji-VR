# EEG pipeline

Code in `backend/app/eeg/`. Nothing here changes a frozen rule: values change only by a numbered decision.

## Streams and clocks

- `AURA` (8 ch, 250 Hz) and `UnityMarkers` (JSON strings) come over LSL. `lsl_reader.open_local_inlet`
  takes only the stream of this PC, and refuses if there are two.
- The S3 sync taps on Cz give the offset between the two clocks (`sync.py`): robust spread ≤ 50 ms,
  |offset| ≤ 250 ms. The offset is applied to the EEG before cutting.

## Epochs (`epochs.py`)

- **5 s epochs every 2.5 s**, on a grid fixed by the session's first stamp (`eeg_sessions.grid_origin_lsl`),
  so the live and the offline cut share indices.
- Each epoch has **9 chunks of 1 s every 0.5 s**. A chunk is clean unless:
    - a blink: Fp1 over 75 µV, ±200 ms around it (not with rule `ica`);
    - an index channel over 100 µV;
    - a flat index channel (peak to peak < 1 µV) or missing samples;
    - the 0.5 s after a sound onset (which sounds, by rule).
- The quality (`GOOD`, `ACCEPTABLE`, `POOR`) follows the seconds the clean chunks cover. A `POOR` epoch
  has no indices.
- Filter: 1–40 Hz band-pass and a 60 Hz notch, zero-phase (`preprocess.py`).
- A channel more than 20 % over 100 µV in two consecutive 30 s bins is excluded from then on
  (`persistently_bad`); two out and the EEG no longer counts.
- Indices per epoch (`features.py`): Engagement Index β / (α + θ), theta in Fz, parietal alpha and θ/β
  (the last two for analysis only).

## Live (`live.py`)

- Started by `autorun`. It cuts from the end of S3: the S1–S3 epochs arrive together at that moment, and
  from S4 one every 2.5 s, about 1.2 s after the epoch ends.
- An epoch is cut once there is `EDGE_S` = 1.0 s of signal after it, filtering from `PAD_S` = 10 s before.
  **Known limit:** the zero-phase filter bends the last second of the buffer, so a chunk at a threshold
  can flip between the live cut and the offline one. With a blink-heavy Fp1 this reached ≈ 20 % of the
  epochs in one November 2026 test session; usually ≈ 2 %. A causal filter is the planned fix, after the pilot.
- It writes epochs, sync, the reference, the ICA result and a heartbeat every 2 s. With
  `EEG_MONITOR_LIVE=true` it also writes the per-channel figures of the monitor (M1b), outside the cut.

## The reference (`reference.py`)

- From the non-POOR epochs of S6: at least 15 (`MIN_EPOCHS`); with fewer, the S4 eyes-open epochs, marked
  as the fallback. Stored with `s6_non_poor` and `at_threshold` (S6 within one of 15).
- Each index is used as ln, and its z against the reference's mean and SD.
- `fill_from_xdf` overwrites `eeg_sessions.reference` after the Stop; the official one stays the live one
  (the `autorun` line and `live_epochs.csv`).

## The three rules (`EEG_LIVE_RULE`)

| Rule | Name | What |
| --- | --- | --- |
| `current` | option (1) | blink rule on Fp1, every sound trimmed |
| `nosound` | option (2) | the task sounds of S6–S8 kept (select and result); a sound-density check instead |
| `ica` | option (3) | before S6 as (2); at S6 an ICA fitted on S4–S6 removes the eye component from every epoch from S6 on, with no blink rule |

With `ica` (`ica.py`, inside `live.Buffer`):

- the component is identified when its correlation with Fp1 is ≥ 0.7 and its top weight is on Fp1;
  otherwise the session runs with (2) and says why;
- a channel out before S6 → the ICA is fitted without it (Fp1 out → (2)); out after S6 → (2) from then
  to the end, with no refit;
- the fitted model is stored in `eeg_sessions.ica` and reused, never refitted, by `fill_from_xdf`.

## Offline

- `fill_from_xdf` (run by `autorun` after the Stop) re-cuts the XDF through the same `Buffer` and
  replaces the live rows, for the analysis.
- `python -m app.adaptation.replay <session> --xdf <path> --rule <rule>` replays the engine on the XDF.
  Run it inside the backend container.
- `database/verify_eeg.sql`: sync, S4 alpha, S6 and the reference, usable epochs per state, A-7 (live,
  official, and from the XDF) and the epochs that differ between both cuts.
