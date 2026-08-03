# Stage4.2R3c3T13S24D1 forensic report

## Final result

S24D1 completed the preregistered zero-new-TSC contracted-amplitude replay.
The S24 source boundary passed every applicability condition, but the fixed
`0.25/0.25/0.225/0.225` candidate failed the unchanged static Card15 geometry
gate. The final route is:

```text
CONTRACTED_AMPLITUDE_PREFLIGHT_FAIL_REDESIGN_REQUIRED
```

This is an identification/action-schedule design failure. It is not a runtime,
deployment, raw, restart, causality, TSC, controller, MPC, or reporting
failure.

## Source authentication

```text
S24 active raw strict parse / identity / restart / causal     600 / 600
S24 successful baselines                                      24 / 24
S24 complete sequential success                              522 / 576
S24 allowed 0.50 cancellation failures                        54 / 54
actually executed 0.25 cancellations passed                1152 / 1152
archived pre-hotfix raw authenticated                         576 / 576
S21 raw authentication                                       360 / 360
S21 baseline / probe formal reproduction                      40 / 320
```

No S24 failure class changed, so the D1 source-stop route did not trigger.

## Static replay

```text
contexts / detailed event rows                               40 / 3840
finite issue plus cancellation constructions              7680 / 7680
issue gate pass                                           1920 / 3840
cancellation gate pass                                    3840 / 3840
central Decimal symmetry                                  1280 / 1280
rank-16 contexts / rank-4 slot blocks                        40 / 160
minimum late residual                                     0.94280904
requested global condition                                1.57134840
requested maximum slot condition                          1.11111111
new raw / snapshots / Ray / gotsc / TSC / controller       0 / 0 / 0 / 0 / 0 / 0
```

All 1,920 issue failures are the two contracted canonical patterns:

```text
++-- at 0.225                              960 failures
+--+ at 0.225                              960 failures
relative off-basis residual                1920 failures
desired/applied current cosine              960 failures
other issue criteria failures                 0
```

The active-coordinate floor was not the failure: the minimum was 0.1843174,
above the unchanged 0.18 gate. The actual failures were relative off-basis
residual 0.1392722 through 0.2791298 versus the 0.10 cap, and cosine down to
0.9538859 versus the 0.98 floor. Decreasing these two block amplitudes made the
exact Card15 reconstruction geometrically impure even though action, current,
finite, rank, condition, novelty, and cancellation gates remained safe.

Because the fixed candidate failed, D1 correctly emitted an empty sentinel
table and authorized no real TSC sentinel.

## Provenance

```text
local implementation checkpoint                              be7d2e1
local package checkpoint                                     d29303b
remote output
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1_audits/
stage4_2r3c3t13s24d1_contracted_amplitude_preflight_20260803_143246

detailed SHA-256
dc76c330bacb37c6b09e019f2a54c6d19c0b1c97aef96cf095c0458fd4a4d410
summary SHA-256
b063174025d5d82ac6762cac3167170ee05659d43e860c638a6ef3ae2dd41172
sentinel table SHA-256
cd47365195433e310853c7bdcce8c1d3248dcc793939e3003494fe8e7d830577
manifest SHA-256
52a432dc20cb76231c7eab72bd5c50af193e036b9b0a23c4348805a170d3955b
```

Staging and installed package verification passed 495/495 checksums, shell
syntax, JSON, compile, and 17 focused tests. Both the empty staging tree and
the installed canonical project passed 924 Linux tests with one expected skip.

## Next route

D1 must remain frozen and may not be edited or reinterpreted. The next stage
is the separately preregistered zero-TSC S24D1R1 minimum geometry-restoring
amplitude search. It keeps all physical and formal gates unchanged and searches
only a fixed Decimal grid for the two failed canonical patterns. Its pass may
authorize only a new-identity real-TSC sentinel over every one of the 54 S24
failure contexts. It cannot authorize a full identification campaign, MPC,
expert data, BC, DAgger, or RL.
