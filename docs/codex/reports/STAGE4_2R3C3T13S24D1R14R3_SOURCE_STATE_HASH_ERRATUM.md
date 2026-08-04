# D1R14R3 source-state hash erratum

Recorded: 2026-08-04, after the first zero-TSC D1R14R3 audit stopped at its
source authentication gate and before any corrected audit execution.

## Error

The frozen D1R14R3 design and initial config transcribed the D1R14R2
`stage_state.json` SHA-256 as:

```text
46552980d1514eec75fc5df9b76b7c9c4c49aa0ec13f180dc7fdc3113d1468c6
```

That value is incorrect. The authentic immutable file SHA-256 is:

```text
46552980c0cdc8e97968ac18a04cbb5d64f2cdf2885b9df121d9db86c2a37d07
```

## Evidence predating the failed audit

The corrected value is not selected from a response outcome. Before the
D1R14R3 design existed, checkpoint `73c5811` committed both the compact
D1R14R2 `stage_state.json` and `LOCAL_COMPACT_INVENTORY.json`. The latter
records the corrected SHA explicitly and states that local size/SHA matched
the remote compact manifest. Direct hashing of that committed local file and
of the still-immutable remote source file gives the same corrected value.

The first D1R14R3 primary and structurally separate independent executions
both calculated the corrected value from the remote source. Their other
source hashes matched exactly:

```text
final_result.json
  3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a
server_independent_forensics_v1.json
  68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df
posthoc_sign_split_diagnostic_v1.json
  2a843ca4f9d05e1f5fbb7036313652fce2093062bf7a4b1fa969ad599f406f61
raw inventory
  72 files / 2,254,876 bytes
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
```

The complete frozen R2 forensic also re-passed all 72 safety rows, eight
snapshots, 64 issue actions, 64 cancellations, source prefixes, logs, and the
original R2 geometry-failure reproduction. No source file was repaired,
rewritten, resumed, or relabelled.

## Permitted correction

The D1R14R3 config may replace only the erroneous expected
`stage_state_sha256` with the authentic value above and must authenticate this
erratum by path and SHA-256. All response formulas, thresholds, counts,
routes, source files, raw bytes, implementation independence, and scientific
interpretation remain unchanged.

The first output remains frozen as
`SIGN_SPLIT_RESPONSE_FEASIBILITY_SOURCE_FAIL_NO_TSC`. A corrected audit must
write a fresh output directory. Because D1R14R3 executes no controller,
plant, Ray, gotsc, or TSC, this is a reporting/source-fingerprint hotfix and
not an experimental resume.

