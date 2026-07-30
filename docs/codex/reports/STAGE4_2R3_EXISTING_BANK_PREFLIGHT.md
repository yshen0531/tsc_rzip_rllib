# Stage4.2R3 existing-bank pair feasibility audit

Date: 2026-07-30 Asia/Shanghai

## Conclusion

The certified R1/R2 bank cannot supply a scientifically valid
matched-visible/different-hidden-history pair. A dedicated authentic TSC
state-generation phase is required before the R3 control gate.

This is an experimental-design/source-coverage result, not a controller or
plant failure.

## Evidence

The read-only server audit used:

```text
source:
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619

audit tool SHA-256:
312d624efffbc3ce7218c2771a702c52ff68b4b391fad200cb6b907fcbf9be94
```

Coverage and integrity:

```text
capture raw                         18
unique target/delay/slew keys       18
histories per key                   1
snapshot manifests                  18
snapshot payloads                   144
input files hashed                  180
input bytes                         2,134,076,925
inventory digest                    d08709393c321582e6caef39043113319b5afcb31e79b6360c4be51b69531b70
within-key candidate pairs          0
valid existing R3 pairs             0
```

Every capture raw parsed successfully, every snapshot manifest passed, every
payload size/SHA-256 matched, and each snapshot wire vector exactly matched
the corresponding raw checkpoint telemetry.

There are 72 same-target cross-key diagnostic comparisons. They are not
eligible pairs because their future actuator semantics differ. They also fail
the fixed visible-matching gate, so there is no accidental near-match that
could justify a narrower existing-bank test.

## Classification

- Runtime/environment error: none.
- Deployment/package error: none in the audit.
- Raw/snapshot corruption: none.
- Statistics/reporting error: none detected.
- Experimental-design limitation: one history per future-semantics key.
- Observer/control result: not run.
- Formal contract result: not run.

The first remote preflight process-filter expression was split by
Windows/SSH quoting. It was read-only and did not affect this audit. The
actual audit was launched from a transferred script that passed `bash -n` and
whose local/remote SHA-256 values matched.

## Decision

Proceed with the fixed state-generation grid in
`STAGE4_2R3_PREREGISTERED_DESIGN.md`. Do not pair different delay/slew cases,
do not edit hidden currents, and do not relax the matching or hidden-state
thresholds.
