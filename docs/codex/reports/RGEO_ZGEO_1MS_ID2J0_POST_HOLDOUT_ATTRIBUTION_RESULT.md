# R_geo/Z_geo 1 ms ID-2J0 post-holdout attribution result

Date: 2026-08-17 Asia/Shanghai

## Verdict

ID-2J0 completed its diagnostic re-observation and independent raw audit,
then recomputed the frozen ID-2G1R1 TCN under truth-recenter periods of 1, 2
and 4 ms and under the original free recursion. The final route is
`ONE_MS_ID2J0_MIXED_DATA_AND_STRUCTURED_MODEL_REQUIRED`.

This is a post-holdout attribution result, not another blind holdout. It fits,
updates, selects or recalibrates zero models. Its trajectories are forbidden
for fitting, calibration, width reduction, model qualification, controller
qualification, expert data and RL data.

## Execution and evidence integrity

- implementation revision: `2e1eaa784c98bda084206bf4b19a167a366ead01`;
- reporting-only evidence-reader repair: `53d0f9db24a73bf85716aafb7f040dfacea07793`;
- 16/16 diagnostic rollouts, 544/544 verified one-ms advances and 560 states;
- all eight matched baseline/probe prefixes passed;
- 2,800 required raw files, 32,980,037,440 bytes, inventory digest
  `fd884699425916b774650c882659bff3826f41b7d8d689a093984f7fea3bd52d`;
- primary result SHA-256
  `8f473103b4b609db8845735f3ee28701ce1e74c93f65f492dd31fec4c76d31f2`;
- independent raw-audit SHA-256
  `7b4885bbc005cf2270d263d969a2332fe889b4e6b6567965ea734d9f3f63cf8f`;
- attribution and independent recomputation SHA-256
  `fbc1a58a34e15c0c0b9f87afcc3852ccf8c09f712f1281a393e02edb49d1f02d`;
- independent attribution-audit SHA-256
  `f3cec48ab5102cc403b665db6bcf5f4ae3f166835c7ca22e3e83c7a534f73c65`;
- independent metric difference: exactly zero.

The first attribution attempt stopped after TSC was complete because the
reporting helper called a nonexistent evidence-reader name. Raw and compact
results were preserved. Revision `53d0f9db` changed only that reader call,
server regression tests passed, and attribution was recomputed with zero new
TSC calls. This is a reporting defect and repair, not a rerun or scientific
identity change.

## Attribution result

Exact next-current propagation remains consistent with the frozen actuator
contract: the maximum next-current residual is
`1.00000000031741e-05 A`, below the frozen `2e-05 A` diagnostic threshold.
No queue/effect-state implementation fault explains ID-2I1.

| Prediction mode | Paired-response NRMSE | Positive peak direction | p95 absolute R/Z/Ip error |
|---|---:|---:|---|
| exact 1 ms truth recenter | 1.133318 | 5/8 | 0.359755 mm / 0.146197 mm / 5.89315 A |
| 2 ms truth recenter | 1.150032 | 5/8 | 0.362487 mm / 0.148992 mm / 8.37375 A |
| 4 ms truth recenter | 1.184157 | 5/8 | 0.326787 mm / 0.129229 mm / 9.95810 A |
| original free recursion | 1.109016 | 5/8 | 0.534567 mm / 0.226199 mm / 19.7570 A |

Truth recentering sharply reduces absolute-state drift, especially Ip, but it
does not repair the paired signed response. At 1 ms recentering the three
minus groups `h00`, `h02` and `h06` retain peak R/Z cosines
`-0.773315 / -0.878424 / -0.786459`, while all five other groups remain
positive. Six of eight probe prefixes are also outside the development
full-feature support reference.

Therefore ID-2I1 was not merely a long free-recursion failure. The frozen
monolithic TCN is also structurally wrong or unsupported for several local
history/sign/action combinations after exact current-state recentering.
Conversely, the result does not prove that recurrent learning is useless or
that a particular hidden physical mechanism has been identified.

## Route

Do not enlarge the same TCN, tune against ID-2I1/ID-2J0, or widen the old
global tube. The next development data identity must deliberately factor
conditioner history, action direction, sign and action duration/age with a
matched baseline in every complete causal context. Whole causal families,
not individual steps, remain the split unit.

After that data gate, compare an explicit architecture in this order:

1. exact Card15/current/queue propagation;
2. explicit time-indexed active nominal continuation;
3. stable low-order latent action-memory dynamics;
4. context-gated nonlinear residual, with a small TCN/GRU admitted only when
   it improves fresh whole-family evidence.

Evaluation must include exact 1 ms truth-recentered one-step prediction,
2/4 ms rolling prediction, direct or stable multi-step prediction, matched
baseline response direction and family-conditional uncertainty/OOD. A fresh
calibration and a new untouched whole-history holdout are still required
before controller-grade tubes. Authority, recourse, NMPC, transport,
crossing, adaptation and RL remain separate later gates.
