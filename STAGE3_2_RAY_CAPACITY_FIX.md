# Stage3.2 Ray-capacity scheduler fix

## Failure signature

The interrupted run completed all 84-candidate margin waves and the 48-candidate extension screen, then stalled permanently at `108/120` during the first long-hold finite-difference wave.  System CPU remained mostly idle.

## Root cause

The original shared evaluator computed `n_workers = min(requested_workers, pending_candidates)` before the first `ray.init`.  Because the first wave had 84 candidates and the campaign requested 96 workers, Ray was initialized with only 84 CPU resources.  Ray remains at that total capacity for the process lifetime.  A later 120-candidate wave created 96 one-CPU actors.  Twelve actors could never be scheduled.  With modulo task assignment, 84 first tasks and 24 queued second tasks completed, producing exactly 108 saved results; the 12 tasks assigned to actors 84–95 never started.

## Corrected behavior

The new `tsc_rzip_rllib.utils.ray_runtime.ensure_ray_worker_plan` function:

1. initializes a new local Ray cluster with the configured campaign capacity;
2. reads the actual total CPU capacity from `ray.cluster_resources()`;
3. rejects an undersized pre-existing cluster immediately;
4. creates only `min(requested, pending, cluster_cpus)` actors for the current wave;
5. logs requested capacity, cluster capacity, pending tasks, actor count, and whether initialization occurred.

This is deliberately a fail-fast, full-speed policy.  It does not silently fall back to 12 or 84 workers.

## Resume guarantee for the interrupted run

After the old process and Ray instance have been stopped, a resume with 12 missing probes performs:

```text
ray.init(num_cpus=96)
current wave actors=12
completed results reused=108
new probes executed=12
```

The following 24-proposal wave then uses 24 actors on the same 96-CPU cluster, and later 120/150/99-candidate waves use up to 96 actors.

## Scientific invariants

The hotfix does not alter the 30 mm / 0.10 m/s / 10 kA hard gate, 250 ms hold requirement, candidate manifests, SQP equations, finite-difference deltas, target/disturbance scenarios, saved JSON.GZ results, or final-task definition.  It only corrects runtime resource planning.
