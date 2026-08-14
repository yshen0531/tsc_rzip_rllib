# R_geo/Z_geo 1 ms ID-0 vector/tail pilot design

Date: 2026-08-14 Asia/Shanghai

Prospective identity:

```text
rgeo-zgeo-1ms-id0-vector-tail-v1
```

Frozen config SHA-256:

```text
668b0e4bb21166dc4d92fe4381c4177b4789b5a3139a176f7ab1b109393c31eb
```

## 1. Purpose and evidence class

ID-0 is the first campaign under the accepted TSC-only prospective empirical
identification contract. It is not a controller, hold, recovery, expert,
Oracle, calibration or holdout campaign. Its purpose is to measure source-
local two-sided response geometry, effect/tail length, finite repeatability
and early-versus-late context dependence before choosing a model.

E1 and A4 remain parked and unrun. ID-0 does not resume, relabel or use their
one-successor identity. NR2R1 holdout is not read. NR1/B0/C1a and A1--A3 keep
their frozen evidence roles and do not become ID-0 training rows.

If execution, raw integrity and all scientific gates pass, ID-0 compact
development records may be used only to select response directions, memory/
tail windows and a later prospective model structure. They remain forbidden
from uncertainty calibration, blind validation, expert/BC/DAgger/RL data and
controller safety qualification.

## 2. Exact matrix and budget

Every rollout independently resets to the canonical 1100 ms source and has
exactly 20 one-millisecond issues if complete.

```text
q0 baselines                                      2
directions                               p03, p04, p07
signs                                        plus, minus
early context, issue2                           2 repeats
late context, issue10                           1 repeat
total rollouts                                      20
maximum reset calls                                 20
maximum advance attempts/gotsc calls               400
completed states                                   420
completed required artifacts                     2,100
```

No failed, stale or uncertain advance is retried under this identity. Any
execution/interface/raw failure stops the campaign; already produced raw is
preserved. The order and per-rollout IDs are deterministic and part of the
implementation gate.

The q0 baselines issue q0 for all steps. An action arm issues q0 everywhere
except one full pulse:

```text
early: issue2 exact signed target, issue3 exact q0 return
late:  issue10 exact signed target, issue11 exact q0 return
```

The early response is observed through state20, giving effect state3 plus a
17 ms post-effect window. The late response is observed through state20,
giving effect state11 plus a 9 ms post-effect window. A terminal response that
has not closed does not authorize truncation; it routes to a separately
designed longer-horizon stage.

## 3. Actual Card15 coordinates

All six signed targets are explicit fourteen-field Card15 vectors in the
frozen config. They are derived prospectively from development pair indices
3, 4 and 7 using the exact existing Card15 lattice and the canonical q0
source. The implementation must independently reconstruct them from the
frozen NR2 spec and reject any mismatch before TSC.

The plus/minus labels are identifiers only. Quantization makes some actual
offsets unequal in magnitude; central symmetry, odd response and an exact
negative action pair are not assumed. Every analysis uses the actual
q0-relative fourteen-dimensional target vectors.

Every source->q0, q0->pulse and pulse->q0 adjacent target transition is
checked in exact decimal single-turn amperes before the runner. Equality at
0.3 A is allowed, any exact excess is refused, and all targets must remain
inside absolute current limits. The legacy runner's silent clipping may not
be reached or used.

## 4. Exact observation and empirical exposure

Before each issue, current same-step paired-boundary R_geo/Z_geo and Ip are
exact noiseless observations. All post-takeover causal observation and
controller-owned action/readback history remains available. This does not
make the successor known.

The two q0 baselines are directly supported by prior q0 replay through this
horizon. Every nonbaseline pulse, return and subsequent action-tail successor
is explicitly declared a new simulator-identification exposure without a
pre-action transition tube. The campaign therefore makes no plant-safe or
controller-safe claim.

