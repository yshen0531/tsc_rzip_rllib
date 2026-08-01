# Stage4.2R3c3T13S5 implementation validation

## Identity

```text
local branch       codex/stage4_2r3c3t13s1-transition-sentinel
implementation     d048686 Implement T13S5 lattice-native split holdout
stage              Stage4.2R3c3T13S5
campaign           quantized_lattice_native_split_two_step_blind_holdout_v1
controller         quantized_lattice_native_split_probe_v42r3c3t13s5_v1
package            r42r3c3t13s5_lattice_native_split_holdout_v1
```

The implementation is independent Stage4.2R3c3T13S5 code. It does not
modify T13S4 raw or reinterpret the T13S4 preflight failure.

## Frozen matrix implemented

```text
contexts                                      4
development / blind holdout               34 / 34
baselines / signed probes                   4 / 64
total fresh authentic rollouts                  68
signed direction-window groups                  32
current components                            34272
identification directions                         4
physical controller modes                         3
```

Physical mode 0 is split only as an identification coordinate into its
non-coil-8 and coil-8 components. Modes 1 and 2 remain the other two
directions. The coil-8 direction has an exact local Card15 displacement of
at least `0.08 A`; the other directions use at least one exact significant
local formatter step.

The cancellation trace records both causal candidates. It must select an
exact return to the stored issue-center fields whenever that candidate
passes; only otherwise may it select the exact negative issued displacement
relative to the current baseline center. The raw recomputation independently
checks this priority and the selected Card15 fields.

## Local validation

```text
compileall                                            PASS
repository JSON parse                                 PASS
PACKAGE_MANIFEST / SHA256SUMS                 307 / 307
focused T13S5 tests                              13 / 13
complete Windows suite with existing resource shim 677 / 677
```

A direct Windows discovery without the repository's `resource` shim produced
27 import errors because the POSIX `resource` module is absent. No test body
failed. Repeating with the established Windows shim passed 677/677; this is a
local platform/environment distinction, not a T13S5 code failure.

## Empty-directory deployment simulation

The declared package was copied file-by-file into a new empty directory under
`.codex_tmp/`, without an archive. Validation in that isolated tree produced:

```text
declared files and SHA-256                        307 / 307
four replaced-tree inventory exact                     PASS
compile/import/self-test                               PASS
complete isolated suite                          677 / 677
expected isolated-data skip                              1
```

No undeclared source tree, Git checkout, network, or external Python package
installation was used.

## Server staging validation

The package was transferred directly, without compression, to:

```text
/home/yangshen0711/tsc_software/stage4_2r3c3t13s5_d048686
```

Using the existing server virtual environment, staging validation passed:

```text
SHA256SUMS                                      307 / 307
Linux bash -n for declared shell scripts              PASS
Python / JSON / scientific contract guards            PASS
focused T13S5 tests                              13 / 13
```

The subsequent installed-project command did not obtain an SSH session: the
endpoint timed out before the SSH banner/handshake. This is a connection or
sshd availability error, not an installed-package, TSC, controller, raw-data,
reporting, or scientific failure. At this checkpoint no T13S5 TSC campaign
has been started and no T13S5 raw exists by claim.

## Authorization state

T13S5 is implemented and staging-validated, but its installed-project full
suite, zero-plant offline gate, and real 68-rollout result are not yet
certified. Real TSC may start only after connectivity returns, remote project
integrity is read-only verified, installation succeeds, the installed full
suite passes, and the zero-plant offline gate passes exactly.

BC, DAgger, and bounded residual RL remain forbidden.
