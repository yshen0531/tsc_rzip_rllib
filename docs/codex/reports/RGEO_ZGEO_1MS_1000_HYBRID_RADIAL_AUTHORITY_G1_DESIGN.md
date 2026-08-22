# Fixed-1000 hybrid radial Authority G1 design

G1 is the single authorized nominal/action-semantics redesign after G0.  N0
showed that even-minus improves the early trajectory but rebounds late; G0
showed that even-plus strongly brakes the late trajectory but initially moves
in the wrong direction.  G1 combines those already measured roles rather
than adding a deeper amplitude to either closed matrix.

The frozen candidate reaches an initial even-minus level 4, 8, 12 or 16 at
one level per issue, then changes the scalar level by +2 per issue, crosses
zero, reaches +32 and holds through state64.  A fresh q0 and a depth-12 exact
replay give 6 rollouts / 384 advances.  All depths, transition rate and final
level are frozen before execution and may not be extended after the result.

The exact same terminal gates as G0 apply: state56--64 must improve fresh-q0
worst source distance by at least 15%, improve maximum 1 ms R/Z speed by at
least 0.03 m/s, keep Ip within 5%, and pass every hard interface/envelope
gate.  A transient dip cannot pass.  PASS opens only signed-Z/co-allocation
design.  FAIL closes this scalar even-axis schedule family and requires a
different action basis/nominal object before any model is fitted.
