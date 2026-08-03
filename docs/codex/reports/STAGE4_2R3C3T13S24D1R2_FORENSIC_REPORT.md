# Stage4.2R3c3T13S24D1R2 final forensic report

Date: 2026-08-03/04 Asia/Shanghai  
Result: `GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED`

## 1. Exact identity

```text
local branch             codex/stage4_2r3c3t13s24-sequential-transition
execution package commit 9e6bba2
implementation commit    9a8ce4d
reporting audit commit   d239e28
package revision         r42r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_v2
controller revision      sequential_amplitude_coded_card15_probe_v42r3c3t13s24d1r2_v1
normalized spec digest   50832fadb244bbd338bd7c5cd5f9ff136eedce498d920f416458516d7655648f
```

Relevant local hashes:

```text
PACKAGE_MANIFEST.json  9b1f9219fd45b98f93b721345e5f741607092ab02b6ebc5a1a0b76e99ccb5bfb
SHA256SUMS             92d7f6838ec9fe5b6e2bbed0ee40ef23f6164b5d1da89fe40f049c128e7beb37
config                 13d8634276fb0215eaf798d4a9ba17db9b15e83eadf4df97eedad17c1146ae34
execution module       bed7c39d4354116bb2e3464f4a14f9a8f6b45d378986a0d617b8e9c9c03ec5d1
prospective forensics  4108c002d404364db1caf6b5cb620ec940869d9a9deacd485164ad2dc50d50aa
retrospective audit    4ec52f535176f43c0a716eb34564970c2cd76addbbb7e27c7f8ad3858d202e06
frozen design          34107fd77ff709de03e91566619951b0b649eb0073fb9bd96551f67033fc50ae
```

The execution package and controller were not changed after TSC began. The
later `d239e28` file is an undeclared reporting-only audit: it is outside the
519-file execution manifest, authenticates the frozen v2 package and raw
inventory, and does not alter run state, raw, actions, or verdict.

## 2. Server paths

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

clean staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s24d1r2_transfer_clean_9e6bba2_lf

run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r2_runs/
  stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2

complete rollout log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r2_rollout_20260803_160426_9e6bba2_v2.log
```

The complete-log SHA-256 is
`89b23c022580ec70fb4df1d8367759685b610ccd319eb59b6383a3c14e5321ff`.

## 3. Validation and deployment incidents

Local validation used only `venv/Scripts/python.exe`:

```text
focused D1R2 tests after snapshot fix                 8 / 8
D1R2 + S24 + D1R1 empty-deploy tests                23 / 23
all strict JSON files                               6142 / 6142
full Windows suite                         546 pass / 27 errors
```

The 27 Windows errors are the unchanged Unix `resource` import limitation;
there was no new failure. Server staging and installed validation used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`:

```text
manifest files / SHA256SUMS             519 + 1
initial pyc/__pycache__                        0
checksum verification                    519 / 519
focused tests                               23 / 23
full server suite               940 / 940, 1 skipped
```

Two pre-experiment integration incidents were contained:

1. The first zero-plant preflight reused an S21 helper whose aggregate
   expected 40 contexts. All selected rows were actually 18/18, but the old
   aggregate returned false. Package v2 added a D1R2 18-context subset
   aggregation. No Ray, TSC, plant step, or raw ran in that attempt.
2. One transferred checksum file had Windows CRLF and a later clean transfer
   initially lacked Unix execute bits. Checksum validation stopped both
   attempts before tests or installation. A new LF-clean 520-file staging was
   transferred, shell modes were restored, and only manifest-listed files
   were installed. Neither incident touched experiment semantics.

The successful zero-plant preflight recorded 54 specs, 18 contexts, snapshot
18/18, zero raw, and `real_tsc_executed=false` before the same run identity was
resumed for rollout.

## 4. Raw inventory and integrity

```text
expected / actual raw                         54 / 54
raw total bytes                               3,078,383
canonical raw inventory digest
  eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83
strict parse / exact identity                 54 / 54
snapshot authentication                       18 / 18
state/manifest/final/log consistency              pass
runtime or audit failures                          0
```

All raw and snapshots remain on the server. Only 840,230 bytes of compact
JSON/log evidence were copied directly, uncompressed, to
`artifacts/server_audits/stage4_2r3c3t13s24d1r2_20260803_160327_9e6bba2_v2`.

## 5. Corrected all-prefix execution counts

The prospective internal and independent audits correctly selected the FAIL
route, but their top-level event totals included only the 45 full successes.
They therefore reported 180 issue/cancel events and a maximum successful
cancel increment of 0.2162433071. This is a reporting-coverage bug because
the frozen design required all 216 attempted cancellations to be summarized.

The reporting-only audit read every raw again and found:

