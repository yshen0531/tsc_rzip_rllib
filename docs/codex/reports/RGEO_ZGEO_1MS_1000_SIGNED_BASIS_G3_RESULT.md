# Fixed-1000 signed Card15 action-basis G3 result

## Verdict

`ONE_MS_NR1000G3_SIGNED_ACTION_BASIS_INSUFFICIENT_ARCHITECTURE_REDESIGN`

G3 completed all 18 authentic rollouts and all 720 one-ms advances. The two
critical replays were exact. Independent raw reconstruction passed 738 states,
720 Card15 actions and 702 observed-current transitions. The verdict is a
scientific all-basis FAIL, not an execution, safety, replay, raw or reporting
failure.

## Quantitative result

The exact input basis remained rank four with condition `1.438375` and maximum
single-turn delta `0.145833 A`. Ip gates passed. The load-bearing failure was
the predeclared requirement that every signed input coordinate carry persistent
task-plane signal:

- `block2` odd-response norm was only `0.01082/0.01223 mm` at phase8 h4/h8;
- at phase24 it was only `0.01108/0.01239 mm`;
- its signed-pair separations were only `0.0216--0.0248 mm`, below `0.06 mm`.

Even, odd and block4 did carry material signed response. At phase8 h4 their
four-column matrix including block2 had condition `3.906`, maximum angular gap
`81.68 deg` and weakest-best projection `0.14351 mm`; at phase24 h4 the values
were `1.480`, `80.73 deg` and `0.06720 mm`. Block4 odd-response norms were
`0.44354/0.06187 mm` at phase8 h4/h8 and `0.11264/0.06563 mm` at phase24.
Thus the data contain a useful discrete action library, but the frozen
four-coordinate all-axis qualification is false.

## Architecture decision

G3 remains FAIL. `block2` is retained as a prospectively fit-eligible weak/
negative label; it is not silently deleted to make the old gate pass. No fifth
code, neighboring amplitude, phase or pulse duration will be tried.

The successor changes semantics from a qualified linear input basis to a
support-gated discrete candidate library. Safe candidates may have unequal or
near-zero utility; a direct outcome/value model must learn or abstain rather
than assume every actuator coordinate is authoritative. The next data stage
must use matched no-action branches and cumulative exact-return candidate
macros under whole causal histories, including even/odd/block4 signed actions.
Only that prospective dataset may support one bounded direct candidate-value
model. Authority/Recourse and feedback remain separate later gates.

## Evidence

- implementation revision: `406b4a74215cc4fac1c085555dd1161f196a73c1`;
- zero-TSC preflight SHA-256: `99e25ae6d57a49add7dd57c53e0b09d3afd8da1518fad6dd9d8e9ec9ad4ac50e`;
- primary result SHA-256: `5b4b93d26380edab242e7b05efa3472f7eda7e9067748bf49c891550773ecff0`;
- independent audit SHA-256: `51fc70e91f9f55f3a49056be7c9e53faea7c538e75bff30c5b39974ae8621e61`.
