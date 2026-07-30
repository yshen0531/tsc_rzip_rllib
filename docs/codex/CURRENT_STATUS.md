# Current status

## Stage4.2R2 certified; Stage4.2R3 design is next

Status timestamp: 2026-07-30 Asia/Shanghai

Local R2 code identity:

```text
branch              = codex/stage4_2r2-controller-checkpoint
code commit         = 84962ef
controller_revision = persistent_mpc_controller_checkpoint_replay_v42r2
package_revision    = r42r2_persistent_controller_checkpoint_v1
```

Remote identity:

```text
source R1c = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
R2 run     = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250
R2 log     = /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082828.log
backend    = Ray
capacity   = 128
```

## Certified R2 result

R2 persisted causal controller state through the 200 ms checkpoint:
measurement/observer history, integral, previous correction, pending
delay queue, trusted calibration and modeled delay/slew, controller phase,
and fingerprints. Checkpoints contain no future action or measurement.

The offline mandatory gate reconstructed actions without TSC:

```text
checkpoints                        18/18
exact action cases                 18/18
suffix actions recomputed          282
maximum action difference          0
future action replay               0
future measurement use             0
new TSC processes                  0
```

The real phase used 18 fresh controller/TSC processes:

```text
raw rollouts                       18/18
environment success                18/18
controller checkpoint loaded       18/18
online actions exact               18/18
visible restart suffix exact       18/18
full wire-current suffix exact     18/18
formal contract                    18/18
minimum signed formal margin       1.0456920999768471e-05
minimum case                       RZ_p10_m10, delay 0, slew 0.9
```

Independent server-side postprocessing covered all 50 R2 input files
(604,967 bytes, 30 JSON and 18 JSON.GZ) and all 18 source snapshot manifests
plus 144 payload files (2,133,646,442 bytes). Strict parse, source
fingerprints, sizes, and SHA-256 checks passed. Independent metrics agree
with the saved summary.

## Classification

- R2 scientific runtime/environment errors: 0.
- Final package/import/deployment errors: 0.
- Raw/snapshot corruption: 0.
- Final statistics/reporting errors: 0.
- Controller-checkpoint/design failures in the tested matrix: 0.
- Plant-restart fidelity failures in the tested matrix: 0.
- Real formal-control failures in the tested matrix: 0.
- Real conclusion: finite clean same-source persistent-controller restart is
  exact and preserves the immutable formal contract 18/18.

Pre-run/tooling incidents were repaired and did not alter the experiment:

- one Windows-to-remote shell quoting failure during clean deployment;
- a non-idempotent verifier rejection of runtime `__pycache__`;
- an offline-only state/reporting bug that falsely marked an intentionally
  unrun replay phase as failed;
- one postprocessor launch without project `PYTHONPATH`;
- Windows Unicode-path SFTP failure and a later aggregate SCP timeout during
  compact evidence retrieval.

The complete classification and command record are in
`docs/codex/reports/STAGE4_2R2_FORENSIC_REPORT.md`.

## Evidence policy and local compact evidence

No R2 raw JSON.GZ or large snapshot tree was downloaded. Server-side raw and
snapshot evidence remains at the exact run/source paths above.

Local compact transfer:

```text
artifacts/server_audits/stage4_2r2_20260730_082250
files       = 19
bytes       = 185,302
JSON parse  = 14/14
raw/JSON.GZ = 0
```

Tracked compact audit:

```text
docs/codex/audits/stage4_2r2_20260730_082250
```

## What remains unvalidated

R2 does not validate matched-visible/different-hidden history, different
initial state, unseen targets, continuous actuator variation, plant/Jacobian
error, measurement noise, disturbance recovery, or independent long hold.
The minimum formal margin remains razor-thin.

## Active next step

Stage4.2R3 must first preregister and authenticate matched-visible /
different-hidden-vessel-history pairs and different initial states. Hidden
wire state is audit evidence, not an online controller input. Invalid pair
construction, observer/history-identification failure, and real control
failure must be reported separately.

BC, DAgger, and residual RL remain blocked.
