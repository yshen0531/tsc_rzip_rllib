# R_geo/Z_geo 1 ms ID-0R1 memory/context audit

Date: 2026-08-14 Asia/Shanghai

Route:

```text
ONE_MS_ID0R1_STABLE_LATENT_MEMORY_AND_ID1A_CONTEXT_PILOT_REQUIRED
```

## Scope and evidence identity

This was a repository-local, zero-TSC, zero-server, zero-fit audit of the two
tracked ID-0T1 q0 baselines and six tracked early signed response records.
Every input SHA-256 is frozen in
`configs/rgeo_zgeo_1ms_id0r1_memory_context_audit.json` and reproduced in
`docs/codex/audits/rgeo_zgeo_1ms_id0r1_memory_context_audit_result.json`.
No NR2R1 holdout, server raw, model, controller or optimizer was read or run.
The eight records remain consumed design evidence and are forbidden for
fitting, calibration, holdout, fixtures, expert data or controller safety.

## What the full window shows

All six state32 absolute R/Z responses are small: the largest is
`0.0127813 mm`. The largest response anywhere in states21--32 is
`0.0472375 mm`. Nevertheless the tails are non-monotone: every arm has at
least five R/Z-norm turning points, and p04-minus has 15. Its states21--32
maximum is `0.8700` of its earlier peak even though its state32 ratio is only
`0.1631`.

Therefore neither a single endpoint nor literal decay below a fixed fraction
of the peak is a valid certificate of finite memory order. ID-0T1 remains a
frozen FAIL under its own preregistered gate; this audit does not weaken or
rewrite it. The forward design decision is instead:

1. validate recursive prediction over the complete declared horizon;
2. carry a stable low-order persistent and damped-oscillatory latent state;
3. retain a nonzero uncertainty floor for unresolved tail/context effects;
4. recenter every decision on the exact current R_geo/Z_geo/Ip observation.

No numerical latent order is selected from these consumed records. Candidate
real and complex-conjugate stable modes must be compared only after fresh
development data exist.

## Why model fitting is still premature

The records contain only the canonical 1100 ms source anchor. The maximum
same-time R/Z spread of the six signed arms is about `0.101 mm` at state3 and
falls to about `0.027 mm` in two-axis span at state16. Under the descriptive
matching scales `0.1 mm / 0.1 mm / 20 A`, the nearest different-time,
different-history pair has normalized squared distance `10.986`, driven by a
`0.319 mm` Z difference. There is no matched-position/different-time contrast
at that scale.

Thus existing data can describe source-local pulse response and small latent
tails, but cannot identify position dependence separately from absolute time
and arrival history. It cannot decide between a global map, LPV scheduling,
local mixtures or recurrent residuals.

## Prospective model backbone

The next model comparison, after new data gates pass, is constrained to:

```text
exact Card15 / issued / applied / readback / queue semantics
    + time-indexed nominal q0 evolution
    + stable low-order latent action-response state
    + continuous context scheduling in R_geo, Z_geo, Ip and R_geo-R_mid
    + optional small GRU/TCN residual only after a grouped fresh-data gain
```

Current and past R_geo/Z_geo/Ip are exact observations, not belief variables.
Belief and uncertainty cover latent TSC memory, future response and model
mismatch. The model must consume actual 14-dimensional Card15 vectors or a
prospectively frozen low-dimensional virtual-actuator coordinate; sign labels
are not sufficient.

## Next stage

Before fitting any model, run a separately frozen ID-1A small-HFS context and
anchor pilot. It must create fresh, prospectively usable development data with:

- repeated same primitive at multiple issue times;
- matched-clock siblings with different controlled prefixes/positions;
- near-matched current R_geo/Z_geo/Ip with different causal histories;
- q0 baselines matched to every context;
- both signs, exact return/cumulative semantics and complete tail windows;
- whole-prefix family grouping and data-role separation.

ID-1A is TSC-only empirical identification, not controller-grade safety. It
may expose a bounded, declared set of simulator transitions, but cannot use
its own outcomes to certify current-action safety, recovery or deployment.
If it cannot produce useful position/history contrasts above repeatability and
Card15 response floors, the project must pause before model fitting and
redesign anchor construction rather than train a larger network.
