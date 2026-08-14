# R_geo/Z_geo 1 ms NR2R2C2a nominal-hold search design

Status: prospectively frozen before implementation or new TSC.

Date: 2026-08-14 Asia/Shanghai

## 1. Question and claim boundary

C1a qualified only canonical-source full-prefix replay mechanics and rejected
1 ms online-Oracle use on cost. C2a now asks one smaller physical-authority
question: can either of two already observed constant Card15 dwell cells
produce a finite 32 ms source continuation that materially arrests the q0
drift?

This identity is development search, not fresh qualification. Its trajectories
are forbidden from fixtures, model fitting, training and expert data. Even a
successful search result can authorize only a separately committed fresh-
reset validation of one frozen candidate. It cannot establish Nominal-H1,
backup, Recourse-L1, model, controller, MPC, atlas, adaptation or RL.

## 2. Why these two candidates

Only the 28 already-consumed NR2R1 development/calibration compact records
were used; the invalid diagnostic holdout was not opened. Their tracked input
inventory is
`98f6bd1992b9681ec548e4bbc8f1f6b6c7332309522a81e961c8be57edbd3c49`.
Across all 448 transitions the observed one-step maxima were:

```text
|Delta R_geo|     0.833656 mm
|Delta Z_geo|     0.855951 mm
|Delta Ip|       45.9948 A
```

The strongest supported four-step constant-dwell responses opposing the
source q0 `(-R,+Z)` drift were `development_p04_plus` and
`development_p07_plus`. At state 5 their direct q0-relative deviations were
approximately `(+0.699,-0.369) mm` and `(+0.699,-0.383) mm`. Each uses a
fixed target at no more than `0.15 A` from q0 and has the exact already
observed causal prefix:

```text
step 0       q0
steps 1..4   same frozen target
```

C2a extends only the zero-increment hold at that same target through step 31.
It does not add a new sign, target amplitude, or per-step current increment.
The longer history is new and remains the scientific object under test.

## 3. Frozen matrix and budget

```text
candidate                                    resets    advances
development_p04_plus_constant_dwell              1          32
development_p07_plus_constant_dwell              1          32
maximum total                                    2          64
```

Every rollout starts from the canonical 1100 ms source. Search ordering is
the configuration order. There is no adaptive action within a rollout, no
optimizer, and no snapshot restart. A failed candidate stops before any later
issue but does not erase the other candidate's already independent identity.

## 4. Interface and empirical successor gate

Before every issue and after every successor require the NR0/NR1 contract:
same-time paired boundary, limiter, Ip, exact Card15, command/readback slew
`<=0.3 A`, absolute currents, direct `k -> k+1` effect, non-abnormal TSC, and
no silent R/Z or action fallback.

This is a TSC-only bootstrap sentinel, not deployable safety evidence. Its
independent empirical successor support is the complete NR2R1 dev/cal maximum
above, inflated prospectively to:

```text
|Delta R_geo| <= 0.002 m
|Delta Z_geo| <= 0.002 m
|Delta Ip|    <= 100 A
```

Before an issue, the current state must be within the 25 mm R/Z and 5% Ip
inner envelope and must retain at least that full successor allowance inside
the 50 mm R/Z and 10% Ip outer envelope. If the observed successor exceeds
the empirical bound or any hard gate, record FAIL and issue nothing further.
The bound is fixed before this result; passing it does not turn it into a
deployment theorem or recovery set.

## 5. Search eligibility and deterministic selection

For a candidate to be eligible for later fresh validation it must complete all
32 advances and keep every state in the inner envelope. In terminal states
24..32 it must also satisfy:

```text
maximum |R_geo-R0| and |Z_geo-Z0|           <=0.005 m
each terminal |Delta R_geo|,|Delta Z_geo|   <=0.0001 m
terminal-window net |Delta R_geo|,|Delta Z| <=0.001 m
```

These retain B0's frozen short-hold velocity/net-drift gates and add a source-
proximity gate. They do not reinstate the retired 250/270 ms contract.

If both are eligible, select lexicographically by: smallest terminal maximum
source-axis displacement, then terminal maximum axis step, then terminal net
axis drift, then candidate id. The search output freezes the winner's exact
Card15 sequence and hashes. Search data never serve as its qualification
repeat.

## 6. Routes

```text
offline/source/package failure
  ONE_MS_NR2R2C2A_SEARCH_OFFLINE_FAIL_NO_TSC

runtime/interface/current/boundary failure
  ONE_MS_NR2R2C2A_SEARCH_EXECUTION_FAIL_STOP

empirical successor bound exceeded
  ONE_MS_NR2R2C2A_SEARCH_SUPPORT_BOUND_FAIL_STOP

both candidates complete but neither is eligible
  ONE_MS_NR2R2C2A_SEARCH_NO_NOMINAL_HOLD_CANDIDATE_REDESIGN

at least one candidate is eligible
  ONE_MS_NR2R2C2A_SEARCH_CANDIDATE_FOUND_VALIDATION_DESIGN_ONLY
```

The last route permits only a separate prospective validation design. No
route here authorizes C2b, response-tail work, atlas, model fitting or control.
