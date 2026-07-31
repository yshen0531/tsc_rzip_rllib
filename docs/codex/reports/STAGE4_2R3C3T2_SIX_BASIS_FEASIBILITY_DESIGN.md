# Post-T2 six-basis optimistic feasibility design

Frozen prospectively on 2026-07-31 before server execution.

## Purpose

Build an authenticated six-basis development bank from:

```text
frozen R3c3 four bounded local-response bases
+ certified T2 two held-transport response bases
```

Then run the unchanged corrected optimistic formal-feasibility calculation
for all 32 locked development contexts.

This is a server-side read-only/offline audit. It starts no `gotsc`, changes
no raw result, and is not a real-control or long-hold test.

## Exact code

```text
commit
  e3222a1dd011fff9bf992d95412da8c2149840d3

new audit tool SHA-256
  62c748de11956b468b73dd0ae3937ce2a19b6f241da7281b0fe5e7cd0425f2ab

frozen corrected T1 feasibility tool SHA-256
  7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

The new tool imports the exact frozen corrected T1 `FormalEvaluator`,
six-column R/Z-velocity condition calculation, exhaustive ternary grid, and
per-endpoint multistart SLSQP optimizer. It does not change their metrics,
search bounds, endpoint set, or tolerance.

## Exact immutable inputs

```text
T2 run
  stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902

T2 server audit SHA-256
  e96f9538f5878ac745424d783e8f57c5ff41d61220b7d22ea66bfb1a08107d9c

T2 raw count / digest
  160
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

T2 runtime package fingerprint
  5544b0fe4bc50e03d4dc83183f846c9315db353dcb17c7179371f8fe1b046011

R3c3 audit bank SHA-256
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

R3c3 controller bank SHA-256
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

R3c1 baseline inventory digest
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

## Response construction

For each context and T2 mode:

```text
odd response = (positive raw trajectory - negative raw trajectory) / 2
```

The controller-use response column ends at:

```text
state 35 for slew 1.0
state 37 for slew 0.9
```

The full state-0..50 T2 response remains in the audit bank. States after the
formal endpoint, including the state-39..44 neutralization effects, cannot
improve the formal feasibility column.

The two new basis amplitudes remain exactly:

```text
held_transport_mode0 = 0.0060
held_transport_mode1 = 0.0075
```

No amplitude scan or post-result rescaling is allowed.

## Authentication gates

Before optimization, require:

```text
T2 raw identities / success / 51-state / 50-action       160/160
T2 phase and causal schedules                             160/160
extended-baseline source-prefix equality                    32/32
R3c3 and T2 context-set equality                            32/32
R3c1 formal evaluator pass reproduction                     32/32
R3c1 saved baseline pass count                              16/32
maximum saved-margin reproduction error                  <= 1e-12
T2 reported six-basis condition reproduction                32/32
maximum reproduced condition                   22.89380096837352
```

Any mismatch aborts without producing a bank verdict.

## Formal feasibility gate

For every locked context:

```text
basis count                                                   6
each coefficient                                         [-1,1]
formal arrival/hold timing                              unchanged
R/Z tolerance                                             30 mm
speed threshold                                         0.1 m/s
Ip thresholds and arrival streak                         frozen
six-basis R/Z velocity rank / condition              6/6, <= 25
```

Required aggregate outcome:

```text
optimistic formal feasibility                              32/32
previously failed baseline contexts repaired               16/16
baseline-pass regressions                                      0
condition-number pass                                      32/32
```

The gate is frozen before inspecting its output. It may not be weakened.

## Outputs

The new server output directory must not exist beforehand and must remain
outside all source run trees. It contains:

```text
combined six-basis audit bank
combined six-basis controller bank without hidden-history labels
per-context optimistic feasibility audit
output manifest with sizes and SHA-256 hashes
```

Large banks stay on the server. Only the compact feasibility JSON, manifest,
and log are downloaded.

## Interpretation and advancement

Failure means the optimistic linear response bank still cannot cover the
locked formal envelope. Do not implement or run R3c4.

Pass authorizes only a prospectively frozen R3c4 implementation. It is not
evidence of real restarted MPC, independent histories, unseen targets,
continuous actuator/plant variation, noise, disturbance recovery, or long
hold. R3c4 real TSC execution remains unauthorized until its independent
design, implementation, full validation, and server preflight are complete.

BC, DAgger, and bounded residual RL remain prohibited.

## Post-run disposition

The exact frozen audit completed without starting TSC:

```text
condition pass                                      32/32
maximum condition                               22.893801
optimistic formal pass                              16/32
failed baseline repair                               0/16
baseline-pass regression                             0/16
all preregistered gates pass                           false
```

Therefore this design is frozen as a pre-execution failure and R3c4 remains
unauthorized. See:

```text
docs/codex/reports/STAGE4_2R3C3T2_SIX_BASIS_FEASIBILITY_REPORT.md
```

