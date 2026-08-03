# Stage4.2R3c3T13S24D1R2 real-TSC safety sentinel design

## Status and purpose

This design is frozen after the completed S24D1R1 result and before D1R2
implementation, package construction, normalized-spec creation, Ray startup,
or any new TSC trajectory. D1R2 is a 54-rollout development-set safety
sentinel for the geometry-restored sequential schedule selected by D1R1.

It answers one narrow prospective question: do all 54 S24 contexts that
previously hit the 0.50-amplitude online cancellation guard now execute all
four causal issue/cancel pairs with every original action gate and the added
online cancellation margin `<= 0.24`?

It does not fit a transition model, optimize an MPC, establish formal tracking
success, or validate a full identification grid.

## Immutable source evidence

D1R2 must authenticate the following D1R1 package and server outputs before
creating a run directory:

```text
D1R1 config sha256
  860dffbf5a25f7275a0976bdb0e037b859519c35c8365480c364fbbdfd7bde99
D1R1 implementation sha256
  0557961967b3129f0e4ec122b03c6132f8936d6d554b1c93dab5cae1c1cde2e1
D1R1 preregistered design sha256
  e6a9fd89397aabd1ac2017448b1d9cea278b67e3af198508b037ecdcb2c44407
D1R1 final forensic report sha256
  b24cb0773e107d826bf5d69a047c7af412852634403741942eae4c343202f9d7
D1R1 detailed sha256
  81168e646f2b40e443fa85f535193474651eb899ac8a74e1c9cd282b4f66ff98
D1R1 summary sha256
  0ec97157184ba85c70507adcc9978f9c2f87afbaa462af58152bccc008e145a0
D1R1 selected-spec table sha256
  61574900383ae91083173065561ea8f2a80a96a4c6935f3a965ef7ce43215c46
D1R1 manifest sha256
  d6f42befe92b170226ea19f73bebbe8623191debde756b61500d6daa22ea7b9f
D1R1 complete log sha256
  89eb453af423ed9a7b4cb48122e0228b99ec1a8b3335865f7d6cf4f1bb59eb2e
```

The source output directory is exactly:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r1_audits/
stage4_2r3c3t13s24d1r1_geometry_restoring_search_20260803_145327
```

The source route must be
`GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED`, with
selected amplitudes `++--=0.290` and `+--+=0.360`, all 3,840 issue and 3,840
cancellation gates passed, and exactly 54 selected rows. D1R2 must also
authenticate the unchanged S24 active raw inventory digest
`fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70`
through the D1R1 provenance chain, the exact S24 controller source hash
`29283348f004f90eeea5e563ae2e5397397e324bfb6b51ecff3436398938c6e9`,
and all selected restart snapshots/manifests in place.

Any mismatch stops before TSC with
`GEOMETRY_RESTORED_SENTINEL_PREFLIGHT_FAIL_NO_TSC`.

## Frozen identity-only normalization

The D1R1 table correctly freezes the authoritative next stage, campaign,
controller, selected source context, snapshot, amplitude, action schedule,
and gates. Its reused helper nevertheless wrote an older `s24d2/contracted`
token into several future opaque labels. No TSC has run with those labels.

D1R2 must retain the source rows in their exact selection-index order and may
change only these five paths inside each `sentinel_spec`:

```text
experiment_id
environment_variant
kind
phase
s24d2_online_cancel_margin_gate -> s24d1r2_online_cancel_margin_gate
```

The deterministic transform is:

```text
experiment_id:
  s42r3c3t13s24d2_<suffix> -> s42r3c3t13s24d1r2_<same suffix>
environment_variant:
  stage4_2r3c3t13s24d2_<old experiment id>
    -> stage4_2r3c3t13s24d1r2_<new experiment id>
kind:
  stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel
phase:
  prospective_geometry_restored_amplitude_safety_sentinel
margin key/value:
  s24d1r2_online_cancel_margin_gate = 0.24
