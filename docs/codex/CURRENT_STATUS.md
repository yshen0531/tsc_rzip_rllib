# Current status

## Stage4.2R1 R1c certified; Stage4.2R2 is active

Status timestamp: 2026-07-30 Asia/Shanghai

Local identity at the R1c execution checkpoint:

```text
branch              = codex/stage4_2r1-forensics
code commit         = 4ff8a1d
controller_revision = true_tsc_plant_restart_action_replay_v42r1
package_revision    = r42r1c_terminal_wire_telemetry_resume_v4
```

R1c was installed after staging validation and 428/428 server tests.  The
existing R1 run was resumed without changing its experiment IDs, selected
expert digest, controller revision, action semantics, matrix, checkpoint, or
formal contract:

```text
remote run = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
remote log = /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_070023.log
driver PID = 1217510 (finished normally)
backend    = ray
workers    = 128
```

Observed real execution:

- capture: 18 actors and 18 concurrent `gotsc` processes;
- restart: 18 fresh actors and 18 concurrent `gotsc` processes;
- capture raw: 18/18, success 18/18;
- restart raw: 18/18, success 18/18;
- snapshot cases: 18/18;
- snapshot payload files: 144 plus 18 manifests;
- complete log traceback count: 0.

Independent server-side postprocessing read all raw source/capture/restart
JSON.GZ and every snapshot payload.  It did not trust the saved verdict:

```text
strict run JSON/JSON.GZ                    = 114/114
selected source raw size/SHA-256           = 18/18
capture visible equality to source         = 18/18 exact
capture source-action equality             = 18/18 exact
checkpoint elapsed                         = 200 ms
snapshot absolute TSC time                 = 1300 ms
snapshot manifest/hash failures            = 0
snapshot 14-coil difference after turns    = 0 A
snapshot 48-wire difference                = 0 A
fresh restart visible suffix difference    = 0
fresh restart 48-wire suffix difference    = 0 A
fresh restart action difference            = 0
recombined/source visible difference       = 0
formal contract pass                       = 18/18
minimum formal signed margin               = 1.04569209997685e-05
minimum case                               = RZ_p10_m10, delay 0, slew 0.9
controller checkpoint loaded               = 0/18 by R1 design
```

The snapshot folder name `1300ms` is the absolute TSC clock:
`1100 ms + 20 * 10 ms`; it is exactly the preregistered 200 ms elapsed
checkpoint.

The complete R1c tree was downloaded before the user changed the evidence
transfer rule.  It has 261 files and 2,134,623,716 bytes.  Remote/local
SHA-256 comparison is 261/261 with missing 0, extra 0, mismatch 0.  For all
subsequent large result trees, process raw evidence directly on the server
with the existing virtualenv and download only compact audit JSON/CSV,
manifests, hash inventories, and logs.

## Classification

- Runtime/environment errors: none in R1c.
- Packaging/deployment/import errors: none; staging and installed validation
  passed.
- Raw/snapshot integrity errors: none across the authenticated finite matrix.
- Statistics/reporting errors: saved capture/restart result rows exactly match
  independent recomputation.
- Design limitation: R1 deliberately replays fixed expert actions and restores
  no observer, integrator, previous correction, pending delay queue, or
  trusted calibration controller state.
- Real plant-restart conclusion: authentic `sprsina` restart is bit-exact for
  visible state, all 14 coil channels, and all 48 wire currents over the full
  same-action suffix in all 18 finite clean cases.
- Control conclusion: the original 250/350 and 270/370 ms contract is
  preserved 18/18, but the minimum source margin remains razor-thin and no
  robustness beyond the frozen finite grid is implied.

## Active next step

Stage4.2R2 is active.  It must persist and restore controller state on the
certified R1 plant bank and recompute actions online.  Merely storing or
replaying the source suffix is not an acceptable controller-restart test.

The first R2 gate is same-source exact replay with:

- causal measurement/observer history;
- integrator;
- previous correction;
- pending physical delay queue;
- trusted calibration token and modeled delay/slew;
- explicit controller phase and source fingerprint;
- no future measurement or future action in the checkpoint.

Only after exact same-source controller restart may the project advance to
matched-visible/different-hidden-history tests.  BC, DAgger, and residual RL
remain blocked.
