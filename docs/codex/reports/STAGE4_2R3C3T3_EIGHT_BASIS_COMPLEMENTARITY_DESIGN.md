# Stage4.2R3c3T3 eight-basis complementarity audit

Frozen prospectively on 2026-07-31 before server execution.

## Purpose

Test the last zero-new-TSC temporal-complementarity hypothesis:

```text
R3c3 local four
+ T1 long-separation two
+ T2 held-transport two
= eight authenticated response bases
```

The failed post-T2 six-basis result remains failed. This is a new audit
identity and does not reinterpret, replace, or weaken that gate.

## Exact code

```text
commit
  1a75fffdd50dfcfde993d31ea1e63194f478235e

audit tool SHA-256
  e3c067574ebcb98dc6f30d4e29a41521c38368862fa23f01c0714e8d28dac093

frozen six-basis builder SHA-256
  62c748de11956b468b73dd0ae3937ce2a19b6f241da7281b0fe5e7cd0425f2ab

frozen formal evaluator SHA-256
  7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

The formal evaluator and signed-margin calculation are unchanged. The
six-basis search is generalized only by replacing six with eight variables:

```text
exhaustive {-1,0,1}^8 grid
top-eight grid starts
same four starts per allowed endpoint
same SLSQP bounds, maxiter=400, ftol=1e-12
```

## Exact inputs

```text
post-T2 six-basis manifest
  46bc47cfc1b8fb779b9ed1308e1d322364e80e780e8596e58e9b9cdc5d0dc2b5

post-T2 six-basis audit bank
  0ef668da87d97012c101245556ee268b00cac535011b6025aa3fecc82bbb6081

post-T2 six-basis controller bank
  81e3c309d9055ba23587f4162641692680464d465f68342a845184e03b53b2fe

post-T2 six-basis feasibility result
  1c74a6c1ef05ff447eb1030f7a7ef1e13390eacfc74e795a556899405c95eacb

T1 server audit
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd

T1 raw count / inventory digest
  128
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

T2 raw inventory digest
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

R3c1 baseline inventory digest
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

## Response and information contract

All eight columns are authenticated odd responses:

```text
odd response = (positive raw - negative raw) / 2
```

Every column ends at the unchanged 35/37-step formal horizon. T2's
post-contract cancellation tail is excluded from formal prediction.

The controller-facing bank contains no pair/history/source/raw/result/wire
labels. Audit provenance remains in a separate audit bank.

No response is scaled beyond its real identification amplitude:

```text
R3c3 four                              0.0075 each
T1 long-separation two                 0.0075 each
T2 held mode0 / mode1           0.0060 / 0.0075
```

## Authentication gates

Before optimization:

```text
T1 raw identity, success and causal trace              128/128
T1/T2/six-bank context equality                          32/32
R3c1 saved formal pass reproduction                      32/32
R3c1 baseline pass count                                 16/32
maximum saved-margin error                            <= 1e-12
six-bank and source file SHA matches                         all
```

Any mismatch aborts without a result.

## Frozen acceptance gate

For all 32 locked contexts:

```text
basis count                                                   8
each coefficient                                         [-1,1]
eight-column R/Z velocity rank / condition              8/8, <=25
formal timing                                           unchanged
R/Z tolerance                                             30 mm
speed threshold                                         0.1 m/s
Ip thresholds and arrival streak                         frozen
```

Aggregate acceptance:

```text
optimistic formal feasibility                              32/32
failed baseline contexts repaired                           16/16
baseline-pass regressions                                       0
condition pass                                             32/32
```

The gate may not be relaxed after result inspection.

## Interpretation

This audit executes no TSC and proves no controller. A pass authorizes only
prospective R3c4 implementation and validation; real TSC remains separately
gated.

A failure eliminates the remaining combination of already authenticated
temporal shapes. R3c4 then remains unauthorized and the next design must add
genuinely new causal authority or a richer plant/response model.

BC, DAgger, and bounded residual RL remain prohibited.

