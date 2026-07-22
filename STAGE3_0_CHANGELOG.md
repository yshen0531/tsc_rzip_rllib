# Stage3.0 changelog

## Direction change

Stage3.0 stops extending the five-node 100 ms CEM search. It accepts the user's clarified 120–150 ms arrival budget and adds an independent six-step tail plus explicit real-TSC Jacobian-based local optimization.

## Added

- 150 ms / 15-action episode while retaining the 10 ms control interval.
- Arrival endpoints at 120, 130, 140, and 150 ms.
- Persistence-through-150-ms hard gate.
- Eight-category-enforced Stage2.2 source nominals: 3 corner, 2 speed-safe, 2 gate, 1 position-front.
- Six independent three-mode controls at steps 9–14 (18 variables).
- 96-candidate deterministic time-margin screen.
- Up to three two-center trust-region SLSQP rounds.
- 72 real-TSC finite-difference probes and 24 real-TSC SLSQP proposals per round.
- Adaptive inward secant probes when a center lies on a coefficient bound.
- Cross-center provenance-safe IDs so an accidental duplicate trajectory cannot delete a required Jacobian column or shrink a fixed wave.
- Final 36-probe local identification.
- Offline MPC-compatible Jacobian and batch-gain bundle.
- Category-aware deterministic confirmation.
- Separate strict/minimax/speed-safe/relaxed/earliest-arrival Hall of Fame.
- Standalone launch, stop, verify, resume, prepare, screen, one-round, identify, confirm, and analyze scripts.
- Stage3.0 unit tests and complete package verification.

## Hard gate changes

The following are unchanged from Stage2.2 and are checked against the source run:

- 30 mm precise R/Z rectangular tube;
- 40 mm relaxed tube;
- three-sample position streak;
- 0.10 m/s endpoint speed;
- 0.10 m/s late RMS speed;
- 10 kA Ip tolerance;
- first three validated SVD modes;
- current and 3 A / 10 ms slew constraints.

The only task-level change is that arrival may occur between 120 and 150 ms, and an accepted trajectory must remain safe through 150 ms.

## Safety and correctness fixes included during audit

- Enforced nominal category quotas before deduplication; all eight sources can no longer silently become corner candidates.
- Validated source horizon, mode count, node steps, control interval, target, and hard gate.
- Used independent endpoint and RMS speed limits.
- Separated the precise-objective endpoint from the endpoint that actually passed a relaxed/strict gate.
- Included the frozen step-8 to optimized step-9 transition in tail smoothness.
- Made finite differences robust at global coefficient bounds.
- Represented unavailable Jacobian denominators as JSON `null` and froze the corresponding SLSQP variables, preventing unmeasured directions from moving through the smoothness term.
- Made fixed-size probe and SLSQP waves robust to cross-center duplicate physical sequences.
- Removed hard-coded 1100/1220/1250 plotting/artifact times; absolute times now derive from the source start folder and `dt_ms`.
- Retained inherited strict JSON/NaN protections and atomic result writes.
