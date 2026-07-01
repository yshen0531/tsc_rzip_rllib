# B99.2 run notes

Run from the project root:

```bash
unzip -o b99_2_fast_10ms_extrema_clean.zip -d .
chmod +x run_train_b99_2_native.sh run_train_b99_2_nohup.sh run_probe_b99_2_modes.sh
./run_train_b99_2_nohup.sh
```

Monitor:

```bash
tail -f logs/nohup/latest_b99_2_train.log
```

Expected first-screen checks:

- `ulimit -n=1048576`
- `ulimit -u=262144`
- `num_tsc_workers = 192`
- `ray_num_cpus = 208`
- `obs_dim` should be 9 larger than the corresponding B99.1 env obs plus the same 3 goal features, if boundary points are available in the env observation construction.

Boundary extrema caveat:

B99.2 does **not** invent boundary points.  It uses `state[boundary_R/Z]` if present, otherwise `gfile[xplot/zplot]` if available.  If no reliable boundary-like trace exists, `boundary_valid=0` and all extrema features are zero.  Contact features are intentionally not included.

Evaluation policy:

Training does not run repeated full grid probes.  A final deterministic fixed probe and final 3x3 target grid are run once at shutdown and written to `final_eval_summary.json`.


## GEQDSK boundary-source clarification

The uploaded sample GEQDSK shows the standard post-qpsi integer pair `nbbbs limitr`.
B99.2-gfilefix treats the first outline (`nbbbs` points) as the plasma boundary
for compact extrema observation and the second outline (`limitr` points) as the
limiter/wall trace.  The parser exposes explicit keys `boundary_R/Z` and
`limiter_R/Z`, while preserving old aliases `xplot/zplot` and `rwall/zwall`.
The RL observation uses only the plasma boundary (`boundary_R/Z`) and never uses
`limiter_R/Z` or `rwall/zwall` for extrema.
