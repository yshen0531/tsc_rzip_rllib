# ID-2Z22 discrete-vertex moving-nominal preflight result

Date: 2026-08-20

Final route:
`ONE_MS_ID2Z22_DISCRETE_VERTEX_PREFLIGHT_PASS_ID2Z23_DESIGN_ONLY`

ID-2Z22 completed on the server with zero TSC calls, zero plant advances and
zero model fits. Its structurally separate audit reproduced the final route,
all four arm metrics and both task-plane geometry values.

The exact vertices `p00_minus4`, `p05_minus4`, `p05_plus4` and `p06_plus4`
share their complete state/action prefix through state 48. Relative to the
matched held branch, every arm retained its direction from state 52 to state
56 with cosine `0.9604--0.9956`. At state 52 the four-vector family has maximum
angular gap `110.627 deg` and weakest-best projection `0.06957 mm`; at state 56
the corresponding values are `108.136 deg` and `0.16820 mm`.

All eight issue-24/issue-32 prospective replacement schedules are exactly
Card15 representable, have maximum per-coil issue delta `0.3 A`, and retain at
least `103.9 A` absolute-current headroom. They replace F for four issues and
then resume F from the attained target. They do not add a residual to saturated
full-F and do not use continuous basis inversion or clipping.

This PASS authorizes only implementation and execution qualification of the
ten-rollout ID-2Z23 simulator-development campaign frozen in the design. The
held-state positive span is nomination evidence, not moving-nominal authority.
ID-2W1's state-25 geometry/state-26 collapse remains a load-bearing warning,
so ID-2Z23 must pass both moving-nominal phases separately. It cannot authorize
capture, recovery, MPC or real control.

Primary SHA-256:
`1faa7e4f6f478ab080f8fcce96a80496c86f3b700bdc18149c794916df34a95e`.

Independent SHA-256:
`529a8ef6be28e9d0aea887deec15e8798a86c61a59b06933ce0aaf49a65532f4`.

The installed server-side 1 ms regression suite passed `617/617`; its log
SHA-256 is
`64f5702f4f5df6f2b9c983e19766ecee07dfcdb26441f6f2e1837e9916f98259`.
