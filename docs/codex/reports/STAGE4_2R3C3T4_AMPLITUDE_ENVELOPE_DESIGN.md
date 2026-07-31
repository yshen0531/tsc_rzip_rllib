# Stage4.2R3c3T4 amplitude-envelope route diagnostic

Frozen prospectively on 2026-07-31 before server execution.

## Purpose

T3 proved that all eight authenticated temporal columns improve every failed
context, but the frozen `[-1,1]` envelope repairs none and almost every
coefficient saturates. T4 asks a narrower route-selection question:

```text
How much unvalidated response-amplitude extrapolation would be required
before the same eight temporal directions become optimistically feasible?
```

T4 is not a new T3 gate and cannot reinterpret T3. It runs no TSC, validates
no larger action, and cannot authorize R3c4.

## Exact code

```text
commit
  8fbebe0078203665ba1d7b4707f6100d2ad4f306

diagnostic tool SHA-256
  cdcdd00ce78c19909b2e9859ee5b790a995020053a2bed509d148c1f07b5d027

frozen T3 audit tool SHA-256
  e3c067574ebcb98dc6f30d4e29a41521c38368862fa23f01c0714e8d28dac093

frozen formal evaluator SHA-256
  7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

Local validation before this design was frozen:

```text
focused T4 tests                                      4/4
complete repository unittest discovery             559/559
Python compile                                          PASS
long-line and git diff checks                           PASS
```

## Exact authenticated inputs

```text
T3 manifest
  2c9389af0ea8d0f9538a0e4af34e604331981e77cfc0bc9c5bf353617c541b09

T3 audit bank
  f6cf5ae8642b68fc9947eaa1c2a3d18074e4e3e5be1f422f50ffa03f1a1a1970

T3 controller bank
  6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86

T3 feasibility result
  08c253f7e8b66165704ec22e7b56c7e5c1abb1a30b8738be8b1d240211729744

T3 shared provenance digest
  a536183fc8e192fafc8c28bdc9897ecf3acb5dc9f0c5ed6257f236e2e8c03935

T1 raw inventory digest
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

T2 raw inventory digest
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

R3c1 baseline inventory digest
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

Every one of the 32 R3c1 baseline raw files must also match the size and
SHA-256 embedded in the T3 audit bank.

Before extrapolation, the tool must reproduce:

```text
T3 context identity                                   32/32
T3 optimized pass/fail                                32/32
T3 optimized signed margin                    error <= 1e-9
T3 eight-column rank/condition                        32/32
T3 formal pass count                                  16/32
```

Any mismatch aborts without an output.

## Frozen diagnostic profiles

The original T3 basis order is unchanged:

```text
0  R3c3 early mode0
1  R3c3 early mode1
2  R3c3 deadline mode0
3  R3c3 deadline mode1
4  T1 long-separation mode0
5  T1 long-separation mode1
6  T2 held-transport mode0
7  T2 held-transport mode1
```

Evaluate exactly three amplitude scales:

```text
1.25
1.50
2.00
```

under exactly two profiles:

```text
transport_only
  bases 0..3 remain bounded by [-1,1]
  bases 4..7 expand to [-scale,+scale]

uniform_all
  all eight bases expand to [-scale,+scale]
```

The implied largest individual identified amplitude at scale two is
`0.0150`; T2 mode0 reaches `0.0120`. These are mathematical extrapolations,
not executed or safety-certified actions.

## Frozen optimizer

For every failed T3 context and every profile:

1. enumerate the full scaled ternary grid;
2. retain the top 12 global grid starts;
3. add zero, the saved T3 optimum, and the bound-scaled T3 optimum;
4. retain the top six starts for every unchanged allowed endpoint;
5. run bounded SLSQP with `maxiter=400` and `ftol=1e-12`;
6. report the best unchanged formal signed margin.

Baseline-pass contexts return the exact zero-coefficient baseline. The
formal deadlines, hold horizons, target, R/Z/Ip thresholds, and arrival
streak are unchanged.

For route diagnostics only, scale the measured velocity columns by the same
profile and recompute rank/condition. This extrapolated condition number is
not identification validation.

## Required output

Emit one compact JSON containing:

- exact input hashes and provenance digest;
- T3 row-by-row reproduction;
- all six profile summaries;
- all 32 per-context formal results per profile;
- extrapolated rank/condition per context;
- the first passing tested scale for every failed T3 context;
- explicit scientific guardrails.

No combined bank, trajectory, snapshot, Ray task, or TSC process may be
created.

## Interpretation frozen before result

```text
transport_only reaches formal 32/32 by scale <= 2
  evidence for a new, independently preregistered transport-amplitude
  identification campaign; not permission to run a controller

only uniform_all reaches formal 32/32 by scale <= 2
  broader causal authority is required; transport-only identification is
  insufficient

neither reaches formal 32/32 by scale <= 2
  reject amplitude-only continuation within this diagnostic ceiling and
  prioritize genuinely new temporal shapes or a richer response model
```

Even if formal feasibility reaches 32/32, an extrapolated condition failure
still requires a new identifiable parameterization. Even if both quantities
reach 32/32, T4 cannot authorize R3c4 because linearity, combined-action
safety, current utilization, and real closed-loop behavior were not tested.

R3c4, BC, DAgger, and bounded residual RL remain prohibited.
