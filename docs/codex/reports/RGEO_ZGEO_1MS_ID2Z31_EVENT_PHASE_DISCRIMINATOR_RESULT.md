# ID2Z31 qZ event-phase discriminator result

Date: 2026-08-21  
Implementation revision: `c5e8bc8f5f7ce6d0fdb3a4cde37dc77e6905703d`  
Config SHA-256: `f4bec9a86014ea8edbee89d8848e768ddb2f52bbf7116c8d87119df9101c86de`

ID2Z31 completed all six frozen simulator-development trajectories: six
resets, 438/438 verified plant advances, 444 states and 2,220 raw artifacts
(26,148,458,256 bytes). Exact execution, action, prefix, raw and issue-44
qZ+ replay integrity passed. The independent raw audit reproduced the route
and event map without failure.

Final route:
`ONE_MS_ID2Z31_EVENT_PHASE_MAP_PASS_GUARD_DESIGN_ONLY`.

The preregistered positive-R event detector produced exactly one event in
states 47--52 for every row:

| family | event state | one-step R increment |
|---|---:|---:|
| matched baseline | 50 | `+0.3432865 mm` |
| qZ+ issue 43 | 49 | `+0.3181785 mm` |
| qZ+ issue 44 | 49 | `+0.3198100 mm` |
| qZ+ issue 44 replay | 49 | `+0.3198100 mm` |
| qZ+ issue 45 | 50 | `+0.3397495 mm` |
| qZ- issue 44 | 50 | `+0.3471440 mm` |

The map and exact replay show a deterministic finite action-age/phase
interaction in this identity, not measurement noise. They do not identify
its physical cause.

Primary result SHA-256:
`1a9a9cdb7754fa1c10c663cf8a4013cf8ae970dad89527e063a433e98d011f25`.
Independent audit SHA-256:
`31c8bf53e57b6430ded2f185b99e2d0ff45ab6da1ae7d7963d970a8f1b9150c5`.

## Cross-stage bounded attribution and route decision

A no-fit scan of the complete retained ID2Z27 and ID2Z30 compact trajectories
shows that the event is not merely a near-event issue-43/44 hazard. qR+ and
qZ+ branches beginning at issues 32, 36 and 40 also place the event at state
49; their signed-minus controls and matched baseline generally retain state
50. The old model qualification evaluated only h1--h8 after each branch, so
these delayed state-49/50 consequences lay outside its evaluated horizon.

Therefore a narrow issue-43/44 mask would be false reassurance. The next
identity must expand the causal outcome through the exact return and delayed
tail and represent the event as an explicit hybrid/set-valued outcome. It
must not merely enlarge the smooth point tube or add generic network
capacity. A post-event development domain may be isolated prospectively, but
it still requires fresh signed data with enough tail to reveal a comparable
delayed event.

ID2Z31 fits no model and authorizes no feedback. Source capture,
Authority-L0, Recourse-L1 and final path/crossing goals remain open.

After compact recovery and independent hash verification, the exact
server-side `rollouts/` tree was deleted under the authorized cleanup policy;
the deletion is irreversible. Compact, result, audit and log evidence remain.