At runtime, exact Card15/current/slew, limiter, paired boundary, Ip and the
50 mm R/Z plus 10 percent Ip outer envelope are hard checks. A non-q0 pulse
may issue only while the current state remains inside the 25 mm R/Z plus
5 percent Ip exploration-clearance envelope. The 2 mm/2 mm/100 A successor
caps are post-successor empirical stop thresholds, not a theorem or tube.
Any failure stops before the next issue.

## 5. Baseline and response definitions

The two fresh q0 baselines must match on checked R_geo/Z_geo/R_mid, Ip,
fourteen coil currents, forty-eight wire-current diagnostics, action stream
and four semantic artifact hashes at the frozen repeatability tolerances.
`sprsina` is diagnostic and is not silently equated or ignored.

For signed arm `j`, context `c`, repeat `r` and matched state `k`:

```text
d[j,c,r,k] = [R_geo, Z_geo, Ip]_arm[j,c,r,k]
             - mean_q0([R_geo, Z_geo, Ip]_baseline[:,k])
```

R/Z geometry metrics use metres internally. The effect-age 1--4 mean R/Z
vector is used for the first vector-geometry gate. Peak and terminal metrics
use the complete declared context window. Early repeated arms must reproduce
checked raw-derived observations at the frozen tolerances before their mean
is used.

## 6. Prospective scientific gates

The gate order is fixed:

1. input/evidence/config/package identity;
2. exact execution, boundary, Card15, current, slew, Ip and outer envelope;
3. complete raw inventory and independent reconstruction;
4. q0 and early-arm repeatability;
5. signal for every signed arm;
6. R/Z vector geometry and signed response cone;
7. Ip response cost; and
8. early-context terminal tail closure.

Required values are:

```text
peak R/Z norm for every signed arm                 >= 0.02 mm
R/Z mean-response rank                                      2
best two-column condition                               <= 10
largest angular gap of normalized signed vectors       <= 170 deg
maximum absolute q0-relative Ip response                <= 150 A
early terminal R/Z response norm                       <= 0.05 mm
early terminal / peak R/Z norm                         <= 0.20
early terminal absolute q0-relative Ip                  <= 10 A
```

The angular-gap gate tests whether the observed signed response rays provide
a local two-sided positive cone; it is not a global controllability theorem.
Rank and condition use the six actual effect-age-1--4 mean R/Z columns after
repeat averaging. Context differences are reported rather than converted
post hoc into a failure threshold. A PASS remains source-local and cannot
identify position dependence.

Route precedence is:

```text
offline/package fail                    -> no TSC
execution/interface/safety fail         -> stop, preserve raw
raw-integrity fail                       -> stop, no scientific verdict
repeatability fail                       -> redesign
signal/vector/Ip fail                    -> redesign
tail not closed                          -> longer-horizon redesign
all gates pass                           -> next design only
```

The exact route tokens are machine-frozen in the config.

## 7. Independent audit and artifact identity

The primary runner writes one compact rollout record per completed or partial
rollout plus a failure-classified stage result. A structurally separate
auditor reparses server raw, reconstructs every action from final raw timing,
checks the actual directory set, hashes every retained required artifact,
recomputes all response/repeatability/vector/tail metrics and verifies route
precedence. A scientific FAIL may still have an independent-audit PASS when
the auditor confirms that exact FAIL from intact raw.

Remote raw remains on the server. Only compact JSON, logs and checksum
evidence are copied directly without archives. A complete package must bind
the implementation revision, config, launcher, primary, auditor, focused
tests, every imported repository dependency and every evidence input. Server
Git is forbidden.

## 8. Authorization and next boundary

The user authorized staged implementation and server TSC after this design
checkpoint. Implementation may now add only the ID-0 primary collector,
independent raw auditor, launcher, package identity and focused tests without
changing the frozen config or scientific gates.

Only after local tests, exact package verification, installed-server tests
and zero-plant offline preflight pass may the 20-rollout/400-attempt campaign
run. A PASS may authorize only a new route decision between a longer-tail or
cumulative follow-up and a small-HFS position/history-factorization design.
It does not directly authorize a model fit, calibration, controller, MPC,
recovery, adaptation or RL.
