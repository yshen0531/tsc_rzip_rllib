# ID-2Z16 full-F-prefix beam reachability result

## Result identity

ID-2Z16 ran once on the server from implementation revision
`c6ad775e881fa6e1b10c7104d49d3849c6b1cd08`. The frozen config SHA-256 was
`64da1123f1768d202c82f61480d207bc2ad049f1c308b2eafea942fff6e0b07d`.
Server validation passed the focused suite `11/11` and the complete 1 ms
suite `534/534` before any plant advance.

The campaign completed all `16/16` authentic rollouts, `1040/1040` plant
advances, `1056` states and `5280` required artifacts. The independently
recomputed artifact inventory was `62,190,927,744` bytes with digest
`55ac071618c21bebafd85832d7330e9f4a4d24933bf5d70df2ec826edc0287b3`.
Execution, interface, prefix, raw-integrity and exact selected-replay gates
passed. No model was fit and no calibration or holdout record was read.

## Frozen scientific result

No branch satisfied the six-state capture gate. Round zero selected
`f100__b4f4` and `f100__f8`. The ten round-one terminal results were:

| path | terminal worst score | max source distance (mm) | max speed (m/s) | max source-relative Ip |
|---|---:|---:|---:|---:|
| `f100__f8__f8` | 4.164724 | 28.254919 | 0.416472 | 2.44142% |
| `f100__f8__b4f4` | 4.317101 | 29.725755 | 0.431710 | 2.28990% |
| `f100__f8__f4b4` | 4.375450 | 29.624619 | 0.437545 | 2.29190% |
| `f100__b4f4__f8` | 4.441505 | 29.900274 | 0.444151 | 2.30074% |
| `f100__f8__b8` | 4.678887 | 30.801968 | 0.467889 | 2.13309% |
| `f100__b4f4__f4b4` | 4.815806 | 31.008356 | 0.481581 | 2.14640% |
| `f100__b4f4__b4f4` | 4.840602 | 31.115725 | 0.484060 | 2.14901% |
| `f100__b4f4__b8` | 5.019535 | 32.265243 | 0.501953 | 2.01484% |
| `f100__b4f4__h8` | 5.029850 | 32.840407 | 0.502985 | 1.41202% |
| `f100__f8__h8` | 5.117274 | 31.576280 | 0.511727 | 1.53481% |

The selected path was `f100__f8__f8`; its fresh replay was exact. It did
show finite transient utility: at state 48 its all-state diagnostic was
`23.207 mm / 0.2180 m/s / +1007.7 A`, compared with the selected terminal
maximum speed `0.416472 m/s` after the common hold. This is evidence that
continued F changes the trajectory, not evidence of a capturable terminal
set. The rebound after the active sequence is precisely why an instantaneous
or single-state minimum cannot replace the frozen six-state capture gate.

The final route is therefore
`ONE_MS_ID2Z16_FULL_F_PREFIX_BFH_BEAM_NO_CAPTURE_NEW_BASIS_REACHABILITY_REQUIRED`.
It closes this exact full-F-prefix, two-layer, width-two B/F/H grammar. It
does not prove global plant unreachability, absence of all useful B/F
authority, or failure of a controller that has a materially different
physical action basis.

## Reporting-only audit repair

The first independent audit incorrectly inserted `critical_replay` into the
round-one search population because the replay deliberately shares the
selected child's `round_index=1` and `path_id`. This produced only
`RECOMPUTE_PREFIX_CHECKS` and `RECOMPUTE_SCIENTIFIC_METRICS`; the raw
inventory, individual prefix checks, route and primary metrics were intact.

Reporting-only revision `2360a847` excludes the replay from search ranking
while retaining its separate exact replay check. Server tests then passed
`12/12` focused and `535/535` complete 1 ms tests. Re-auditing the immutable
raw produced `audit_passed=true`, no failures, the same scientific route and
the same primary result. The initial failed audit is preserved rather than
rewritten.

Evidence hashes:

- primary result: `a7c4096d8bb14e4c23a4871c687213e43d05c817c66e66ad33f53216ffcacc8a`;
- corrected independent audit: `463a70691205043f11f6d8de2ee9c3d8634a0c522157e1f467732689176cbb62`;
- initial audit FAIL: `f606f9deb2e79a4fbafbd3c44837811b3455e76a0f2f12e5ba1e880571ad77ac`;
- critical replay compact: `b2c1575188b304f075f9d9e855c66850b73c2415c569c148d216122187c6569b`;
- launch log: `ed6ed7673325713ffe574a1407f44a85235e123842e606e09a61ef7b288e3f81`.

After full-raw audit and local/remote compact hash recovery, only the exact
current-stage `rollouts/` tree (`63,154,824,228` bytes) and the temporary
two-file hotfix staging directory were removed. Compact evidence remains on
both machines; server free space was `118,100,652,032` bytes afterward.

## Route

Do not add a third B/F/H round, a wider beam, another constant F rate, a
nearby root or a larger predictor. The next bounded stage is a zero-new-TSC
physical-action-basis and reachability review. It must distinguish transient
transport from terminal capture, inventory all still-admissible Card15
directions against the exact moving prefix and current/headroom constraints,
and either freeze one materially different finite discriminator or record a
finite reachability blocker. ID-2Z16 has zero model-fit weight.

