# B99.2 fast 10ms extrema from-scratch package

## Main changes from B99.1

1. Full action authority from the beginning:
   - `actor_output_scale = 1.0`
   - no actor output scale schedule
   - with `dt_ms=10` and `current_slew_a_per_ms=0.3`, every coil channel can use the full `+-3 A/step` slew allowance.

2. Faster parallel sampling:
   - `num_tsc_workers = 192`
   - `ray_num_cpus = 208`
   - assumes the user has raised `nofile` and `nproc` limits.

3. Low probe overhead:
   - deterministic fixed probe every 100 iterations
   - stochastic probe disabled
   - online local grid probe disabled
   - final deterministic fixed + final 3x3 grid eval are run once at shutdown.

4. Time curriculum simplified:
   - stage0: 500 ms reach / 650 ms episode / 70% fixed
   - stage1: 400 ms reach / 600 ms episode / 50% fixed
   - B99.1 300 ms stage2 refocus is removed.

5. Compact boundary extrema observation added, contact omitted:
   - R_left, R_right, Z_bottom, Z_top
   - R_center, Z_center, boundary_width, boundary_height
   - boundary_valid
   - no contact side, contact point, or limiter regime features.

6. Constrained part softened:
   - cost-Q softplus kept
   - lower dual max/lr and slower warmup/ramp
   - action minimization is not allowed to dominate early training.

7. Timing diagnostics added:
   - rollout collection, ray wait/get, learner update, actor sync, eval/probe timing
   - worker fragment and env-step wall-time summaries.


## GEQDSK boundary-source clarification

The uploaded sample GEQDSK shows the standard post-qpsi integer pair `nbbbs limitr`.
B99.2-gfilefix treats the first outline (`nbbbs` points) as the plasma boundary
for compact extrema observation and the second outline (`limitr` points) as the
limiter/wall trace.  The parser exposes explicit keys `boundary_R/Z` and
`limiter_R/Z`, while preserving old aliases `xplot/zplot` and `rwall/zwall`.
The RL observation uses only the plasma boundary (`boundary_R/Z`) and never uses
`limiter_R/Z` or `rwall/zwall` for extrema.
