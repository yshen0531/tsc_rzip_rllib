# R_geo/Z_geo 1 ms ID-2W1 sustained branch result

Date: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w1-sustained-branch-campaign-v1`

Plant source revision: `eb36c12e8ff5d97a8aefdddce31a00948aca7169`

Final route:
`ONE_MS_ID2W1_SUSTAINED_BRANCH_CONTROL_UTILITY_FAIL_REDESIGN`

## Outcome

ID-2W1 completed all six prospectively frozen real-TSC branches. Execution,
Card15/current semantics, the common causal prefix, raw inventory, and the
separate full-raw recomputation pass. The campaign produced 288/288 verified
plant advances, 294 states, and 1,470 required artifacts totalling
17,314,519,656 bytes. The inventory digest is
`1d4fecf043a4fa41839c947bb5915b43e6d35e3f44a3912462b745783291457e`.

The scientific action-grammar gate fails. This is not a runtime, package,
TSC, Card15, current, paired-boundary, raw-data, prefix, or reporting failure.
It is also not a controller, hold, recovery, waypoint, global-authority, or
reachability result.

## Measured branch response

All responses below are relative to the matched paused/catch-up baseline.

| branch | peak R/Z norm (mm) | state-25/26 median (mm) | state-25/26 cosine | max paired Ip (A) | terminal max R/Z (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| p04 plus | 0.9330 | 0.5004 | 0.4625 | 310.30 | 0.3901 |
| p04 minus | 0.8876 | 0.8014 | 0.9999 | 308.84 | 0.3624 |
| p07 plus | 1.0963 | 0.5900 | 0.5100 | 166.08 | 0.3845 |
| p07 minus | 0.9899 | 0.8267 | 1.0000 | 162.86 | 0.3648 |

The p04-plus persistence criterion fails because its consecutive-state cosine
is below the frozen 0.5 floor. All arms pass the paired-Ip and bounded-tail
gates.

At common state 25, the four measured vectors do positive-span the plane in
the finite 64-direction audit: maximum angular gap `169.715 deg` and weakest
best progress `0.087061 mm`. At the equally primary state 26 the geometry
collapses: maximum angular gap `230.348 deg` and weakest best progress
`-0.166962 mm`. State 27 is also one-sided and was prospectively forbidden
from repairing a state-25/26 failure. Therefore transient timing cannot be
silently promoted to sustained two-axis authority.

## Absolute trajectory and route implication

The uninterrupted p03 nominal reaches a terminal source-relative R/Z distance
of `26.8068 mm`; pausing at level 18 and catching up later reaches
`29.1251 mm`. The pause therefore has a material transport cost. The four
returned residual branches finish at `28.9463--29.3661 mm`, so none repairs
that cost. This confirms that p04/p07 depth-6 branches are measurable and can
be useful timing-dependent deviations, but this pause/ramp/hold/return grammar
is not a persistent general control allocation.

The next finite discriminator moves back to the selected p03 transport axis.
Existing evidence only exercised the stride-one staircase through level 31;
the absolute current lattice permits a much longer exact continuation. A
single bounded, prospectively frozen extended-p03 development trajectory will
measure whether continued transport approaches, crosses, or departs the
source corridor and where a future slowdown/braking/hold schedule should be
placed. It must retain exact 1 ms observation, Card15/slew/current/Ip/paired-
boundary gates and stop-after-successor semantics. It is route/design evidence
only and cannot itself qualify a controller.

## Reporting-only independent-audit correction

The first independent audit incorrectly interpreted each retained raw state
directory's final `inputa` as the command active on arrival. The runner writes
the outgoing issue into that directory, so branch state 19 appeared to differ
even though the preceding issue-18 command and all physical prefix fields were
identical. The pre-correction audit is preserved unchanged.

Commit `ec0b9891` reconstructs arrival-active Card15 fields from the preceding
raw issue. It changes no raw data, action, threshold, route, or scientific
metric and reruns no TSC. Server tests pass `10/10` focused and `346/346`
one-ms tests. The corrected independent audit passes with no failures and
reproduces the primary route and all metrics exactly.

## Evidence

- Primary result:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w1_20260819_eb36c12e/result.json`
- Corrected independent audit:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w1_20260819_eb36c12e/independent_raw_audit.json`
- Preserved initial audit:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w1_20260819_eb36c12e/independent_raw_audit_pre_hotfix.json`
- Six compact trajectories and the offline preflight are stored in the same
  tracked audit directory.
- Frozen design:
  `docs/codex/reports/RGEO_ZGEO_1MS_ID2W1_SUSTAINED_BRANCH_CAMPAIGN_DESIGN.md`
