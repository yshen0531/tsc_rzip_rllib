# Fixed-1000-ms authentic restart reconstruction

## Why this stage exists

The first real fixed-1000-ms interface attempt stopped after one hold issue.
Raw evidence proved that `1000ms/sprsina` and `1100ms/sprsina` are byte
identical (`5ead6983...afabe`).  The attempted successor began internally at
`1.1000 s`, jumped from the 1000-ms state to the former 1100-ms state and
violated the observed-current gate.  This is a source/restart identity failure,
not a control-model or plant-reachability result.

The authentic `1000ms/outputa` independently records the original initial run
from cycle zero through exactly `1.0000 s`.  Its `inputa`, geqdsk, coil and wire
files are intact and hash-bound.  Therefore a matching 1000-ms restart may be
reconstructed by repeating that initial run without loading the contaminated
restart file.

## Frozen execution

In isolated project-owned TSC workspaces:

0. run a zero-TSC preflight that rehashes all six source files, revalidates the
   frozen 1000-ms source/interface gate, authenticates the 0--1.000 s output
   clock and installed runtime paths;
1. copy the installed TSC runtime without runtime I/O;
2. copy only the authentic `1000ms/inputa`; explicitly require no `sprsina`;
3. run `gotsc` twice from the initial state;
4. require both outputs to start at 0 s and end at 1.000 s;
5. require both reconstructed 1000-ms R/Z/Ip, 14-coil and 48-wire semantics to
   reproduce the frozen source and one another;
6. require byte-identical regenerated `sprsoua` files whose hash differs from
   the contaminated 1100-ms restart;
7. build a project-owned canonical `1000ms` folder from the authentic input
   plus reconstructed outputs and renamed `sprsoua -> sprsina`;
8. perform two fresh reset/hold issues from that folder, each exactly one ms;
9. require internal output times 1.000 to 1.001 s, exact Card15 hold, observed
   per-coil change `<=0.3 A`, valid paired boundary/Ip/current limits, and exact
   semantic replay.

Maximum budget is four TSC invocations.  No retry is allowed after any TSC
invocation.  The immutable simulation source is never changed.  Partial raw is
preserved on failure.  Invocation attempts are counted immediately before the
TSC call, not after a successful return.

## Routes

- `ONE_MS_NR1000S0R1_INPUT_FAIL_NO_TSC`
- `ONE_MS_NR1000S0R1_OFFLINE_PASS`
- `ONE_MS_NR1000S0R1_INITIAL_RECONSTRUCTION_FAIL`
- `ONE_MS_NR1000S0R1_SOURCE_SEMANTIC_MISMATCH`
- `ONE_MS_NR1000S0R1_RESTART_1MS_FAIL`
- `ONE_MS_NR1000S0R1_CANONICAL_1000_RESTART_QUALIFIED`

A PASS creates only a project-owned, hash-bound canonical 1000-ms restart and
authorizes a new interface qualification against it.  It does not authorize a
model, Authority, Recourse or controller.
