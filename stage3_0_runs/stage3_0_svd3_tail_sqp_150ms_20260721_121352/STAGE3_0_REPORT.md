# Stage3.0 extended-horizon tail SQP and MPC-compatible POC

- Source Stage2.2 run: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_20260721_085327`
- TSC control step: 10 ms
- Episode horizon: 150 ms
- Allowed arrival endpoints: 120, 130, 140, or 150 ms
- Action space: first three validated SVD modes
- Frozen nominal actions: steps 0-8
- Independent optimized controls: steps 9-14 x three modes = 18 variables
- Optimizer: real-TSC finite-difference trust-region SQP
- Hard success is always decided by real TSC

## Optimization state

- Screen complete: True
- SQP rounds completed: 3
- Optimization finished: True
- Stop reason: `max_sqp_rounds`
- Strict fixed-scenario trajectory found: False
- Controller identification complete: True
- Total real-TSC optimization/identification evaluations: 420
- Successful evaluations: 420
- Precise sustained 30 mm passes: 0
- Relaxed sustained 40 mm passes: 45

## Best real-TSC candidate

- Candidate: `s30r999p_3d650586695d1458`
- Nominal: `nominal_05_s22g000_571ab4a158d29207`
- Source phase: `controller_identification_999_probes` / `real_tsc_fd_probe`
- Gate: `PASS_DAMPED_HOLD_40MM_120_150MS`
- Selected arrival endpoint: 140 ms
- Earliest strict arrival: None ms
- Sustained R/Z box error through 150 ms: 34.783 mm
- Endpoint velocity: 0.089410 m/s
- Endpoint late velocity RMS: 0.095026 m/s
- Post-arrival velocity RMS: 0.073804 m/s
- Maximum normalized violation: 15.9434%

## Deterministic confirmation

- Verdict: `PASS_DAMPED_HOLD_40MM_120_150MS_CONFIRMED_ONLY`

## MPC-compatible artifact

`stage3_0_controller/mpc_poc_bundle.json` contains a real-TSC finite-difference tail Jacobian and a regularized batch correction gain.
It is an offline local sensitivity POC. It has not been tested in closed loop, and it is not a deployable PCS controller.

## Final-task reminder

The final project objective is not one fixed 150 ms open-loop sequence. The objective is a feedback controller that reaches, brakes, and robustly holds R/Z/Ip across initial-state, target, noise, and model variations.
A confirmed Stage3.0 strict trajectory is only the nominal-trajectory gate before perturbation experiments, behavior cloning, MPC/feedback validation, and eventually bounded residual RL.
