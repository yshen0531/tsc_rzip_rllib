# Stage4.2R3c3T13S23D1 forensic report

## Result

The bounded D1 development search completed twice with byte-identical output:

```text
BOUNDED_TERNARY_SCHEDULE_SEARCH_FAIL_NEW_EXCITATION_ARCHITECTURE_REQUIRED
```

This is a deterministic finite-search/design result. D1 executed no Ray,
`gotsc`, TSC, controller, plant step, or snapshot and makes no control, MPC,
plant-reachability, or hidden-history robustness conclusion.

## Identity and validation

```text
branch
  codex/stage4_2r3c3t13s23d1-schedule-search
preregistered search commit
  b8cca13 Preregister bounded S23D1 schedule search
implementation/deployment commit
  7f66d4c Implement bounded S23D1 schedule search
config SHA-256
  a3962a63977c10644f1395be5b8ac25174201830f23e47b62465ec8244fcb8ff
implementation SHA-256
  ac0b82a7f550b6ea1cf4f4d71d231293af334a4ced38975be54b8ca85e8a224f
PACKAGE_MANIFEST.json SHA-256
  eae30ff9dec488f816fe1dcbdb1f917b67adabdb81b25682281974217648337e
SHA256SUMS SHA-256
  58f021975953f41c34daa813b144e1dec1121d10ab8b143a1ce78aca2fc9aa8e
declared package files
  457
```

Local manifest/hash/compile/JSON closure and an empty-directory deployment
simulation passed. Focused S23 plus D1 tests passed 15/15. The Windows full
suite ran 527 tests and had only the same 27 pre-existing Unix `resource`
import errors, with no D1 failure. Staging and installed server verification
passed; both Linux full suites ran 894 tests successfully with one expected
skip. Relevant log hashes are:

```text
staging package verification
  2a5c85b61998d851c314021662d62fee31691d4468a5816f973b59691fbcbfe8
staging full tests
  35c3f535fc85a829e6f59ed937f1f66d2295227c4c54325807ad4c58857edf3a
installed package verification
  2a5c85b61998d851c314021662d62fee31691d4468a5816f973b59691fbcbfe8
installed full tests
  662d186ebbb4c1f79d244fea13ff3651ba5a6d3b7c7a6e571e97fba84e90b660
```

All server Python work used only
`$HOME/tsc_all/tsc_simulation/venv_simu/bin/python`.

## Server evidence

```text
staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s23d1_7f66d4c
primary output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s23d1_audits/
  stage4_2r3c3t13s23d1_bounded_schedule_search_20260803_095124
independent output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s23d1_audits/
  stage4_2r3c3t13s23d1_bounded_schedule_search_independent_20260803_095421
primary log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s23d1_bounded_schedule_search_20260803_095124.log
```

The complete output is compact: detailed 43,636 bytes, summary 1,759 bytes,
and manifest 795 bytes. Their byte-identical primary/independent hashes are:

```text
detailed
  510c0dab1f08aa0e111001cb78c236cb622d1b1b13a7b783ad3e7c1489597bd8
summary
  c00d651454767781d88cf5d83ee861dd2a666b7fd069d47db3c6b24e211a9c0a
manifest
  22b2282734f67653f51d1501e0c9d3ca840bbd93b799752483be632df7ca863a
provenance digest
  4c15cb5f1db01a310cbd07b258c388343c881782d356ead82402ee117c2e6cc3
```

## Raw/source and construction checks

D1 authenticated all 360 immutable S21 raw files, all S22 hashes and route,
and the exact failed S23 config, implementation, detailed output, summary,
and manifest. It reproduced 40/40 baseline and 320/320 measured-probe formal
metrics, with the unchanged 16/40 and 99/320 formal pass counts.

It evaluated the frozen 320 signed templates at ten steps and all 40 contexts:

```text
signed issue constructions                              128000 / 128000
feasible sign pairs at every issue step                    103 / 160
feasible signed templates at every issue step               206 / 320
step 10--17 cancellation contexts                    40 / 40 each
step 18 cancellation contexts                              39 / 40
step 19 cancellation contexts                              35 / 40
```

The 103 feasible pairs were identical at every step. By amplitude they were
`13, 31, 34, 25` at `0.25, 0.50, 0.75, 1.00`; by active-coordinate count they
were `10, 29, 44, 20` for one, two, three, and four active coordinates. Thus
the D1 failure was not absence of action-feasible Card15 templates.

## Schedule-search failure localization

Cancellation-safe steps 10 through 17 produced exactly five admissible
four-knot sets under the frozen minimum separation. Each received its full
20,000 seeded candidates:

```text
10,12,14,16     20000
10,12,14,17     20000
10,12,15,17     20000
10,13,15,17     20000
11,13,15,17     20000
total          100000
```

An independent local reconstruction of the exact seeded requested-coordinate
matrices from the saved feasible-template IDs found zero global-condition
passes. The best normalized global condition was `7.2966498190`, above the
unchanged cap `3.0`. Therefore no actual-coordinate, per-slot, or late-novelty
candidate could be admitted. This is a random independent-block schedule
architecture failure, not evidence that the feasible template catalog lacks
a structured rank-16 design.

## Next route

D1 remains frozen and does not authorize S24. Post-D1 algebra found a new
structured schedule without changing any action/geometry/current threshold:
use the original H16 block patterns with amplitudes `0.25` for `++++` and
`+-+-`, and `0.50` for `++--` and `+--+`. All four sign-pair templates are in
the authenticated D1 feasible catalog. The requested matrix has normalized
global condition `2.8284271247`, slot condition `2.0`, and minimum late
residual `0.9428090416`.

That observation may only be frozen as a new S23R1 identity and revalidated
from actual coordinates in all 40 contexts. It is not a D1 PASS. No real
campaign, MPC, expert data, BC, DAgger, or bounded residual RL is authorized.