```text
full-horizon successes                              45
structured safe stops                                9
restart exact, including failure prefixes       54 / 54
causal phase traces                              54 / 54
exact eight-event calibration                    54 / 54
issue gates                                     216 / 216
successfully returned/applied cancellations     207 / 207
unapplied failed cancellation attempts                 9
total cancellation attempts                     216 / 216
0.24-margin pass / fail                           207 / 9
original 0.25-cap pass / fail                     211 / 5
forbidden controller-use rows                           0
maximum current utilization                         0.392
maximum successful cancel increment          0.2162433071
maximum attempted cancel increment           0.2787208138
```

The retrospective audit SHA-256 is
`d6ea5fed0aa943c16ce850b80c9786556a9cd5e0de26a2e19d7a18d5d88914ec`.
It records `prospective_route_changed=false` and
`forensic_recomputation_passed=true`.

## 6. Exact failure localization

Every failure occurred before applying the task-step-18, slot-3 cancellation.
Each partial raw has 19 states and 18 returned controller rows, proving the
failed action did not advance the plant. All four issues and the first three
cancellations had already passed.

```text
pair/history                                      sequences     attempted increment
p5_q2_a0p750_gap4_settle4 / plus_first            6,10,18      0.2707613--0.2787208
p9_q1_a0p900_gap4_settle4 / minus_first           6,10,18      0.2409720--0.2523598
p9_q1_a0p900_gap4_settle4 / plus_first            6,10,18      0.2439688--0.2537396
```

All nine were the final `++--=0.290` exact stored-center return. Four were
inside the original 0.25 cap but outside the added 0.24 margin; five exceeded
both. Exact Card15 targets, exact-zero target-jump bookkeeping, total action,
current utilization, no saturation, and no clipping otherwise passed.

## 7. Scientific classification

- Runtime/environment error: **none**.
- Packaging/import/deployment error during the real run: **none**.
- Raw/snapshot corruption: **none**.
- Statistics/reporting error: **one post-result aggregation-coverage bug**;
  corrected without changing the FAIL route.
- Design flaw: **yes**. D1R1 evaluated issue/cancel constructions at a frozen
  S21 baseline. It did not model the sequentially evolved plant and underlying
  feedback center at the fourth cancellation. D1R2 was the prospective real
  TSC test of that missing dynamic condition and rejected it safely.
- Real control/plant conclusion: the bounded one-step stored-center
  cancellation primitive is unsafe for 9/54 selected sequential contexts.
  This is not plant unreachability and is not a reliable-MPC result.

Formal tracking passed only 8 of the 45 completed probe trajectories, but it
was preregistered diagnostic-only: the trajectories deliberately contain
identification probes, and the nine safe stops did not reach the formal
horizon. It is not used as a changed gate or as an MPC verdict.

## 8. What is frozen and what remains unvalidated

D1R2 is frozen as a genuine action-schedule design FAIL. It may not resume or
rerun any of the 54 identities. Its successful and partial raw remain forensic
development evidence and are forbidden from model fitting and expert data.

No full replacement identification, sequential transition model, robust MPC,
unseen target, continuous delay/gain/slew, plant mismatch, sensing noise,
disturbance recovery, independent long hold, expert dataset, BC, DAgger, or RL
has been authorized. The 250/270 ms arrival and 350/370 ms hold contract was
unchanged.

## 9. Next action

The next route must change the failed physical action semantics under a fresh
identity. The immediate development step is a zero-new-TSC causal replay on
all 54 D1R2 raws that constructs a bounded two-step Card15 return only when a
direct cancellation would exceed 0.24. It must keep every returned increment
within a preregistered sub-cap, preserve exact telescoping return to the stored
center, and expose no labels or future data. A pass may authorize only a new
real-TSC sentinel over the nine failure contexts. It cannot authorize the full
campaign or MPC.

This route addresses the observed final-cancel mechanism while keeping the
static geometry floor `++--=0.290`; lowering it below 0.290 would knowingly
reintroduce D1R1's 960/960 off-basis failures.

## 10. Commands actually run

- local `compileall`, strict JSON parse, focused/joint `unittest`, full
  `unittest discover`, manifest hash regeneration, and an empty 520-file
  deployment simulation;
- direct `scp -r` of the clean tree, with no archive operation;
- server `sha256sum -c`, `bash -n`, package verifier, focused tests, and full
  tests under the existing virtualenv;
- foreground zero-plant `offline`, followed by the same-identity
  `rollout --resume` through the fixed 54-worker nohup launcher;
- repeated PID/log/raw/gotsc monitoring until the exact driver exited;
- prospectively frozen independent raw forensics and the separate
  post-result all-prefix audit;
- direct download of compact audits/logs only.

No full replacement campaign, MPC execution, training, BC, DAgger, RL, noise,
disturbance, continuous-parameter, or long-hold experiment was run.
