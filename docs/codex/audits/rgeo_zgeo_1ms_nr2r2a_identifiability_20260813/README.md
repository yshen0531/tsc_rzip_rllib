# NR2R2A identifiability audit evidence

Stage identity:

```text
rgeo-zgeo-1ms-nr2r2a-identifiability-audit-v1
```

Final route:

```text
ONE_MS_NR2R2A_IDENTIFIABILITY_AUDIT_COMPLETE_SOURCE_BASELINE_RECOVERY_DESIGN_REQUIRED
```

This was a local, read-only, zero-fit audit of the 28 previously retained
NR2R1 development/calibration compact records.  It read no holdout record,
server raw or server state.  It ran no server command, TSC, plant advance,
snapshot/replay, model fit, training, controller or optimizer.

The frozen input inventory remains:

```text
files                                      28
bytes                               2,431,302
ordered inventory SHA-256
98f6bd1992b9681ec548e4bbc8f1f6b6c7332309522a81e961c8be57edbd3c49
```

Primary and structurally independent recomputation agreed under the frozen
`1e-12` absolute/relative numeric tolerance.  Their full compact outputs were
generated under `.codex_tmp/nr2r2a_audit_v2/` and remain untracked; tracked
`RESULT.json` retains all load-bearing values and exact output identities:

```text
PRIMARY.json SHA-256
8cc6af465d9f7152d2f5f2756181ac2a41db96dd612855bf8fa87205b06e249c

INDEPENDENT.json SHA-256
d481f0aae99ef42f44fcd26f31b8c318151d6ffc433f16149d041c566a52f27b
```

## Load-bearing conclusions

- all 28 trajectories begin at one physical state and all 476 states are HFS;
- there is no independent full-horizon all-q0 trajectory;
- no target moves cumulatively outside `q0 +/- 0.3 A`;
- without any history padding, development has full column rank through lag
  7 for both issued-increment and q0-offset coordinates, but lag 8 is only
  `94/112`;
- calibration has full column rank only through lag 3 for issued increments
  and lag 2 for q0 offsets; its lag-8 ranks are `40/112` and `41/112`;
- the old 8-frame ARX left-pads by repeating its first frame, contains the
  absolute `step/16` feature and has no explicit stable passive/innovation
  state; and
- position, time and arrival history are not factorizable in this campaign.

The rank numbers are dataset support measurements, not physical memory
cutoffs.  The 16 ms records still provide only a lower bound for prospective
tail measurement.

## Reporting-only erratum found by NR2R2A

The previous post-NR2R1 tracked descriptive `RESULT.json` reported the maximum
signed-pair Ip half-difference as `22.50995 A`.  Direct primary and independent
recomputation over every declared pair and all 17 states gives
`30.14075 A`, at development pair 0, horizon 6.  R/Z values and all route/
architecture conclusions are unchanged.  This is a derived-summary error;
no raw or compact record is changed.

## Reproduction

Using only the project virtual environment and the existing locally retained
records:

```powershell
.\venv\Scripts\python.exe scripts/rgeo_zgeo_1ms_nr2r2a_identifiability.py `
  --records-dir .codex_tmp/nr2r1_evidence/records `
  --output .codex_tmp/nr2r2a_audit_v2/PRIMARY.json

.\venv\Scripts\python.exe scripts/rgeo_zgeo_1ms_nr2r2a_independent.py `
  --records-dir .codex_tmp/nr2r1_evidence/records `
  --primary .codex_tmp/nr2r2a_audit_v2/PRIMARY.json `
  --output .codex_tmp/nr2r2a_audit_v2/INDEPENDENT.json
```

Both scripts refuse to overwrite outputs.  A fresh directory is required for
a new reproduction.
