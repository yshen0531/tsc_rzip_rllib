# ID-2Y1 late mixed-braking hold design

## Question

Can the best measured p03 transport be retained through level64 and then,
after its full-slew increments end, can finite p04-minus braking with an
optional small p07-plus correction produce a source-local nominal hold
candidate?

This is the final bounded hand-designed branch discriminator.  It is not a
model, controller, recovery policy, transition tube, waypoint or reachability
test.

## Why this differs from ID-2X1

ID-2X1 stopped p03 at level32.  Its residual allocations changed R/Z by only
about 1--2 mm at common state65 and all branches reached the 25 mm R or Z
preissue clearance before the terminal window.  The independent p03-level64
run instead retained substantially more Z correction, ending at
`R=-25.3167 mm`, `Z=+13.4719 mm` at state86.  It therefore leaves a more useful
late geometry for outward-R braking, although it did not hold by itself.

P04-minus cannot be superposed on a continuing p03 full-slew issue: both use
real Card15 coordinates and the per-coil per-step cap remains 0.3 A.  ID-2Y1
therefore begins residual allocation only after the level64 p03 increment.

## Frozen branches

Every branch starts from the canonical 1100 ms source and issues q0 at issue0.
Issues1--64 are the exact p03-minus stride-one levels1--64.  The complete
states0--65/actions0--64 prefix must match the independently audited ID-2W3R1
record before any branch can create a scientific result.

The four fresh branches are:

1. p03L64, then p04-minus depth6, then hold;
2. p03L64, then p04-minus depth12, then hold;
3. p03L64, then p04-minus depth12, p07-plus depth4, then hold;
4. p03L64, then p04-minus depth16, p07-plus depth4, then hold.

Only one direction is incremented per issue.  The exact 14-field Card15
target is accumulated; clipping, a software queue, silent fallback and an
assumed linear plant response are forbidden.  All targets must pass an
offline exact-lattice enumeration, per-coil slew `<=0.3 A`, absolute-current
limits and a frozen minimum current-headroom gate before any TSC run.

The horizon is 104 issues.  The terminal evaluation window is states96--104.
Each branch holds its final exact target from its declared hold-start issue
through issue103.

## Runtime and evidence gates

- at most four resets, 416 advance attempts/`gotsc` calls/verified advances,
  420 retained states and 2,100 required raw artifacts if complete;
- exact/noiseless same-step paired-boundary R_geo/Z_geo and Ip are observed
  before every issue; the future successor is not known;
- exact source reset, complete p03L64 causal prefix, Card15 target,
  issued/readback slew, absolute current, queue/effect timing, limiter,
  paired-boundary and Ip checks remain fail closed;
- the empirical per-successor caps and inner/outer envelopes are unchanged;
- a branch may stop and allow the next independent reset only when all stop
  reasons are among `PULSE_CLEARANCE_R/Z/IP`; any other failure aborts the
  campaign;
- raw is retained uncompressed and independently reparsed on the server;
  no server raw is downloaded as a fixture.

The storage preflight requires at least 65 GB free, estimates at most 28 GB
for this campaign, and requires at least 35 GB after that estimate.  Older
fully audited p03-only raw may be removed only by exact verified path after
its compact evidence is tracked; the latest X1 raw is retained.

## Scientific gate and routes

For a complete branch, states96--104 must satisfy the unchanged nominal hold
conditions:

- maximum one-step `|dR_geo|` and `|dZ_geo| <= 0.1 mm`;
- terminal-window net `|dR_geo|` and `|dZ_geo| <= 1 mm`;
- terminal-window net `|dIp| <= 100 A`;
- source-relative terminal `|R_geo|, |Z_geo| <= 25 mm` and
  `|Ip-Ip_source| <= 5%`.

At least one branch must complete and pass.  PASS nominates only a finite
Nominal-H1 candidate and requires a fresh repeatability identity followed by
bounded-tube recourse qualification.  It does not authorize controller or
MPC execution.

A clean scientific FAIL ends the hand-tuned ramp ladder.  The next route is
a prospectively bounded sequence/control-utility search or feedback design
with explicit R/Z/Ip/current/clearance objectives, followed by fresh TSC
validation.  It is not another p03/p04/p07 depth sweep and not a larger neural
model.

The stage is route/control-design evidence only.  Model fitting, calibration,
blind holdout, expert/BC/DAgger/RL/fixture use, controller deployment,
recovery, transport, waypoint, R_mid crossing and online adaptation are all
forbidden.

