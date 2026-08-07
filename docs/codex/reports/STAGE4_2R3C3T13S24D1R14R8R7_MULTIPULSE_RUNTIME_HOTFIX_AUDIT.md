# Stage4.2R3c3T13S24D1R14R8R7 multipulse runtime hotfix audit

## Frozen evidence boundary

This audit was written after the first R8R7 multipulse launch returned, but
before any successful R8R7 multipulse trajectory, action event, model metric,
or multipulse scientific outcome existed. The R8R7 design, specs, action
matrix, schedules, thresholds, model/tube artifacts, phase-one evidence, and
scientific routes remain unchanged.

The accepted execution package is `d8d231e`; the implementation and package
fingerprints stored in the existing run remain immutable. The local
reporting-only inventory fix is `a39c5a9`. The controller-construction hotfix
is `4a8b558`.

## Immutable failed-attempt evidence

The first multipulse invocation returned all 32 Ray tasks and wrote 32 strict
JSON.GZ files before the primary raw-report writer stopped on a non-finite
derived aggregate. Independent server-side raw inspection found:

```text
raw files                                      32
raw bytes                                  145407
raw inventory digest
  7cadf53a6870980802009eef71e3d7c8e5c2707eb446d85f125851e239af160d
runtime success                                  0
full horizon                                     0
trajectory length in every file                  1
controller-trace length in every file            0
action events                                    0
common exception
  ValueError('D1R14R4 per-spec issue schedule changed')
```

The sole trajectory row is the post-reset initial state. No controller action
was returned and no `env.step`, plant advance, issue, cancellation, or
scientific response measurement occurred. This is a controller-construction
implementation error followed by a reporting serialization error. It is not
a TSC solver failure, restart failure, safety stop, controller-design result,
plant result, response-model result, MPC result, or reachability result.

The compact read-only diagnostic SHA-256 is
`9192a2bf00b45906c78fd552b6808db0388b554db934fefde0eddff1ab882530`.
The 32 failed files and the original execution/reporting logs must be moved
without modification into a stage-local `runtime_bug_evidence` directory and
authenticated before the active raw directory is reused.

## Root cause and semantics-preserving correction

R8R7 owns the prospective issue clock `(10,14,18,22)` in its overridden
`action()` method. Its constructor nevertheless passed issue step 10 to the
inherited R4 constructor, whose historical single-pulse validation accepts
only the R4 slots `(14,18,22)`. The exception therefore occurred before the
controller existed.

The hotfix passes the first valid historical R4 slot only as a constructor
compatibility placeholder, then restores the frozen R8R7 clock on the R8R7
subclass. The overridden R8R7 `action()` remains the sole owner of the actual
four issue/cancel pairs. No requested coordinate, Card15 conversion, action,
current bound, cancellation rule, causal feature, model, tube, metric, gate,
route, or experiment ID changes.

The raw reporter also represents unavailable extrema as JSON `null` instead
of `inf`; this changes only failure reporting and cannot turn a failed row
into a pass.

## Validation and continuation rule

The Windows project virtual environment passed focused tests `11/11` and the
full suite `1219/1219` after the hotfix. A focused constructor test proves
that the inherited placeholder is a valid R4 slot while the live subclass
clock remains the frozen R8R7 slot 10.

Continuation under the existing R8R7 identity is allowed only after:

1. all 32 failed files are authenticated and preserved byte-for-byte;
2. the installed package fingerprint used by the primary run remains the
   stored `d8d231e` fingerprint;
3. the hotfix source is executed from a separately hashed audit/runtime entry;
4. server compile, focused, and full tests pass in the existing virtualenv;
5. the active multipulse raw directory is empty before relaunch; and
6. exactly the same 32 frozen specs are executed once, with no resume of an
   applied physical trajectory because none previously advanced the plant.

If any failed file contains a plant advance or action event, or any stored
fingerprint/spec differs, continuation is forbidden and a new identity is
required.
