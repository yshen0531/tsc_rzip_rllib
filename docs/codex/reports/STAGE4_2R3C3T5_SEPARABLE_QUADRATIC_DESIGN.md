# Stage4.2R3c3T5 separable-quadratic route diagnostic

Frozen prospectively on 2026-07-31 before server execution.

## Purpose

T4 rejected amplitude-only continuation within `2×`. T5 tests the remaining
zero-new-TSC model hypothesis using exact signed responses:

```text
prediction =
  baseline
  + sum(c_i * odd_i)
  + sum(c_i^2 * even_i)

odd_i  = (plus_i - minus_i) / 2
even_i = (plus_i + minus_i) / 2 - baseline
```

This model exactly reproduces each individual signed probe at `c_i = ±1`
when all other coefficients are zero. It omits every cross-basis interaction.
It is a route diagnostic, not a controller model validation.

## Exact code

```text
commit
  46e0f60dd0a927043534977927daa92d9f7adb16

diagnostic tool SHA-256
  7392458284ce7860e4e52ddfc59b7523f1bfcd96ab0426317a4ef76bc951dcaa

frozen T3 audit tool SHA-256
  e3c067574ebcb98dc6f30d4e29a41521c38368862fa23f01c0714e8d28dac093

frozen formal evaluator SHA-256
  7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

Validation before freezing:

```text
focused T5 tests                                      4/4
complete repository unittest discovery             563/563
Python compile                                          PASS
long-line and git diff checks                           PASS
```

## Exact authenticated bank inputs

```text
T3 manifest
  2c9389af0ea8d0f9538a0e4af34e604331981e77cfc0bc9c5bf353617c541b09

T3 audit bank
  f6cf5ae8642b68fc9947eaa1c2a3d18074e4e3e5be1f422f50ffa03f1a1a1970

T3 controller bank
  6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86

T3 feasibility
  08c253f7e8b66165704ec22e7b56c7e5c1abb1a30b8738be8b1d240211729744

T3 provenance digest
  a536183fc8e192fafc8c28bdc9897ecf3acb5dc9f0c5ed6257f236e2e8c03935

T1 raw inventory digest
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

T2 raw inventory digest
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

R3c1 baseline inventory digest
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

## Raw authentication contract

For every one of 32 contexts and eight bases:

- locate the exact plus and minus JSON.GZ under the frozen R3c3, T1, or T2
  source run;
- verify the per-file SHA-256 and recorded size where present;
- require `completed=true`, `success=true`, and empty failure reason;
- require at least the exact 35/37-state formal prefix;
- recompute odd response and require maximum error `<= 1e-12`;
- require both single-basis signed endpoint reconstructions to agree with raw
  to `<= 1e-12`.

Required aggregate:

```text
signed raw files                                      512/512
signed pairs                                          256/256
R3c1 baselines                                         32/32
T3 optimized pass/margin reproduction                  32/32
```

The completed read-only availability scan before implementation found all
256 pairs and zero odd-response error. It did not run this T5 optimizer or
reveal the T5 formal result.

## Frozen coefficient and timing contract

```text
basis count                                                 8
every coefficient                                      [-1,1]
formal arrival deadlines                             unchanged
formal hold endpoints                                unchanged
R/Z tolerance, speed, Ip, streak                     unchanged
T2 post-contract tail                                excluded
```

There is no amplitude expansion in T5.

## Frozen optimizer

For every failed T3 context:

1. enumerate the complete `{-1,0,1}^8` grid under the quadratic model;
2. retain the top 12 global grid starts;
3. add zero and the saved T3 linear optimum;
4. retain the top six starts for every unchanged allowed endpoint;
5. run SLSQP with bounds `[-1,1]`, `maxiter=400`, and `ftol=1e-12`;
6. report the best unchanged formal signed margin.

Saved T3 baseline-pass contexts return the exact zero-coefficient baseline,
preventing a diagnostic model from regressing certified finite passes.

## Required output

Emit one compact JSON containing:

- exact provenance and input hashes;
- authenticated signed-file count and a canonical inventory digest;
- T3 reproduction rows and errors;
- all 256 even-term magnitude rows;
- all 32 optimized context rows;
- formal pass, repair, regression, and remaining-margin counts;
- unchanged T3 odd-column condition result;
- explicit scientific guardrails.

Raw JSON.GZ, large banks, snapshots, and trajectories remain server-side.
The tool may not start Ray, `gotsc`, or TSC.

## Interpretation frozen before result

```text
formal 32/32, repairs 16/16
  separable quadratic terms are an optimistic candidate explanation;
  next step must validate cross interactions and identifiability in a new
  independent campaign before any controller

formal result below 32/32
  reject the interaction-free quadratic route and design genuinely new
  target-relevant temporal or actuator response directions
```

The existing odd-column condition result is only `11/32`. T5 cannot change
that measured identifiability result. Therefore even a formal `32/32` cannot
authorize R3c4.

Cross interactions, combined-action current safety, plant nonlinear
extrapolation, and real closed-loop behavior remain unvalidated. R3c4, BC,
DAgger, and bounded residual RL remain prohibited.
