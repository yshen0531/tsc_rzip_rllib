# Stage 1: TSC/RZIP controllability and 100 ms reachability

This package is the first step of the B100 redesign. It does **not** train an RL policy. It answers a more basic question first:

> Under the present TSC start state, 14 CSPF channels, ±current limits, 0.3 A/ms slew, 10 ms control interval, and a 100 ms horizon, what directions are locally controllable and can any constrained open-loop sequence reach the requested R/Z target in the real TSC model?

## What the pipeline does

1. Runs three zero-action baseline trajectories to measure repeatability.
2. At every one of the ten control instants, perturbs each of the 14 TSC-order channels in both signs and at 0.5 and 1.0 normalized amplitudes.
3. Fits `d(R,Z,Ip trajectory)/d(single-turn current increment A)` using all four signed amplitudes.
4. Reports nonlinearity, pre-injection leakage, horizon-dependent ranks, singular values, condition numbers, SVD coil modes, and common/differential pair-mode gains.
5. Computes a local linear 100 ms R/Z reachable polygon under:
   - ±3 A per-step single-turn current increment;
   - cumulative coil-current lower/upper limits;
   - an optional terminal Ip tolerance.
6. Solves constrained late-window tracking problems using 2/3/4/5/6/8 SVD modes and the full 14-D action space.
7. Replays the strongest predicted sequences in the **real TSC environment** at several sequence scales.
8. Produces a Gate-A verdict. The real TSC replay is the source of truth; linear predictions are diagnostic only.

## Default computational load

The scan contains:

- 3 baseline episodes;
- `10 injection times × 14 channels × 2 signs × 2 amplitudes = 560` perturbation episodes.

Total: **563 episodes**, each 10 TSC steps. With 192 workers this is about three waves. Actual wall time is determined by server load and `gotsc` runtime.

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o stage1_controllability_100ms_runtime_only_192worker_clean.zip -d .

chmod +x run_stage1*.sh run_resume_stage1*.sh
./run_stage1_controllability_nohup.sh
```

Monitor:

```bash
tail -f logs/nohup/latest_stage1_controllability.log
cat stage1_runs/latest_stage1_run.txt
```

Immediately stop:

```bash
./run_stop_stage1_now.sh
```

Completed `raw_experiments/*.json.gz` files are written atomically and remain resumable. A hard stop can lose the currently running episodes, but not completed experiment files.

Resume:

```bash
./run_resume_stage1_controllability_nohup.sh
```

## Separate phases

```bash
export STAGE1_RUN_DIR=$(cat stage1_runs/latest_stage1_run.txt)
./run_stage1_analyze_only.sh
./run_stage1_validate_only.sh
```

## Main outputs

Inside the run directory:

- `raw_experiments/*.json.gz`: one atomic file per baseline/perturbation experiment;
- `analysis/response_tensor_dy_per_a.npy`: full time-varying response tensor;
- `analysis/response_fit_quality.csv`: linearity and leakage diagnostics;
- `analysis/horizon_controllability.csv`: rank and singular values versus horizon;
- `analysis/coil_modes.csv`: SVD spatial modes in TSC and display order;
- `analysis/pair_mode_ranking.csv`: U/L common and differential mode gains;
- `analysis/reachable_set_100ms.csv/.png`: constrained local R/Z reachable set;
- `analysis/candidate_summary_linear.csv`: constrained linear predictions;
- `candidate_sequences/*.csv/.json`: optimized current-increment sequences;
- `validation/validation_summary.csv`: real-TSC replay results;
- `validation/gate_a_verdict.json`: machine-readable verdict;
- `STAGE1_REPORT.md`: concise report.

## Gate-A verdicts

- `PASS_TERMINAL_1X`: a real-TSC candidate is within `|R error|≤80 mm`, `|Z error|≤80 mm`, and the configured weak Ip safety band at 100 ms.
- `PASS_REACHED_1X_TRANSIENT`: a real-TSC candidate enters the 1× tube but leaves before 100 ms.
- `PROMISING_REACHED_2X`: a candidate reaches the 2× tube.
- `PROMISING_LARGE_REDUCTION`: no tube entry, but normalized R/Z distance decreases by at least 50%.
- `FAIL_OR_INCONCLUSIVE`: the present local model and constrained candidates do not produce enough real-TSC progress.

A failure is **not** a mathematical proof of global uncontrollability. It means that local identification around the present baseline plus the tested constrained sequence family is insufficient. That result determines whether the next step should change actuator limits/horizon or move to iterative nonlinear trajectory optimization.
