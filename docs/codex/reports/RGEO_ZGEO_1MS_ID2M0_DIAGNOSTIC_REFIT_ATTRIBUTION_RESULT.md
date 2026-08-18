# R_geo/Z_geo 1 ms ID-2M0 diagnostic refit attribution result

Date: 2026-08-18 Asia/Shanghai

## Verdict

ID-2M0 passed as
`ONE_MS_ID2M0_DIAGNOSTIC_ATTRIBUTION_PASS_ID2M1_DESIGN_ONLY`.
The server refitted exactly the four frozen ID-2L1
`stable_signed_even` folds. Every saved fold aggregate was reproduced with
maximum numeric difference `0.0`; a separate process reproduced both the
result and all 720 per-issue rows exactly.

This does not change ID-2L1's formal FAIL and does not select or emit a model.
It authorizes only a separately frozen ID-2M1 development comparison with at
most two small structured candidates.

## Evidence identity

- implementation revision: `176cf1a946cc58b50b3145748125984025085286`;
- server output: `artifacts/server_runs/rgeo_zgeo_1ms_id2m0_20260818_176cf1a9`;
- result SHA-256: `0624799999d2efca584ad2c75960e7d8e4568bb06fa4960738a963b2c4d84de1`;
- predictions SHA-256: `b842011b87231eb3fa28117191ed27be795d7c1c479f1e0548da2d461115b32d`;
- independent audit SHA-256: `7aa1dc54bd8921ec01531ddab3521ebf0c26c2c05a925f3e329345b569d9bfd1`;
- focused server tests: `10/10`;
- all matching one-ms server tests: `213/213`;
- TSC calls, resets and plant advances: `0 / 0 / 0`.

Tracked compact evidence is under
`docs/codex/audits/rgeo_zgeo_1ms_id2m0_20260818_176cf1a9/`.

## Attribution

For issues 16--33, every fold contains 180 cell-weighted one-step rows but
only 106 exact causal-transition keys. The original R p95 values are
`0.426315 / 0.426288 / 0.394224 / 0.394771 mm`; the diagnostic unique-key
p95 values are `0.248585 / 0.247980 / 0.228058 / 0.228665 mm`.

Rows above the frozen `0.300 mm` R threshold number
`15 / 15 / 10 / 10`, but collapse to only `3 / 3 / 2 / 2` unique events.
Every such event precedes probe issue 25 and belongs to a conditioner
hold/return/delayed-tail cell. The maximum issue-25--28 probe-window R error
is only `0.274944 / 0.276108 / 0.266467 / 0.266064 mm`.

This confirms that the signed/even backbone is useful as a local
probe-response component, not a complete world model. Deduplication is a
diagnostic weighting view only and cannot retroactively pass ID-2L1.

## Architecture finding

The retained model uses time and fixed-pole signed/even issued-action memory.
Exact current R_geo/Z_geo/Ip is only a rollout origin; neither current state,
recent velocity nor actual-versus-issued current innovation affects the
predicted increment. A naive unrestricted carry-forward innovation was
already contraindicated by the attribution, so the successor must use a
small bounded state rather than generic online error feedback.

The GRU recenter/free evaluator separately overwrites all earlier context
rows with the later rollout-origin context before rebuilding hidden state.
Its affected results are therefore not valid evidence against recurrent
models as a class. The defect does not affect the deterministic
`stable_signed_even` recomputation and is not repaired inside ID-2L1.

## Authorized next step

ID-2M1 may compare at most:

1. separated causal nominal plus signed/even action memory with explicit
   action edge, dwell, return and tail state; and
2. the same structure plus a low-dimensional, stability-constrained state
   and actual-current innovation correction.

Labels such as history, sign, direction, conditioner or probe remain
evaluator-only. Whole-history folds, original cell-weighted gates,
unique-prefix diagnostics and worst unique-event caps must all be reported.
No new TSC is needed for this discriminator. A PASS still requires a fresh
calibration and unopened whole-history holdout before authority, recovery or
controller work.
