# R_geo/Z_geo 1 ms NR2R2B0 source baseline result

Final route:

```text
ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP
```

NR2R2B0 completed all 6 independently reset 32-step all-q0 trajectories and
all 192 authentic advances without a runtime, TSC return-code, abnormal-state,
boundary, Ip, current, slew or Card15 failure.  Primary and independent raw
audits agree.

The frozen repeatability gate nevertheless failed because `sprsina` was not
byte-identical across resets.  All four other required artifacts and every
physical quantity checked were exactly repeatable at matching times:

```text
R/Z/R_mid                              0 absolute difference
Ip                                     0 A difference
14 coil currents                       0 A difference
48 wire-current components             0 A difference
Card15 fields                           exact
inputa/geqdsk/coil/wire file hashes     exact
sprsina hashes                          different on states 1..32
```

This is a frozen artifact/restart-identity repeatability failure until the
semantic fields inside `sprsina` are prospectively audited.  It is not
evidence of physical-output nondeterminism, but the result may not be
retrospectively relabelled PASS.

More importantly for control, q0 is not a source hold.  In 32 ms it drifts by
up to `17.60 mm R`, `23.44 mm Z` and `335.72 A Ip`; during terminal states
24--32 it still moves up to `0.618 mm R / 0.806 mm Z` per 1 ms step, with
`3.94/5.82 mm` net R/Z drift.  Returning coil currents to q0 therefore cannot
serve as the required backup or recovery continuation.

## Classification

- execution/runtime/interface/safety: PASS within the finite 192-step matrix;
- physical output repeatability: exact descriptive evidence, but not formal
  B0 PASS because the artifact gate failed;
- exact artifact repeatability: FAIL, isolated to `sprsina`;
- q0 short hold: genuine finite-envelope FAIL;
- model/controller/closed-loop tracking: not run.

No new model fitting, training, controller, MPC, RL, branch replay or expert
data was produced.  Raw stays server-side; compact evidence is under
`docs/codex/audits/rgeo_zgeo_1ms_nr2r2b0_20260813_f4b1537/`.

## Required pause

The revised route required a qualified source hold/backup before position
anchors or active probes.  NR2R2B0 proves q0 cannot fill that role.  Designing
an active recovery now requires a real architecture choice: a separately
bounded feedback/recovery controller or a finite branch/replay search with an
independently safe continuation.  The present data contains no already
qualified choice.

Per the user's instruction, development pauses here rather than guessing a
controller or using the expected information gain from a new probe as its own
safety proof.  Any successor must first freeze:

1. the load-bearing versus identity-only semantics of `sprsina`;
2. a bounded source hold/recovery candidate and independent safety proof;
3. a small recovery discriminator matrix with exact hard stops; and
4. a rule that no position atlas/probe begins until recovery passes.
