# ID-2Z23 moving-nominal discrete-vertex campaign result

Date: 2026-08-20

Final route:
`ONE_MS_ID2Z23_MOVING_NOMINAL_VERTEX_GEOMETRY_FAIL_NEW_ACTION_BASIS_REQUIRED`

ID-2Z23 completed all ten authentic canonical-source TSC rollouts and all
`650/650` verified plant advances. Execution, exact full-F prefixes, Card15,
raw inventory, run-root isolation and the preregistered zero-weight replay all
passed. The retained inventory before cleanup was `3300` files,
`38,869,329,840` bytes, digest
`6936d87d28bfc47b0f683a63ba5849777a77bb3e24ad72a72208575bef3e0f6d`.
The independent full-raw reparse reproduced the final route and every frozen
metric with no audit failure.

The scientific geometry gate failed at both moving-nominal phases:

- issue 24: h4/h8 maximum angular gaps were `338.632853/329.435408 deg`;
  weakest-best projections were `-0.359063/-0.590891 mm`;
- issue 32: h4/h8 maximum angular gaps were `241.470739/332.124057 deg`;
  weakest-best projections were `-0.104149/-0.653123 mm`;
- at issue 32, `p05-minus`, `p05-plus` and `p06-plus` had h4/h8 direction
  cosines `0.125176`, `-0.628839` and `-0.645857`, respectively;
- all Ip response caps passed, all four issue-24 individual persistence gates
  passed, and `p00-minus` also passed at issue 32. Those finite signals cannot
  repair the missing two-axis positive span or the other three issue-32
  persistence failures;
- capture diagnostics were `0/10` and are diagnostic only.

This is a clean moving-nominal action-grammar/design FAIL. It is not a runtime,
packaging, prefix, raw, replay, current-interface, model, controller, recovery,
MPC or global plant-reachability failure. The old held-state positive span did
not transport to either continuing full-F phase. Under the preregistered stop
rule, no nearby phase, duration, amplitude, third model or extra rollout is
authorized. The next decision must materially redesign the Card15 action basis
or takeover nominal before any new TSC or model fit.

Primary SHA-256:
`b45dbb6745b68ebddc89d0a8af4a484c016c758108074ce9ffb7c3c3a7967944`.

Independent audit SHA-256:
`3c1de6eea4c172e16db84edb67f43e39f251f8ab7923a55563499607fd9cd2ee`.

The server-side regression suite passed `626/626`; log SHA-256 is
`0d227d32f03986b17efd62a9b032910364ca532fb1c018250a71ba69cfe8ebbd`.
All thirteen compact/result/audit JSON files were retrieved and matched the
server byte-for-byte. Only after that recovery and the independent raw audit,
the exact remote ID-2Z23 `rollouts/` tree (`37G` by `du`) was removed under the
frozen cleanup rule; compact evidence and logs remain, and server free space
returned to about `92 GB`.
