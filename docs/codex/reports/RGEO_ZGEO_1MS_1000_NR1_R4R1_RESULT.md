# Fixed-1000 NR1 R4R1 result

R4R1 completed the new fixed-1000 one-millisecond interface qualification.
It used a prospectively reserved maximum Card15 excitation of 0.299 A while
retaining the unchanged 0.3 A hard command/readback slew limit.

The authentic server campaign completed six rollouts and 24 plant advances.
Hold, pattern A and pattern B each had a primary and replay trajectory. All
checked R/Z/Ip, 14-coil and 48-wire replay differences were zero. The primary
matched-hold evaluator checked 56 signed first-effect components. The
structurally separate raw auditor reparsed 30 states, rebuilt all 24 actions,
and checked 18 later readback transitions. It reported no failures.

Evidence:

- implementation: `3435b1862cbab53484154deb584839e51b3d23a1`
- offline preflight: `b91bf405268c7056500c58d70d9bdce9ac3db06d856c7156b1ff950ee668da7f`
- primary: `791375f0337d2e683f3c5b33b5bae254e03cd16660632acc2f6e3b93c5300644`
- independent: `934d44dc415123d8f8f04a57022500e95f8405ea3e7ea05dc3c499e48fd32827`
- primary route: `ONE_MS_NR1000S1R4R1_INTERFACE_QUALIFIED`
- independent route: `ONE_MS_NR1000S1R4R1_INDEPENDENT_PASS`

This PASS closes only the fixed-1000 restart/interface bootstrap. It does not
qualify natural-drift cancellation, a predictive model, task-plane Authority,
hold, recovery, Recourse or feedback. All fixed-1100 response/model/control
evidence remains historical and may be used only as design context. The next
stage must prospectively collect fixed-1000 matched baselines and bounded
signed temporal responses before fitting any model.
