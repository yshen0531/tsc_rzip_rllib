# ID-2Z26R1 dynamic output-aligned preflight result

ID-2Z26R1 completed on the server with zero TSC calls, zero plant advances,
zero model fitting and zero calibration/holdout reads.  The final route is

```text
ONE_MS_ID2Z26R1_DYNAMIC_OUTPUT_ALIGNED_PREFLIGHT_PASS_CAMPAIGN_DESIGN_ONLY
```

Server focused tests passed 6/6 and the complete one-millisecond suite passed
648/648.  The primary and independent implementations both accepted all 11
prospective 73-issue streams.  Across issues 32--55 the exact signed cell was
rank two with condition `1.050715485445...`; the maximum actual issue slew was
`0.300000000000011 A`.  The minimum absolute-current headroom across every
complete stream, including the continuing-full-F diagnostic, was `101.5 A`.
All eight branches preserved the exact full-F prefix and reached the matched
center endpoint after the eight-issue return bridge.  The zero-weight replay
stream is byte-identical by construction.

The committed v1 preflight is preserved as a clean pre-execution design
failure: naive eight-positive/eight-negative Card15 application did not close
after repeated quantization.  R1 changed only the return construction and its
identity to an equal-fraction exact endpoint bridge.  It did not change the
nominal share, transition phases, output-aligned axes, gates or budget.

Evidence identities:

- implementation revision `22d203d078a8cb00f3f0d616ba7183c8430bddc9`;
- config SHA-256 `0c843a3f4ab61e5f693d7f37aef2961ccd319d7f54d3104c70590878443d8d8d`;
- primary SHA-256 `44ecac05709356db147ee1867df7bf9651a2f1e7f1c2532d0e33f3aedcd946cd`;
- independent SHA-256 `e9ee362fc8aed933b525521f43b08e6f9ccbb0a7dcb287faf98cefe239245192`.

This is exact static action/stream qualification only.  It authorizes one
separately prospective fresh simulator-development D0 campaign over this
matrix.  It is not real response, D0, positive span, capture, Authority-L0,
Recourse-L1, a model, controller, waypoint/path or R_mid-crossing evidence.
