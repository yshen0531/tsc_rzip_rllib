# Fixed-1000-ms authentic restart reconstruction R2

## Frozen correction

R1 is final as `ONE_MS_NR1000S0R1_INITIAL_RECONSTRUCTION_FAIL`.  Its only TSC
call received the 1229-byte checkpoint `inputa`, whose Card00 has `IRST1=1`.
Without a restart file TSC correctly stopped in `problem_size` before creating
a state.  This is an initial-input design error, not a TSC, plant, interface or
control result.  R1 is not retried.

Read-only forensics found the original 13,800-byte non-restart input at
`HH70-PCS-ENV-LOW-FIELD-SIDE/prd_2-2_1000ms/inputa`.  Its Card00 has
`IRST1=0`; its saved `geqdsk`, `outputa`, coil-current and wire-current files
are byte-identical to the chosen fixed-1000 source.  R2 binds the full input
and all four matching state artifacts by SHA-256 and size before any call.

## Execution and gates

The zero-TSC preflight must pass all R1 source gates plus:

- the full initial folder is inside the frozen project root;
- its five files match the R2 config exactly;
- Card00 is non-restart (`IRST1=0`);
- its four state artifacts equal the target 1000-ms artifacts byte-for-byte;
- its output clock spans exactly 0--1.0000 s.

Then run the same maximum-four-call sequence as R1: two independent isolated
full initial runs, deterministic `sprsoua` plus semantic replay, a
project-owned canonical source, and two independent one-ms matched-hold
restart validations.  Every invocation is counted before the call.  No retry
is allowed.  Both immutable simulation folders remain read-only.

Routes use prefix `ONE_MS_NR1000S0R2`.  A final
`ONE_MS_NR1000S0R2_CANONICAL_1000_RESTART_QUALIFIED` authorizes only a new
canonical-source interface identity.  It is not model, Authority, Recourse or
controller evidence.
