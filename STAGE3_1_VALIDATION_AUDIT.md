# Stage3.1 validation audit

## Inputs used

- Stage3.0 standalone code archive:
  `stage3_0_complete_standalone.zip`
- Stage3.0 standalone SHA256:
  `746afc36f34d1b9fa76d8a48ba73124bb9fe695de8a7628c2cbe1eda8cf70e0a`
- Completed Stage3.0 result archive:
  `stage3_0_runs.zip`
- Stage3.0 result SHA256:
  `b3d7148132022e73b9e91fc23c4d9b20dfe04f2080ec5cb8a446322a788f9b37`
- Completed Stage2.2 result archive:
  `stage2_2_runs.zip`
- Stage2.2 result SHA256:
  `a5206e6ca940dab66b3d37d86d3e75802be83fe41fbf130654c640299956ade0`

## Real-history reconstruction checks

Using the uploaded completed runs:

- loaded 420 successful Stage3.0 optimization/identification rows;
- recovered 420 unique 21-variable vectors;
- resolved all referenced compressed real-TSC results;
- selected the Stage3.0 minimax best source candidate
  `s30r999p_3d650586695d1458`;
- reproduced that source candidate's full 15x3 mode sequence and 15x14 physical
  action sequence exactly through the Stage3.1 decoder;
- selected a different-nominal position-front secondary center for round zero;
- constructed 84 unique real finite-difference specs;
- constructed 30 unique SQP proposal specs;
- confirmed every generated spec is strict-JSON serializable;
- generated a 435-file content inventory for the supplied source tree in the
  integration environment.

## Algorithm tests

Stage3.1-specific tests cover:

- fixed 150 ms/three-mode/21-variable configuration;
- hard-gate drift rejection;
- trust-configuration and feedback-design drift rejection;
- exact freezing of steps 0-7;
- mode-action/current repair equivalence with the open-loop decoder;
- 35-feature layout;
- 84 unique probes and inward secants at coefficient bounds;
- partial Jacobians with JSON null metadata;
- freezing unavailable variables in SQP;
- 15 proposals and 0.5/1.0/1.5 real-step multipliers;
- trust expansion and rejection shrinkage;
- trust-ratio comparison at one common requested endpoint;
- forced different nominal family;
- dimensionless batch/causal gain shapes;
- 24 feedback specs;
- selection of one globally fixed feedback scale rather than per-scenario
  post-hoc gain selection;
- strict JSON NaN rejection;
- sustained-window constraint evaluation;
- category-aware confirmation.

The inherited Stage2, Stage2.1, Stage2.2, and Stage3.0 regression suites are
also run.

## No-gotsc integration

A synthetic evaluator was used to execute a complete Stage3.1 round against the
real uploaded Stage3.0 source catalog:

- 84 probe records;
- two 35x21 Jacobians;
- 30 SQP proposal records;
- adaptive trust diagnostics;
- state persistence and readback.

This validates control flow and persistence only. It is not scientific evidence
about the real plant.

## Dimensionless-controller audit

The Stage3.0 30x18 Jacobian was embedded into the Stage3.1 normalized gain path
as a compatibility check. The normalized batch model retained a regularized
low-condition subspace, and the normalized Ip magnitude no longer dominated
R/Z solely because it was expressed in amperes. The real Stage3.1 run will
identify the new step-8 columns directly.

## Final standalone packaging checks

The candidate archive was extracted into a fresh empty directory and verified
for:

- package SHA256;
- complete source tree;
- Python compilation;
- JSON parsing;
- all shell `bash -n` checks;
- complete unit-test suite;
- no Git/network/external-tree dependency;
- real-source prepare-only loading without `.git`.

The fresh extraction passed the complete 64-test suite and loaded the uploaded
420-row Stage3.0 source catalog. It reproduced the 435-file source fingerprint
`7de4a06af4bcc4573c19298cc60af92f407ef19ae2c132d7d4f48b63965e4021`.

## Explicit non-claims

No full Stage3.1 campaign was executed here with the user's gotsc binary. This
audit does not claim:

- strict 30 mm success;
- real trust-region expansion behavior;
- feedback POC success;
- online MPC validation;
- robustness;
- long-duration hold;
- readiness for imitation learning or residual RL.
