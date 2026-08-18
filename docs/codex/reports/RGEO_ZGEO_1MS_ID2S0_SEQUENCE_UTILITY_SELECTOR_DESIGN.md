# ID-2S0 sequence-utility selector design

## Purpose

ID-2R1 proved that the unusual f03 hold/return response is exactly
repeatable. ID-2S0 uses that measured time series only to reduce the number
of subsequent real-TSC branches. It fits no model, runs no TSC, and makes no
authority claim.

## Frozen candidate grammar

The four exact arms are p04-minus, p04-plus, p07-minus, and p07-plus. ID-2S0
enumerates all sixteen ordered two-arm sequences. Every candidate replays the
exact f03 conditioner prefix, holds the first arm at issues 24--25, returns to
the admitted p03 nominal target at issue 26, holds the second arm at issues
27--28, returns at issue 29, and remains nominal through issue 33. All Card15
targets and every adjacent per-coil issue delta must be exactly representable
and at most 0.3 A.

For nomination only, the selector adds the already measured first-arm
response to a copy of the measured second-arm response shifted by three
states. This fixed additive construction is known to ignore history
interaction and must not be called a plant prediction. The real branch stage
exists specifically to test its error.

The selector examines all four-candidate subsets. For sixteen evenly spaced
R/Z target directions it computes the maximum projected displacement over
all selected sequence/time samples at states 25--34. Selection is
lexicographic: maximize the minimum directional progress, then mean progress,
then minimize the maximum angular gap of samples with at least 0.02 mm norm,
then select the lexicographically smallest sequence IDs. No metric, threshold,
kernel, neighbor count, or model is searched after seeing the result.

## Gates and route

The exact ID-2R1 PASS result, corrected independent raw PASS, five fresh
compact rows, ID-2P1 config, and ID-2R0 decision route are hash-bound. The
selector passes only if all sixteen exact action streams are valid, exactly
four candidates are selected, every one of sixteen target directions has at
least 0.02 mm nominal heuristic progress, and the selected sample geometry
has maximum angular gap below 180 degrees.

A PASS authorizes only a separately frozen four-branch TSC development
discriminator with a storage gate. It does not validate additivity,
authority, a tube, recovery, controller, MPC, transport, crossing,
adaptation, expert data, or RL. A FAIL stops this p04/p07 sequence grammar
before real TSC.

