# Stage4.2R3c3T13S12 causal natural-history observer preflight report

## Identity and outcome

```text
branch                              codex/stage4_2r3c3t13s1-transition-sentinel
initial implementation              3eda0cb
target-schema hotfix                d2940b3
design SHA-256
  0e49d9a992d27ae89bf2c6a2f0f153e38a8737459af38473576303d1ca60b541
final audit SHA-256
  1ccaaea1f8da5b5271331758a0a390c5dc663f98c5099299ff3a440007b94b4a
final log SHA-256
  42b2b4e295e731a04c6142e69f87d9efe095e5244b7439ca8288e85bc1c36b0e
route
  CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN
```

T13S12 is a zero-new-TSC read-only development audit. It did not run Ray,
`gotsc`, a controller, an optimizer, a plant step, or a new snapshot. It
therefore has no new closed-loop or plant-restart result.

## Exact evidence

Remote source and final output:

```text
q1 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s9_runs/
  stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a

q2 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_runs/
  stage4_2r3c3t13s5_real_20260802_d048686

final audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s12_audits/
  stage4_2r3c3t13s12_causal_natural_history_observer_20260802_d2940b3m1
```

Source inventory and authentication:

```text
q1 raw JSON.GZ                              68 / 68
q1 raw bytes                              3,610,295
q1 raw digest
  9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
q1 independent source audit
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0

q2 raw JSON.GZ                              68 / 68
q2 raw bytes                              3,610,097
q2 raw digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
q2 independent source audit
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033

T13S10 source audit
  f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b
T13S11 source audit
  6e595fbd4e86276d449fc953edcb06b676bd282b6f0bd68d4e5ac3effe97ffbe
trace identity                               136 / 136
strict final JSON                                      PASS
```

The 136 large raw files and their snapshots remain on the server. Only the
56,903-byte compact result and small logs were copied directly to
`docs/codex/audits/stage4_2r3c3t13s12_result_20260802_d2940b3/`.

## Runtime and implementation incidents

The first invocation at `3eda0cb` stopped before a result because the audit
mistakenly expected `payload.cfg.target` to contain the raw specification's
target offsets. Inspection of all eight baseline payloads and the actual
R3b/R3c1 controller source proved the real contract:

```text
runtime target = payload.cfg.target + raw spec target offsets
payload.cfg.target == payload.train_cfg.target == frozen base target
```

Commit `d2940b3` repaired only that schema interpretation and added a
regression test. It changed no history field, fold, basis, whitening, fit,
support, tube, error threshold, route, source raw, or physical semantics.
The stopped directory contains one log and no JSON result.

The next `d2940b3` invocation used a direct script path and stopped before
module import with `No module named 'docs'`. Its directory also contains one
log and no result. The unchanged module invocation then completed under the
new `d2940b3m1` output identity. This is a launcher/environment error, not a
scientific failure.

There is no remaining statistics or reporting error in the final result.
Direct recomputation from all 64 validation rows exactly reproduced every
reported pass count and the maximum error.

## Frozen scientific gates

```text
causal history schema                            8 / 8
signed braking extraction and causality         64 / 64
history affine rank                              8 / 8
history/current whitening                        8 / 8
current basis rank                               8 / 8
interaction rank/condition/signal                 8 / 8
maximum interaction condition        1.000000000000045
non-vacuous tube                                 8 / 8
history support                                  8 / 8
braking-current support                         64 / 64
prediction supported                            64 / 64
componentwise containment                       61 / 64
scaled relative error <= 0.10                   44 / 64
both response gates                             41 / 64
maximum scaled relative error             1.701539079
exact disjoint causal aliases                         0
forbidden feature/trace/model inputs                  0
```

Response failures are not confined to one campaign, stratum, sign, or
direction:

```text
q1 / q2 both-pass                         21/32 / 20/32
easy / hard both-pass                     20/32 / 21/32
negative / positive both-pass             20/32 / 21/32

mode0 coil-8 / mode0 remainder              8/16 / 12/16
mode1 / mode2                              10/16 / 11/16
```

The worst row is an easy q2 mode-1 negative response. Its causal-history
support, current support, containment, condition, and pre-effect causality
all pass, but its scaled center error is `1.701539079`. The analogous q1 row
is also unsupported by accuracy rather than by input coverage, at
`1.540737161`. Whitening repaired T13S11's numerical conditioning problem;
it did not repair cross-history response prediction.

## Classification and limits

- Runtime/environment: two preserved no-result invocations, both before any
  scientific output; final invocation completed.
- Packaging/deployment: final staging and installed packages passed 347/347
  hashes, all declared `bash -n` checks, focused 7/7, and complete 743/743
  tests with one expected skip.
- Raw/snapshot corruption: none; the two frozen source inventories and
  independent source audits authenticate all 136 raw trajectories.
- Statistics/reporting: none in the final result; row-level recomputation is
  exact.
- Design: the affine history/current interaction observer is insufficient in
  this finite consumed q1/q2 envelope.
- Real control/plant restart: not run and therefore neither passed nor failed.

The immutable 250/270 ms arrival and 350/370 ms hold timing is unchanged.
T13S12 does not authorize q3 under the affine route, a controller, MPC,
expert data, BC, DAgger, or bounded residual RL.

## Validation actually run

Local validation used repository files only: compile, 3,458 JSON parses,
focused 7/7 tests, complete 743/743 tests with the established Windows
`resource` shim, 347/347 package hashes, and an empty direct-copy package
simulation with 743/743 tests and one expected data skip. Direct Windows
discovery without the shim produced 27 POSIX-`resource` import errors and ran
no affected test bodies; this is separately classified as environment.

Server validation used the existing virtualenv and no network: staging and
installed 347/347 hashes, 60 package JSON files, all declared shell syntax,
focused 7/7, and complete 743/743 tests with one expected skip. Staging and
installed log SHA-256 values are respectively:

```text
8b2861ef3dc5001d3caf76080d600fb4a535229477a752dd82c91670309d6345
8ab40ac45be864c14a9f8a27a693b3f0f066619d0b79d7ec6efee81a2f3b44ab
```

## Next action

Do not fit a higher-capacity recurrent model to only eight already-consumed
contexts and call it validated. The next stage must prospectively freeze a
broader same-trajectory history/response campaign with independent history
groups, causal sequence inputs, a training-only recurrent or nonlinear
set-valued predictor, fail-closed support/tube behavior, and a genuinely
fresh history holdout. Probe trajectories remain forbidden from expert data.
