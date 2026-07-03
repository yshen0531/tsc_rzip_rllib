# B99.3 fast-runtime-only hotfix

This package is based on B99.2 gfilefix.  It keeps the same RL/control design and changes only the runtime/diagnostic side plus worker count.

## Kept from B99.2

- Goal-conditioned constrained MPO from scratch.
- 10 ms command period.
- Coil slew limit remains 0.3 A/ms, therefore ±3 A per coil per RL step.
- `actor_output_scale = 1.0` from the start.
- Stage0/Stage1 curriculum only; no 300 ms Stage2.
- Full target-grid probe remains disabled during training; final evaluation still runs fixed/grid checks.
- Compact boundary extrema are still used; contact/regime features are still disabled.
- GEQDSK boundary semantics from the gfilefix are preserved: compact extrema are read from `nbbbs` plasma boundary points (`boundary_R`, `boundary_Z`), not from limiter/wall points.

## Main changes

### 1. 224 workers

`configs/mpo_b99_3_fast_runtime_only_10ms_extrema_224worker.json` now uses:

```json
"ray_num_cpus": 240,
"num_tsc_workers": 224,
"num_cpus_per_tsc_worker": 1
```

This leaves CPU headroom for the driver, raylet, learner, OS, logging, and final evaluation.

### 2. Runtime-only TSC file flow

`configs/tsc_low_field_side_118_runtime_only.json` enables:

```json
"runtime_only_fast_mode": true,
"save_step_artifacts": false,
"save_artifacts_on_error": true,
"save_artifacts_every_n_steps": 0
```

Normal training no longer archives a full `geqdsk/outputa/sprsina/sprsoua/...` folder for every RL step.  TSC still writes current runtime files in each worker's private `runtime_tsc_dir`, and RL still reads the current `runtime_tsc_dir/geqdsk` immediately to compute boundary extrema.

Restart state is rolled forward inside the runtime directory using the safe first-version policy:

```text
runtime/sprsoua -> runtime/sprsina  (copy2, not rename)
```

No symlink workspace is used in this version.

### 3. Error artifacts only

If `gotsc` fails, output collection fails, restart update fails, or output is abnormal, the current runtime files are copied to an error artifact directory under the current episode directory.  Normal successful steps are not archived.

### 4. More timing diagnostics

Worker rollout fragments now aggregate numeric info fields for:

- `runner_timing/*`, including TSC subprocess and runtime file operations.
- `boundary_*`, including `boundary_valid`, `boundary_num_points`, and extrema.
- `runtime_only_fast_mode`.

The driver now logs clearer timing fields:

- `timing/learner_total_s`
- `timing/learner_train_s`
- `timing/learner_sample_batch_s`
- `timing/learner_update_call_s`
- `timing/worker_param_rpc_s`
- `timing/pipeline_wait_s`

The older `timing/learner_update_s` and `timing/actor_sync_s` are kept for backward compatibility, but prefer the B99.3 names.

The learner `update()` return now includes coarse internal timing fields, reported under `learner/timing_*` in the training JSON/CSV.

### 5. Warmup RPC reduction

During replay warmup, if there is no actor update and no parameter change, workers are no longer synchronously called every iteration just to set the same action scale.  This avoids misleading pipeline-wait timing before learning starts.  Set `parallel.force_warmup_param_sync=true` to restore the old behavior.

### 6. Startup CPU diagnostics

The run script prints `nproc`, `nproc --all`, `Cpus_allowed_list`, `taskset`, and `SLURM_CPUS_PER_TASK` instead of a single misleading `CPUs=...` value.

## What this version intentionally does not change

- No symlink-based thin workspace.
- No persistent TSC daemon.
- No 20 ms control-period experiment.
- No change to learner update count.
- No reward/R/Z patch.
- No contact features.
- No full 36-point boundary observation.
