# Fixed-1000 cumulative temporal D1 result

D1 completed all 10 authentic trajectories and all 480 plant advances. The
experiment used two issue phases, two exact Card15 coordinates, both signs,
four-step ramps, four-step plateaus, exact four-step cumulative returns and a
common q0 tail. The two preregistered critical replays are exact in all
checked physical semantics.

The original primary result is retained as a reporting FAIL. It inherited
D0's 41-state/40-action replay cardinality although D1 correctly produced 49
states and 48 actions. Reporting revision `464ec7dc` performed zero TSC and
changed only that cardinality. The repaired result passes every unchanged
scientific gate, and a structurally separate raw audit passes.

Key results:

- phase 8 best R/Z condition `1.459061971`, sigma-min `0.6310575 mm`;
- phase 24 best R/Z condition `1.557923416`, sigma-min `0.2071960 mm`;
- all h4/h8 arm signals and signed separations passed;
- h4/h8 paired Ip gates passed;
- h12/h16 return-tail response remained inside the frozen `3 mm / 400 A`
  development envelope;
- repaired-primary SHA-256
  `bb0899377b10306f373b9b72517a0458dc3498cbd21f4927298e0fb5d4580148`;
- independent SHA-256
  `a17df1173bdd31c41893de376b4e6322a9eebfbbc9729c5dd89a3ab23c720e00`.

The finite conclusion is sustained two-axis development readiness around the
fixed 1000-ms source. It is not a point plant model, hold, capture, terminal
set, recovery, Recourse, feedback, waypoint tracking or R_mid-crossing PASS.
The remaining h16 odd response is explicit evidence that action history must
remain in the next short-horizon model.
