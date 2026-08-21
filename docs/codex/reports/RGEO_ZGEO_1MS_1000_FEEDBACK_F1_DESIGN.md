# Fixed-1000 F1 deadband-abstention feedback design

## Purpose

F1 is the sole bounded repair authorized by F0. It tests whether the finite
q0-relative three-checkpoint controller can avoid a known policy error by
explicitly abstaining when the exact observed checkpoint error is already in
the unchanged tolerance deadband. It does not refit V0, alter the commands or
weaken any measured position gate.

## Frozen causal policy

At issues 24, 36 and 48, compute the exact current R/Z deviation from the
frozen same-state B0 q0 reference and the Euclidean error to the next command.

1. If the current error norm is at most `0.35 mm`, select `q0_noop`. The
   active target must already be exact q0 and remains q0 for the full slot.
2. Otherwise evaluate the four byte-fixed V0 h8 centers. Select the minimum
   predicted-error candidate only when its progress is strictly positive.
3. If outside the deadband and no macro has positive progress, stop before
   issuing the decision action. Do not choose a least-bad negative-progress
   macro.

This rule uses only the current exact observation, the frozen q0 reference,
the command and the frozen V0 artifact. It cannot query future TSC results.

## Matrix, budget and gates

The paths, decision issues 24/36/48 and endpoint states 32/44/56 remain byte-
identical to F0. The four fresh 64-issue rollouts are q0 baseline, path A,
path B and path-A replay. The maximum is four resets and 256 attempts, with
no retry.

All F0 hard, q0-reference, replay, 0.35-mm norm, 0.30-mm axis and 400-A
predicted-Ip gates remain. Active macro selections require positive predicted
progress. A no-op is eligible only through the exact `<=0.35 mm` current
deadband rule. In addition, each path's final command must satisfy the same
0.35/0.30-mm position gates at both state 56 and state 64. Every rollout ends
with q0 active.

PASS is only finite deterministic q0-relative deadband-feedback evidence and
may open a separate Recourse-L1 design. FAIL closes this deadband repair: no
nearby deadband, waypoint or macro-duration adjustment may follow. The next
route would instead model/qualify history-conditioned no-action tail and
continuation viability. All rows have zero fit weight.
