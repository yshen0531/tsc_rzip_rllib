# Stage4.2R3c3T13S24D1R14R8R51R1 q0 first-effect reporting hotfix contract

Status: frozen on 2026-08-10 after the immutable R8R51R1 primary and original
independent audits both reported `39/208`, and after read-only raw forensics
localized that count to binary64 reconstruction roundoff, but before any
corrected hotfix output was produced.

## 1. Preserved evidence

This is a zero-new-TSC reporting repair. It must not rerun a controller, Ray,
`gotsc`, TSC, a plant step, or any R8/R8R1/R8R51/R8R51R1 trajectory. It must
not overwrite the original primary, original independent, state, manifest, or
raw files.

The repair is bound fail-closed to:

```text
run manifest
  c58148f603913c70d5e35626f72dc3541892ad4ec2a919db139a45b51feaa076
original raw primary
  925dbed532e4dcda721592fe409158c7defd89636d94affef9157646df5981a1
original raw independent
  bd7f4a35fbb011abfe282e386080967449f6695486954f2614f4957a12908a4b
original stage state
  3ba2068fdeae0e4a508e648381a080d49c35c933c9f37c76f1b1fb8e4ac34b54
raw inventory
  count 208 / bytes 6,692,740
  0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33
executed config
  a40569191b5d4fc3f8b2663e52f188ed0cf3f211280574d1889750ae6d516c4f
executed controller/audit module
  cfb026f5547ea98d3af0edb9b459e50c1b2826f51ab88b048e8f57af3ce2ccb0
original independent module
  a60bd077e4c4774e44385a1fcc335d11c8b6c4d50f8f662e5c0465661953b1d2
executed package fingerprint
  d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae
executed package manifest
  cd210e76f2b0acdebb1128740fc345995ffd0a88f04dc46f6488c89370898d7e
```

The original reports and state remain historical evidence of the reporting
bug. The corrected conclusion is carried only by new hotfix artifacts.

## 2. Exact correction

The frozen design requires the task-step-10 exact Card15 q0 action to have
physical effect at state 11. The executed audit checked three facts:

1. state-11 applied action equals the task-step-10 trace action;
2. state-11 TSC current equals the q0 event's reconstructed nominal readback;
3. state-10 applied action equals the task-step-9 trace action.

Checks 1 and 3 were exact `208/208`. Check 2 used `numpy.array_equal`, even
though the nominal current was reconstructed through binary64 arithmetic.
Raw forensics found a maximum difference of only
`2.842170943040401e-14 A`; state-11 current itself was exactly the state-10
physical current in all rows. The old binary-exact count was therefore
`39/208` solely because only three contexts happened to reconstruct the same
binary64 values.

The only authorized correction is:

```text
action comparisons                         exact equality
current comparison                         rtol = 0
current absolute tolerance                 1e-12 A
finite-value requirement                   unchanged and mandatory
all other raw/scientific/safety gates       unchanged
```

The `1e-12` allowance was already frozen in the executed package's formal
timing/numerical contract before real execution. This repair neither selects
a threshold from the observed error nor widens any controller, action,
current-utilization, formal, or scientific gate.

## 3. Independent and final artifacts

The primary hotfix must parse all 208 gzip JSON files and use NumPy numerical
equivalence. A separate independent implementation must parse the same raw
files and use scalar `math.isclose` comparisons without calling the primary
calculation. They must agree on inventory, row identity, counts, maximum
error, route, and outcome.

Only these new files may be created in the existing stage analysis directory:

```text
q0_first_effect_reporting_hotfix_primary.json
q0_first_effect_reporting_hotfix_independent.json
q0_first_effect_reporting_hotfix_compact_audit.json
q0_first_effect_reporting_hotfix_final_report.json
```

If and only if every unchanged gate remains `208/208`, both implementations
pass, raw remains byte-identical, and the two calculations agree, the corrected
route is:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED
```

Otherwise the original failure route remains controlling and R51R2 stays
blocked.

## 4. Scientific boundary

A corrected PASS is only finite q0-to-first-transport identification
integrity. It is not a controller, MPC, formal-control, long-hold, robustness,
plant-reachability, or Gate A result. All 208 trajectories remain probes and
are forbidden from expert data. A PASS may authorize only the separately
frozen R51R2 zero-new-TSC model preflight; expert data, BC, DAgger, residual
RL, Gate A, and Gate B remain blocked.
