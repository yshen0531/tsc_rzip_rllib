# ID2Z36 engineering-floor event-set result

Date: 2026-08-21

ID2Z36 passed its zero-TSC deterministic construction and independent
recomputation.

- implementation revision: `0246104bec239c0dfcb5440ea65aa71cb629211c`
- server focused tests: `3/3`
- server complete one-millisecond regression: `706/706`
- TSC calls / plant advances / model fits: `0 / 0 / 0`
- ID2Z35 fit rows: `0`
- payload SHA-256:
  `ace09ffba98b7bf60336452c9f4765ce5b8dc6bfe5bf71e33739eeba5e22c9a8`
- primary / independent SHA-256:
  `e5090d4deeb804db172f039290ad0513c1314773e4973897d576bba78860242a /`
  `9bd8335e0d894f129fb2d8a0a865060ae03550f427973eaf76aed4e7bb31145f`
- route:
  `ONE_MS_ID2Z36_ENGINEERING_FLOOR_EVENT_SET_PASS_FRESH_QUALIFICATION_ONLY`

The sole event remains `q_r:minus/effect-age 13`; its center and every
non-event point prediction are unchanged. The event half-width is now exactly
`[0.375 mm, 0.075 mm, 30 A]`, obtained by componentwise maximum with the
pre-existing engineering floors. No calibration outcome was used in the
calculation.

This authorizes only one fresh phase48 calibration followed, after PASS, by
an unopened phase54 blind family. It is not a calibrated transition tube or
feedback/controller/Authority/Recourse evidence.
