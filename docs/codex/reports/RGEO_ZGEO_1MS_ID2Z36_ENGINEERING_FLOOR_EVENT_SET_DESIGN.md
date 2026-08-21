# ID2Z36 engineering-floor event-set design

Date: 2026-08-21

## Purpose

ID2Z35 rejected the frozen ID2Z34 componentwise event box at fresh phase52.
This stage runs zero TSC and fits no observations. It constructs exactly one
successor payload by applying fixed engineering minimum half-widths to the
already selected ID2Z34 event cell.

The floors are not calculated from the ID2Z35 miss:

- R: `0.375 mm`, one half of the already frozen ID2Z34 maximum permitted
  `0.750 mm` event full width;
- Z: `0.075 mm`, the already frozen ID2Z35 calibrated non-event half-width cap;
- Ip: `30 A`, the already frozen ID2Z35 calibrated non-event half-width cap.

ID2Z35 is read only to authenticate its final route and to prevent accidental
reuse as fit data. Its calibration rows have zero fit weight and do not enter
the payload calculation.

## Construction

Copy the complete frozen ID2Z34 payload. For its sole event cell, replace each
half-width by `max(original_half_width, engineering_floor)`. Preserve the event
center, point centers, effect-age coordinate and all non-event predictions
byte-for-value. Recompute a new payload SHA-256 from canonical JSON.

There is one candidate, no hyperparameter or floor search, no model fit, no
calibration or holdout read, and no plant advance.

## Gates

- ID2Z34 result and payload identity authenticate exactly.
- ID2Z35 result and independent audit authenticate exactly, including the
  calibration-fail route and unopened blind layer.
- the source event count remains one and its coordinate remains
  `q_r:minus/effect-age 13`;
- R event full width remains at most `0.750 mm`;
- all output half-widths equal the deterministic max construction;
- all point centers and non-event metrics remain unchanged;
- ID2Z35 fit rows used: zero; TSC calls: zero.

PASS authorizes only a new-identity fresh phase48 calibration followed, only
after calibration PASS, by an unopened phase54 blind family. It does not
retroactively pass ID2Z35 and does not authorize feedback, Authority-L0,
capture, recovery or Recourse-L1.

If construction or authentication fails, stop without TSC. There is no second
candidate or adjacent floor search.
