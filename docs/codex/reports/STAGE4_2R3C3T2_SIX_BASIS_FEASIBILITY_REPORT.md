# Post-T2 six-basis optimistic feasibility report

Date: 2026-07-31 (Asia/Shanghai)

## Result

The prospectively frozen post-T2 six-basis gate failed:

```text
contexts evaluated                                  32/32
six-basis rank/condition                            32/32
maximum condition                               22.893801
R3c1 baseline formal passes                         16/32
optimistic six-basis formal passes                  16/32
failed baseline contexts repaired                    0/16
baseline-pass regressions                            0/16
R3c4 implementation authorized                         no
real TSC executed                                      no
```

This is a pre-execution design failure. It is not a runtime, raw-data,
plant-restart, or real closed-loop-control failure.

## Exact code and server paths

```text
branch
  codex/stage4_2r3c3t2-held-transport

audit implementation commit
  e3222a1dd011fff9bf992d95412da8c2149840d3

audit implementation SHA-256
  62c748de11956b468b73dd0ae3937ce2a19b6f241da7281b0fe5e7cd0425f2ab

result-forensics commit
  562c111df83c04702edf98c757d25e79b46cc89a

result-forensics SHA-256
  3085e52e2cc462a584577e159eb31008b01012a3c4705a32fa559f9bbe464b37
```

Server result directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t2_six_basis_feasibility/
stage4_2r3c3t2_six_basis_feasibility_20260731_e3222a1
```

Server forensic-audit directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t2_six_basis_feasibility_audits/
stage4_2r3c3t2_six_basis_feasibility_20260731_e3222a1
```

Compact local evidence:

```text
docs/codex/audits/
stage4_2r3c3t2_six_basis_feasibility_20260731_e3222a1/
```

## Input authentication

The tool authenticated:

```text
T2 server audit
  e96f9538f5878ac745424d783e8f57c5ff41d61220b7d22ea66bfb1a08107d9c

T2 raw count / digest
  160
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

T2 runtime package fingerprint
  5544b0fe4bc50e03d4dc83183f846c9315db353dcb17c7179371f8fe1b046011

R3c3 four-basis audit bank
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

R3c3 four-basis controller bank
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

R3c1 baseline inventory
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e

frozen corrected feasibility implementation
  7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

All 160 T2 raw rows were rehashed and rechecked for identity, success,
51-state/50-action length, causal phase trace, and the locked context set.
All 32 extended baselines exactly matched their R3c1 source prefixes.
The frozen formal evaluator reproduced 32/32 saved pass values with maximum
margin error at most `1e-12`.

## Outputs and hashes

The large combined banks remain on the server:

```text
combined audit bank             4.0 MB
  0ef668da87d97012c101245556ee268b00cac535011b6025aa3fecc82bbb6081

combined controller bank        1.8 MB
  81e3c309d9055ba23587f4162641692680464d465f68342a845184e03b53b2fe
```

Only compact files were downloaded:

```text
feasibility JSON
  1c74a6c1ef05ff447eb1030f7a7ef1e13390eacfc74e795a556899405c95eacb

output manifest
  46bc47cfc1b8fb779b9ed1308e1d322364e80e780e8596e58e9b9cdc5d0dc2b5

comparative forensics
  e9827d44efe38cd59a5be37378df2dedeb05750fd6bb09da4ee397b12f0c0691
```

## Failure forensics

Remaining failed margins:

```text
best                                            -0.04148435
worst                                           -0.33841585
mean                                            -0.16326362
median                                          -0.13588835
```

Active constraints:

```text
position                                                14
post-arrival speed                                       2
```

Failure strata:

```text
delay 0 / delay 2                                  4 / 12
slew 1.0 / slew 0.9                               4 / 12
nominal / RZ_p10_m10                               4 / 12
minus_first / plus_first                            8 / 8
```

Coefficient saturation counts over the 16 failed contexts:

```text
early_mode0                15/16
early_mode1                16/16
deadline_mode0             15/16
deadline_mode1             15/16
held_transport_mode0       16/16
held_transport_mode1       16/16
```

The closest four failures use all six coefficients at absolute bound one.
Thus the failure is not caused by poor numerical conditioning or an optimizer
that stopped near zero authority.

Relative to the old four-basis oracle, T2 improves every failed context:

```text
improved / unchanged / worsened                    16 / 0 / 0
minimum margin gain                              0.00905088
maximum margin gain                              0.02944013
mean margin gain                                 0.01927152
```

The improvement is real but insufficient to cross zero.

Relative to the T1 six-basis temporal shape:

```text
improved / worsened                                  10 / 6
mean margin delta                              -0.00490688
median margin delta                             0.00303140
```

This mixed comparison shows that T1 and T2 temporal shapes are
complementary across contexts; replacing T1 with T2 is not uniformly better.
It does not change the failed six-basis gate.

## Error classification

```text
runtime/environment error                              no
deployment/import error                                no
raw or bank corruption                                 no
statistics/reporting error                             no
plant-restart failure                              not run
real closed-loop control failure                   not run
pre-execution six-basis design failure                 yes
R3c4 implementation authorized                          no
```

Two command-level incidents were kept separate:

- the first comparative-forensics call correctly rejected a missing old
  four-basis input path;
- the next call omitted activation of the existing server venv and the
  server's old default Python rejected type annotations.

Neither call created its target output. The corrected call sourced the
existing venv, authenticated every input hash, and produced the compact
forensic JSON.

## Decision

Do not implement or launch R3c4 from this six-basis bank. Preserve the T2 raw
and both combined banks.

Before any new TSC identification campaign, run one new prospectively frozen
read-only complementarity audit using all eight already authenticated bases:

```text
R3c3 local four
+ T1 long-separation two
+ T2 held-transport two
```

This does not weaken or reinterpret the failed six-basis gate. It tests the
remaining zero-new-TSC hypothesis that the six-basis replacement discarded
useful complementary temporal authority. If the eight-basis optimistic
oracle also fails, redesign must add genuinely new causal temporal authority
or a richer response model rather than implement R3c4.

