# Fixed-1000 B1 mixed-history blind design

B1 is the only blind evaluation opened by C0. V0 remains byte-fixed and may
not be refit or widened. C0 and all B1 rows have zero fit weight.

The candidate still begins at issue 24. Before it, B1 composes two complete,
nonoverlapping conditioner macros at issue 0 and issue 12. The two unopened
histories are `even_plus -> odd_minus` and `even_minus -> odd_plus`. This
tests unseen history composition without changing candidate clock. Within
each history, a matched baseline and the same four candidates run through
state 48; one candidate per history has an integrity-only replay. The fixed
budget is 12 resets and 576 advances, with no retry or result-dependent arm.

Hard execution, exact Card15, slew, current, limiter, Ip, raw, replay, signal,
signed separation, geometry and return-tail gates remain unchanged. Every
h4/h8 R/Z/Ip component must lie in the original V0 artifact; maximum
directional regret is 0.03 mm and minimum robust h8 progress is 0.10 mm.

PASS qualifies the finite V0 model only for design of an independent
Authority/feedback sentinel at fixed 1000 ms. It does not itself establish
Authority, capture, Recourse, feedback or path tracking. FAIL closes V0 for
mixed-history use and does not reopen point-model or neural-capacity search.
