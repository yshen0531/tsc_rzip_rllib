# Fixed-1000 B0 result

B0 completed two canonical fixed-1000 q0 continuations through state64. Both
rollouts completed all 64 one-millisecond issues. Their R/Z/Ip, 14-coil,
48-wire and semantic-artifact records were exact. The independent raw auditor
reparsed 130 states, rebuilt 128 actions and checked 126 later readback-slew
transitions with no failure.

The q0 command is not a hold. From 1000 to 1064 ms, R_geo moved inward by
23.538658 mm, Z_geo stayed exactly at zero, and Ip ended 825.9437 A above the
source value. The final eight states moved inward another 2.324410 mm and had
a maximum one-millisecond R/Z speed of 0.318027 m/s. The whole trajectory's
largest one-step R displacement was 1.107517 mm.

Evidence:

- implementation: `d3ecd3cda5253d88b8253e261ef9b8d12a7f44e8`
- primary: `d6eaa48c4e158c48831c34aeb71c51ac455e253fab8e2868d92ec93d402868de`
- independent: `585c8825de755a7b0e7ec30bcaa3a636d9023cd7e0c8e3cf96dc401203ffef74`
- primary route: `ONE_MS_NR1000B0_BASELINE_COMPLETE_SIGNED_ID_DESIGN_ONLY`
- independent route: `ONE_MS_NR1000B0_INDEPENDENT_PASS`

Only the primary baseline has prospective development fit weight. The replay
has zero fit weight. This result opens design of a fixed-1000 signed temporal
response campaign; it does not qualify hold, stability, a model, Authority,
recovery, Recourse or feedback.