```

No suffix is regenerated or selected. The normalized ordered 54-spec digest,
using canonical sorted-key compact JSON, is frozen as:

```text
50832fadb244bbd338bd7c5cd5f9ff136eedce498d920f416458516d7655648f
```

The implementation must deep-compare every source/normalized spec after
reversing exactly those five changes. Any other changed field stops before
TSC. In particular, the snapshot, target, delay, slew, horizon, history,
sequence index, requested matrix row, per-step requested coordinates,
schedule digest, controller revision, formal timing, and all blindness flags
must be identical.

After normalization the table must contain 54 unique experiment and
environment IDs, 18 exact contexts/snapshots across 9 pairs, horizon counts
`35:20` and `37:34`, and sequence-index counts:

```text
6:12, 10:14, 14:6, 18:16, 22:6
```

The experiment/environment labels are bookkeeping only and are not available
to the causal controller.

## Frozen controller and action semantics

Each rollout uses one fresh Ray actor, one fresh `gotsc`/TSC process, and one
fresh causal controller. The controller source is a new D1R2 subclass of the
exact S24 sequential controller. It may change only:

1. stage/controller/result trace identity;
2. the selected requested matrix rows already frozen by D1R1;
3. the additional fail-closed cancellation-margin criterion.

The S21 causal prefix, exact Card15 active calibration, current-step online
issue construction, stored-center cancellation, phase-aligned R17 underlying
controller, plant snapshot, task clock, and formal horizon are unchanged.
The four issue steps remain `10,13,15,17`; cancellations remain
`11,14,16,18`; their effect states remain `11,14,16,18` and `12,15,17,19`.

The amplitude map is exactly:

```text
++++  0.250
+-+-  0.250
++--  0.290
+--+  0.360
```

The saved 24-by-16 matrix is authoritative and its digest remains:

```text
023a6c9212bf52f38b1d4268d2be406964b5c1d1c64e43ffad85f0af689a3ce6
```

Every issue retains all original S24 gates:

```text
finite values                                               true
exact 10-character center/target and exact reproduction     true
active signs and minimum active coordinate               >= 0.18
maximum absolute coordinate error                        <= 0.07
desired/applied current cosine                            >= 0.98
relative off-basis residual                               <= 0.10
incremental normalized action                             <= 0.25
total normalized action                                   <= 1.0
predicted current utilization                             <= 0.55
no action saturation or current clipping                    true
```

Every cancellation retains exact stored-center return, exact zero target-jump
net, the same 0.25/1.0/0.55 action/current gates, no saturation or clipping,
and additionally requires:

```text
online cancellation incremental normalized action <= 0.24
```

The 0.24 margin is an extra development gate. It does not replace or weaken
the 0.25 safety cap. A cancellation that exceeds either threshold must be
recorded as a structured action-schedule failure and must not be applied to
the plant.

## Causality and controller blindness

The controller may use only the current rollout's visible causal state,
current measured coil currents, trusted causal calibration state, task clock,
and the current step's preregistered requested coordinate. It may never use:

```text
S24 outcome, failure reason, future state, future action, or measured response
source/current wire current
source coil action or current
pair, hidden-history, partition, target-ID, or failure-class categorical label
future requested schedule inside the underlying controller
current-run future values
```

Selection metadata remains outside the controller spec. Full wire current may
be recorded only after action choice for forensic evidence. The controller
trace must explicitly record all forbidden-use flags as false. The existing
preregistered numerical target offsets and controller delay/gain/slew
estimates remain available exactly as in S24; they are causal controller
configuration, not source-outcome or selection labels.

## Runtime matrix and phase boundary

The exact campaign is one phase containing 54 fresh real-TSC rollouts:

```text
expected raw files                                      54
fresh actors / TSC processes / controllers              54 / 54 / 54
full horizon                                             20 x 35, 34 x 37
sequential issue/cancel events per successful rollout    4 / 4
total issue/cancel events on a full pass                216 / 216
Ray capacity                                             fixed at 54
```

The initial launch is fresh (`resume=0`). Resume is allowed only after an
infrastructure interruption when the package/config/spec/controller digests
are identical. A matching complete raw file, including a structured semantic
failure, is immutable and may not be rerun. Only missing or byte-invalid raw
may be scheduled. A controller, physical-action, task, gate, or identity
change requires a new run/stage.

## Required raw, restart, and execution gates

A pass requires all 54 raw files to strictly parse and match the exact
normalized specs and identities. For every rollout:

```text
result success/completed                                  true / true
trajectory / trace length                         horizon+1 / horizon
fresh TSC / fresh controller                               true / true
initial authentic plant restart exact                            true
controller trace causal and actions computed online             true
solver success, finite values, no abnormal plant state           true
recorded trajectory action equals returned controller action     true
exact eight-event active calibration and exact net zero          true
exact eight-event sequential issue/cancel schedule               true
all four issue gates / all four original cancellation gates      true
all four cancellation increments <= 0.24                         true
current utilization <= 0.55                                      true
forbidden controller-use count                                      0
active issue state cleared at horizon                             true
```

Formal tracking under the immutable 250/270 ms arrival and 350/370 ms hold
contract is recomputed from raw but remains diagnostic only. The 35/37-state
horizon is unchanged and is not an independent long-hold test.

## Independent server-side forensic requirement

Before TSC opens, an independent audit module must be packaged and hashed.
After the campaign it must read all raw JSON.GZ directly on the server and
independently recompute:

- strict parse, count, bytes, per-file SHA-256, and canonical inventory digest;
- exact spec and identity coverage with no duplicate/missing/extra raw;
- trajectory/trace lengths and numeric finiteness;
- authentic restart, causal phase trace, calibration, recorded-action, solver,
  abnormal-state, saturation, current, and forbidden-input gates;
- exact sequential event order and every saved issue/cancel criterion;
- all 216 cancellation increments and their maximum from raw event details;
- formal tracking diagnostics from raw trajectories;
- snapshot manifest existence/hash inventory and package/config/controller
  fingerprints;
- state, manifest, final-result, and complete-log consistency.

Only compact audits and logs may be downloaded. Raw trajectories and snapshots
remain on the server and are forbidden from expert datasets.

## Frozen routes

```text
source/package/spec/snapshot failure before TSC
  GEOMETRY_RESTORED_SENTINEL_PREFLIGHT_FAIL_NO_TSC

TSC/solver/restart/causality/raw/corruption/runtime failure
  GEOMETRY_RESTORED_SENTINEL_RUNTIME_FAIL_STOP

structured original action/current/Card15/zero-net or 0.24 margin failure
  GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED

all 54 pass internal and independent raw gates
  GEOMETRY_RESTORED_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_REQUIRED
```

Route classification must come from raw evidence, not only the saved verdict.
An unrun trajectory is neither a pass nor a real plant failure.

## Scientific scope and next authorization

A complete D1R2 pass proves only finite development-set causal execution and
online cancellation headroom for the 54 formerly unsafe S24 contexts under
the selected clean discrete regimes. It does not validate the other 946
replacement-campaign trajectories, the transition model, real MPC, unseen
targets, continuous delay/gain/slew, plant/Jacobian mismatch, sensing noise,
disturbance recovery, or long hold.

A pass authorizes only a separately preregistered, new-identity full
replacement sequential transition-identification campaign using the fixed
0.250/0.250/0.290/0.360 map. That campaign must rerun every baseline and
sequence; no S24 or D1R2 raw may be reused for fitting, calibration, holdout,
expert data, BC, DAgger, or RL.
