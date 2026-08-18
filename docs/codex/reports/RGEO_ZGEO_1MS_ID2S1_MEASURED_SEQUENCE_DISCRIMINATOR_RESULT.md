# ID-2S1 measured sequence discriminator result

## Verdict

ID-2S1 completed all four fresh TSC branches and the independent server-side
raw audit. The frozen route is:

`ONE_MS_ID2S1_MEASURED_SEQUENCE_PASS_FRESH_REPLAY_TUBE_DESIGN_ONLY`

This is a finite measured-sequence development PASS. It is not a model,
authority, tube, recovery, controller, MPC, transport, crossing, or
reachability PASS.

## Execution and evidence

- implementation revision: `109b41b808fe6084593c00eafb7f4b9a649c8471`
- config SHA-256:
  `fbf685fd55d2825cb284d1d45ade697f9837bf36ebb3637921a0c93509a9d319`
- primary result SHA-256:
  `2e799febc6682f070e5d2e2a68cdb7d57e238f152c2199270dc85cc5288ec14d`
- independent raw audit SHA-256:
  `77039905527cb8bbb85a042930dcf9734f44187732b0454afbdc1f1d90ea0e4a`
- reset / TSC / verified advances: `4 / 136 / 136`
- retained states: `140`
- required artifacts: `700`, `8,245,009,360 bytes`
- raw inventory digest:
  `168d1e073b534c0e7d84dfcd87b90457012d7bbf109ef46032393c3a722c0dca`
- server tests before TSC: focused `9/9`; complete one-ms suite `287/287`

All four matched f03 prefixes passed. The independent audit reparsed every
raw state, verified every outgoing Card15 action and final active input,
recomputed the inventory and all measured metrics, and reproduced the primary
route with no failures.

## Measured sequence geometry

Across the forty state-25--34 R/Z response samples:

- minimum progress over sixteen target directions: `0.037377 mm`;
- mean progress over sixteen directions: `0.269098563 mm`;
- maximum angular gap: `134.432692848 deg`;
- maximum absolute paired Ip response: `43.0516 A`.

All prospectively frozen measured gates passed. Per sequence:

| sequence | peak state | peak R/Z (mm) | peak norm (mm) | max abs ΔIp (A) | max actual-minus-additive R/Z (mm) |
|---|---:|---:|---:|---:|---:|
| p04+ then p07- | 27 | +0.610886 / -0.285409 | 0.674270 | 42.4445 | 0.017343 / 0.013155 |
| p07- then p07- | 29 | +0.145216 / +0.027454 | 0.147788 | 25.5184 | 0.012812 / 0.013181 |
| p07- then p07+ | 26 | +0.091424 / +0.019840 | 0.093552 | 25.5184 | 0.701085 / 0.280748 |
| p07+ then p04+ | 27 | +0.614097 / -0.299762 | 0.683354 | 43.0516 | 0.697069 / 0.280841 |

The two large interaction residuals are genuine measured failures of the
additive nomination heuristic for those sequence histories. They do not
invalidate the ID-2S1 route because additivity was prospectively descriptive,
not a gate. They are direct evidence that a future model/controller must use
the evolving causal history rather than sum isolated pulse responses.

## Route

ID-2S1 PASS authorizes only a separately frozen fresh replay and finite
repeatability/residual-reserve design for the same four sequences. The four
ID-2S1 records retain zero fit/calibration/holdout/expert/RL weight. A fresh
replay may measure deterministic repeatability and a finite discrepancy
floor, but it cannot by itself create a probabilistic or controller-grade
transition tube. Controller-grade authority and recourse remain independent
gates.
