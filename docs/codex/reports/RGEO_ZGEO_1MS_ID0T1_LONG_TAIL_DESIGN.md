# R_geo/Z_geo 1 ms ID-0T1 longer-tail discriminator design

Date: 2026-08-14 Asia/Shanghai

Frozen identity: `rgeo-zgeo-1ms-id0t1-long-tail-v1`

## 1. Question and evidence role

ID-0 passed execution, raw integrity, independent reparse, repeatability,
signed signal, Ip and source-local R/Z vector geometry. It failed only the
state20 terminal/peak tail ratio for three of six early signed arms. ID-0T1
asks one narrower question: do the same one-issue pulse and exact-return
histories close the unchanged tail gate by state32?

This is a TSC-only prospective empirical-identification discriminator. It is
not model training, controller safety, recovery, hold, Oracle, MPC or closed
loop. All ID-0 and ID-0T1 records remain design evidence. Even a PASS only
permits a separately frozen small-HFS position/time/history factorization
design; it does not authorize fitting a dynamics model.

## 2. Frozen matrix and budget

The campaign contains exactly eight fresh canonical-source rollouts:

- two all-q0 baselines;
- one `plus` and one `minus` arm for each actual p03, p04 and p07 Card15
  vector used by ID-0.

Every signed arm issues q0 at steps 0 and 1, the actual frozen direction at
issue 2, exact q0 at issue 3, and q0 through issue 31. Each rollout therefore
has 32 advance attempts and 33 states (`1100..1132 ms`). The hard maximum is
eight resets and 256 attempts/gotsc/verified advances; retry after any
attempt is forbidden. A complete result has 264 states and 1,320 required
artifacts. No state33 or issue32 is allowed.

## 3. Observation, action and safety semantics

Before issue `k`, the same-state paired-boundary `R_geo/Z_geo` and same-state
`Ip` are exact/noiseless truth, and the complete causal history since the
1100 ms takeover is available. This does not reveal state `k+1` before the
action. Invalid or unpaired boundary data fail closed.

The issued 14-vector must reconstruct the frozen Card15 fields exactly. Both
requested and observed adjacent single-turn changes must be at most `0.3 A`,
and absolute current limits are checked before the legacy runner can clip.
Every state is checked against limiter validity, Ip and the frozen outer
envelope. The prospective per-successor empirical stop cap remains
`2 mm / 2 mm / 100 A`; it is a simulator-exploration trip threshold, not a
controller-grade transition bound. After any failure no further issue is
allowed.

## 4. ID-0 prefix identity gate

The two new q0 rows and six new signed rows must reproduce the corresponding
consumed ID-0 histories through state20. Each new row is compared with both
ID-0 repeats where they exist. Time, same-state geometry, Ip, all 14 actual
coil currents, all 48 wire currents, prior issued actions and the four
semantic artifact hashes must satisfy the frozen ID-0 repeatability
tolerances. `sprsina` is retained and hashed but remains diagnostic rather
than a byte-identity gate.

A prefix mismatch is a replay/evidence failure, not a tail result. The new
states 21 through 32 are separately declared tail exposures and cannot be
used to retroactively weaken the prefix gate.

## 5. Unchanged scientific gate

For each signed arm, subtract the matched mean of the two fresh q0 baselines
at the same state. Let the peak response be the maximum R/Z Euclidean norm
over states 3 through 6. At state32 require all three clauses:

```text
terminal R/Z response norm        <= 0.05 mm
terminal / peak response ratio    <= 0.20
terminal absolute Ip response     <= 10 A
```

The threshold is exactly the ID-0 gate evaluated at the longer frozen state.
No post-result relaxation is allowed. A state32 FAIL ends the automatic
horizon route and requires an architecture/experiment review; it does not
authorize state40. A PASS authorizes only ID-1 design for small-HFS
position/time/history factorization.

## 6. Result routing

Route precedence is input/offline, package/deployment, execution/interface,
raw integrity, ID-0 prefix identity, then scientific tail result. A runtime,
artifact or prefix failure must never be interpreted as plant tail behavior.
Raw is independently reparsed on the server, and only compact result/audit
records may be returned locally. No server raw becomes a fixture.

## 7. Explicit non-authorizations

ID-0T1 does not authorize new directions, cumulative amplitudes, an extended
horizon ladder, multi-anchor transport, training/fitting, calibration,
holdout opening, expert/BC/DAgger/RL data, controller implementation, MPC,
hold/recovery or deployment claims. Those remain downstream gated stages.
