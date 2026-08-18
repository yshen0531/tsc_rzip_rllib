# R_geo/Z_geo 1 ms ID-2V0 control-utility/support audit result

Date: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2v0-control-utility-support-audit-v1`

Source revision: `77372b1f96f66088c78e6ea04f4b4f934d74569d`

Final route:
`ONE_MS_ID2V0_CURRENT_PROBE_CONTROL_UTILITY_INSUFFICIENT_BRANCH_DESIGN_REQUIRED`

## Outcome

ID-2V0 completed its bounded server-side, zero-new-TSC and zero-fit audit.
The primary result and separate-process deterministic recomputation are
byte-identical at SHA-256
`f21c88739acdcd41ed7c1eac7c613e937c3e61c459addf09ac4c1d2e496d193e`.
The independent audit passed and records zero reset, plant advance, TSC call,
model fit, calibration read, and blind-holdout read.

The decision is `branch_design_required`. Adding four more arrival histories
for the same p04/p07 two-issue pulse grammar is no longer the automatic next
step. The existing grammar remains valid as a local excitation, but it has
not demonstrated persistent or distinguishable control utility around the
moving nominal.

## Server validation and execution identity

After the exact tracked U1/U2 compact evidence closure was installed, the
focused suite passed `8/8` and the full one-ms suite passed `336/336` in
`133.181 s`. An initial launch attempt stopped in the shell with
`Permission denied` because direct copy did not preserve the launcher's
execute bit. It ran no Python analysis and no TSC. The execute bit was then
restored on that exact launcher and the stage ran once with the source
revision above. This is a deployment-permission correction, not a scientific
rerun or changed identity.

## Support decomposition

The frozen leave-one-family-out support rule gave:

| held family | distance | threshold | supported |
| --- | ---: | ---: | --- |
| `u00` | 6.212171 | 11.786011 | yes |
| `u02` | 968.176112 | 11.197205 | no |
| `u04` | 8.559689 | 13.093826 | yes |
| `u06` | 5.785521 | 12.153765 | yes |

For `u02`, the pole-0.25 action-memory block accounts for `99.5057%` of
the squared normalized distance and the pole-0.5 block for another
`0.4085%`. This identifies where the frozen support metric rejects the
corner. It does not by itself isolate arrival pace, position, passive-current
memory, or a physical causal mechanism.

## Measured control utility

All dimensions below are recomputed from matched baseline/probe trajectories.

| family | baseline motion at h8 (mm) | max residual at h8 (mm) | residual/baseline | max state-40 residual (mm) | weakest 64-dir h8 progress (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `u00` | 4.547406 | 0.025816 | 0.5677% | 0.017810 | 0.009425 |
| `u02` | 4.483868 | 0.022456 | 0.5008% | 0.017759 | 0.008871 |
| `u04` | 5.238431 | 0.021377 | 0.4081% | 0.018710 | 0.008421 |
| `u06` | 4.275868 | 0.022078 | 0.5163% | 0.018993 | 0.008136 |

Every family failed all three retrospective program criteria while retaining
exact action integrity. The maximum best-versus-second-best action gap over
the 64 direction grid is only `0.01585--0.01621 mm`; all 64 directions in
every family fall inside the frozen `0.02 mm` action-equivalence floor.

`u00` contains the known transient hybrid excursion: the largest branch
reaches about `0.712 mm` at horizon 5, falls to `0.0258 mm` by horizon 8,
and leaves at most `0.0178 mm` at state 40. It is therefore not counted as
sustained authority. The other families remain approximately two-sided but
also decay to the same weak terminal scale.

## Scientific classification

This is a clean retrospective program-decision result. It is not a runtime,
TSC, raw-data, model, controller, MPC, hold, recovery, waypoint, path,
R_mid-crossing, reachability, or plant-safety conclusion. The thresholds are
not transition tubes or formal control bounds.

The result separates two issues that were previously conflated:

1. `u02` has a real causal-feature support gap under the frozen metric; and
2. even supported families show too little sustained action effect for the
   current pulse grammar to justify a history-only data expansion.

Consequently the next bounded stage must design a small exact-Card15,
same-prefix, multi-arm sequence campaign whose objective uses absolute
time-resolved R/Z progress, sustained/terminal effect, Ip/current cost, and
an explicit return/resume continuation. It must not revive broad shooting,
silently clip actions, use a transient single-frame peak as authority, or
open the existing calibration/blind families.

## Evidence

- Primary result:
  `docs/codex/audits/rgeo_zgeo_1ms_id2v0_20260819_77372b1f/result.json`
- Independent audit:
  `docs/codex/audits/rgeo_zgeo_1ms_id2v0_20260819_77372b1f/independent_audit.json`
- Frozen design:
  `docs/codex/reports/RGEO_ZGEO_1MS_ID2V0_CONTROL_UTILITY_SUPPORT_AUDIT_DESIGN.md`

