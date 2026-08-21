# ID2Z33 corrected moving-center delayed-tail D0 design

Date frozen: 2026-08-21

ID2Z33 is a new experiment identity that answers the scientific comparison
which ID2Z32 did not execute. ID2Z32 remains immutable and zero fit weight.
The phase matrix, horizons, signal thresholds, data roles and maximum budget
are unchanged; only the defective action construction is replaced.

For a branch at issue `p`, each of issues `p..p+7` applies the matched
transition-center increment for that issue plus or minus the frozen q_R/q_Z
residual increment. Thus phase 50 follows the still-moving center, while
phase 56 correctly applies a signed residual around the now-held center whose
nominal increment is zero. Issues `p+8..p+15` use an exact eight-slot Card15
bridge to the matched center target at `p+15`; later issues equal the center.
This is one general moving-center equation, not a phase-specific patch.

Before TSC, every branch must differ from baseline at one or more issues,
must differ only inside its frozen 16-issue action/return window, must have a
nonzero first branch issue, must return byte-exactly to the matched center,
and must satisfy all existing `0.3 A` slew, absolute current, prefix, queue,
effect-state and storage gates. Plus and minus streams at each phase/axis must
also differ from one another. Failure is `NO_TSC` and may not be repaired by
dropping a row or changing phase/share/duration.

The real matrix is exactly ten fresh resets and 730 maximum advances: one
zero-weight matched center, eight prospectively fit-eligible q_R/q_Z signed
branches at issues 50 and 56, and one zero-weight replay of issue50 q_Z+.
All complete future states after the branch issue through state73 are labels,
including return and delayed events. Scientific gates remain h4/h8 response
0.05/0.10 mm, persistence cosine 0.5, paired Ip 350 A, per-phase/horizon
angular gap 180 degrees and weakest projection 0.02 mm. Exact replay and raw
independent recomputation are mandatory.

A clean PASS authorizes at most two event-aware/set-valued development model
candidates followed by fresh calibration and unopened whole-family blind
validation. A clean scientific FAIL closes this corrected q cell without an
adjacent phase/share/duration or larger-network ladder. Neither outcome is
feedback, Authority-L0, capture, recovery, Recourse-L1, waypoint/path or
R_mid evidence.
