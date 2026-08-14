# R_geo/Z_geo 1 ms ID-1A context/anchor pilot design

Date: 2026-08-14 Asia/Shanghai

Frozen identity: `rgeo-zgeo-1ms-id1a-context-anchor-pilot-v1`

## Question

Can a small, connected HFS source neighborhood provide measurable, repeatable
contrasts for absolute issue time, recent causal history and controlled
pre-probe position, while all compared probes begin from the exact same q0
active command?

This is the missing discriminator before any plant model is fit. It does not
claim that position, time and latent history become perfectly orthogonal in a
deterministic plant. It asks whether the finite contrast geometry is strong
enough to support a structured contextual model rather than a source-clock
lookup.

## Matrix and budget

Every rollout starts from the canonical 1100 ms reset, runs for 24 one-ms
issues, and stops without retry. There are 28 rollouts and at most 672 plant
advances:

- two all-q0 baselines;
- p03/p07, both signs, at q0 issue2;
- p03/p07, both signs, at q0 issue10, with p03-plus and p07-minus repeated;
- the same four issue10 probes after a short p04-plus or p04-minus issue6
  pulse and exact issue7 q0 return;
- the same four issue10 probes after a bounded cumulative p03-minus or
  p07-plus prefix, stepped back to q0 through an adjacent level at issue7 and
  exact q0 at issue8.

All contextual probes therefore see q0 as the active command before issue10.
They differ only in exact, fully retained causal prefix and resulting current
R_geo/Z_geo/Ip. The probe is returned to exact q0 at issue11 and the remaining
window is recorded; tail extinction is not a gate.

## Why these prefixes

The short p04 histories are expected, from consumed design evidence, to leave
current R/Z/Ip close to the q0 path while changing the latent action tail.
They test near-matched visible state with different history. The cumulative
p03-minus and p07-plus prefixes are expected to create larger, differently
directed pre-probe displacements while returning the command to q0. They test
matched clock and command with a displaced operating point and different
history.

P03/p07 are not declared controller actuators. They are the best-conditioned
source-local pair in consumed design evidence and are tested on both sides.
The prior p07-plus cumulative counterexample is retained; no oddness,
superposition or gain monotonicity is assumed.

## Hard execution contract

Before each issue the same-state paired-boundary R_geo/Z_geo and same-state Ip
are exact, noiseless observations. Invalid boundary data fail closed. Exact
Card15 serialization, requested/applied/readback current, issue+1 effect,
absolute current, limiter, Ip and `<=0.3 A` adjacent slew gates remain hard.
The legacy runner's silent clipping must never be relied on. A successor over
`2 mm / 2 mm / 100 A`, any inner/outer-envelope violation, runtime failure or
raw-integrity failure stops before the next issue.

The finite novel successors are explicitly simulator-only empirical
identification exposures. No pre-action controller tube or recovery claim is
made from their post-action checks.

## Scientific gates

Execution/raw and the frozen repeatability pairs pass first. Every arm must
produce at least `0.01 mm` peak R/Z response and remain within `150 A` Ip
response. Each five-context issue10 response family must have numerical R/Z
rank two and a best two-ray condition no greater than 20.

For each short-history context, the pre-probe R/Z distance from late-q0 must
be no more than `0.1 mm` and Ip distance no more than `20 A`; at least one
same-probe four-state mean response must differ from late-q0 by `0.002 mm`.
For each cumulative anchor, pre-probe R/Z distance must be at least `0.1 mm`
and at least one same-probe mean response must differ by `0.005 mm`.

The early-versus-late q0 difference is reported rather than required: a null
time effect is informative and must not be turned into a post-result failure.

## Data role and route

Only a complete PASS opens these fresh records for development structure and
anchor design. Whole prefix/context families are atomic groups; steps may not
be randomly split. Calibration, holdout, expert/Oracle/fixture/BC/DAgger/RL,
controller safety and recourse remain forbidden.

A PASS authorizes a structured development-model comparison and a separately
frozen fresh calibration/holdout design. It does not authorize MPC, transport,
closed-loop tracking or online adaptation. A history or anchor contrast FAIL
stops model fitting and requires prefix/anchor redesign.
