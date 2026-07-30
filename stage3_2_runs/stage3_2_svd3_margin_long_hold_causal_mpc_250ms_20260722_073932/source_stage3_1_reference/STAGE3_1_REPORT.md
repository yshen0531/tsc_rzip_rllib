# Stage3.1 adaptive SQP and causal-feedback POC

- Source Stage3.0: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_20260721_121352`
- Horizon: 150 ms at 10 ms control intervals
- Control space: first 3 validated SVD modes
- Frozen controls: steps 0-7
- Optimized controls: steps 8-14 (21 variables)
- Hard gate changed from Stage3.0: **no**

## Fixed-scenario optimization

- Real-TSC evaluations in Stage3.1 catalog: 498
- Successful: 498
- Strict 30 mm candidates: 46
- Relaxed 40 mm candidates: 440

## Best fixed-scenario candidate

- Candidate: `s31r999p_69651620f6334222`
- Nominal family: `nominal_05_s22g000_571ab4a158d29207`
- Gate: `PASS_PRECISE_HOLD_30MM_120_150MS`
- Best endpoint: 140 ms
- Sustained box error: 29.937 mm
- Post-arrival velocity RMS: 0.047240 m/s
- Maximum normalized violation: 0.000000

## Deterministic confirmation

- Verdict: `PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED`

## Limited causal-feedback POC

- Rollouts: 24
- Limited POC pass: False
- Online feedback validated: **false**
- Robustness validated: **false**

## Final-task boundary

Stage3.1 is not the final controller. The project target remains a causal, robust feedback controller that reaches, decelerates, and holds R/Z/Ip across initial states and targets.

A fixed-state open-loop strict trajectory is only an expert/nominal entry point. The limited target-shift/disturbance POC does not validate robustness, long-duration hold, or deployable online MPC.
