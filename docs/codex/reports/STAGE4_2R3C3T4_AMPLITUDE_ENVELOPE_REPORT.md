# Stage4.2R3c3T4 amplitude-envelope report

Date: 2026-07-31 (Asia/Shanghai)

## Result

The prospectively frozen T4 diagnostic rejects amplitude-only continuation
within the tested `2×` ceiling:

```text
profile / scale       formal pass   repairs   condition <= 25
transport 1.25×            16/32      0/16              2/32
transport 1.50×            16/32      0/16              2/32
transport 2.00×            20/32      4/16              0/32
uniform   1.25×            16/32      0/16             11/32
uniform   1.50×            16/32      0/16             11/32
uniform   2.00×            20/32      4/16             11/32
```

Neither profile reaches formal `32/32`, and no profile reaches both formal
and extrapolated-condition `32/32`. T4 runs no TSC and cannot authorize
R3c4.

## Exact revisions and paths

```text
branch
  codex/stage4_2r3c3t2-held-transport

diagnostic implementation commit
  8fbebe0078203665ba1d7b4707f6100d2ad4f306

diagnostic tool SHA-256
  cdcdd00ce78c19909b2e9859ee5b790a995020053a2bed509d148c1f07b5d027

prospective design commit
  32f6b6e5c469f6f50ffe67da275dc35430674860

result-forensics and compact-evidence commit
  824558ed96423a5beadd495457b4d70fc5a486bc

result-forensics tool SHA-256
  2c17cdeb0dd6aed28a31ef292ac1dc113a4b66f736a9c4bae5eb11f9f108d2ed
```

Server staging directory:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t4_amplitude_8fbebe0
```

Server result:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t4_amplitude_envelope/
stage4_2r3c3t4_amplitude_envelope_20260731_8fbebe0.json
```

Server log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t4_amplitude_envelope_20260731_8fbebe0.log
```

Compact local evidence:

```text
docs/codex/audits/
stage4_2r3c3t4_amplitude_envelope_20260731_8fbebe0/
```

## Authentication and inventory

The final run authenticated exact T3 manifest, audit bank, controller bank,
feasibility result, T3 audit tool, frozen formal evaluator, T1 raw digest, T2
raw digest, R3c1 baseline digest, and every R3c1 baseline file embedded in
the T3 bank.

T3 reproduction:

```text
contexts                                             32/32
pass/fail matches                                    32/32
maximum optimized-margin error                          0.0
saved T3 formal passes                               16/32
```

T4 expected and evaluated six profiles over 32 locked contexts. All 192
profile/context rows are unique and complete. All extrapolated response
matrices retain rank eight. Every final coefficient is inside its exact
profile bound.

Compact hashes:

```text
T4 result
  64c5ee745e93cc291c58e06974c7d6292594750a81b9e5dcf81966d32cd840f3

T4 log
  89cbed85105fbad91d75d224e76ecf17ff4cf0aa25c0fedf0e8225cd907dcc66

independent result forensics
  3d80815c43fa38de5a48cd34810ed8db9b37b64821865861718fe959629256d2
```

No large response bank was downloaded. The T3 banks remain server-side.

The remote installed T2 configuration used to reconstruct the exact source
context has SHA-256:

```text
3ded442f6c52792b7c2a7ae27f167fb0f2397addee32be947f8259849b994446
```

This is the preserved H1 runtime package used by the valid T2/T3 evidence.
The H2 local source fixes only reporting/resume behavior and was deliberately
not deployed over that runtime before the authenticated offline audits.

## Repair and failure forensics

At `1.25×` and `1.50×`, neither profile repairs any failed context.

At `2×`, both profiles repair exactly the same four contexts:

```text
p5 q1 / q2
minus_first / plus_first
nominal target
delay 2, slew 0.9
```

Uniform `2×` repaired margins range from `+0.00787` to `+0.01289`.
Transport-only `2×` repaired margins range from `+0.00149` to `+0.00600`.

The 12 remaining failures are the offset-target contexts. At uniform `2×`:

```text
best remaining failed margin                    -0.01799523
worst remaining failed margin                   -0.28940127
mean remaining failed margin                    -0.13003348
active position / post-speed constraints              10 / 2
```

At transport-only `2×`:

```text
best remaining failed margin                    -0.02413463
worst remaining failed margin                   -0.29267080
mean remaining failed margin                    -0.13455410
active position / post-speed constraints              10 / 2
```

Even after doubling the allowed mathematical envelope, most coefficients
remain at their expanded bounds in the failed contexts. The result therefore
does not support another amplitude-only identification campaign within this
ceiling.

## Condition result

Uniform scaling multiplies every column equally, so the condition result
remains the failed T3 result:

```text
condition pass                                      11/32
maximum condition                               78.154466
```

Scaling only T1/T2 transport columns makes the imbalance worse:

```text
scale         condition pass      maximum condition
1.25×                   2/32              96.017392
1.50×                   2/32             114.141939
2.00×                   0/32             150.770708
```

These are extrapolated column diagnostics, not new measurements. They show
that transport amplitude alone is the wrong parameterization even before
considering real nonlinear response and safety.

## Errors, warnings, and scientific classification

```text
final runtime/environment error                         no
final deployment/import error                           no
raw or bank corruption                                  no
statistics/reporting error                              no
formal timing change                                    no
real plant restart                                  not run
real closed-loop control                            not run
pre-execution amplitude-route rejection                 yes
R3c4 implementation authorized                           no
```

The final log contains two SciPy SLSQP warnings that an internal trial step
was outside bounds and was clipped. The implementation then clips every
returned candidate again before evaluation. Independent forensics found zero
final coefficient-bound violations. These are optimizer diagnostic warnings,
not runtime failures.

Two pre-run validation commands failed without creating output:

1. the first staging `--help` call omitted the remote project from
   `PYTHONPATH`;
2. a follow-up helper probe looked for the staging-only T4 module in the
   installed project `docs` package.

The corrected exact-path import probe passed, and the final nohup run used
the explicit project `PYTHONPATH`. Neither incident changed code, inputs,
profiles, optimizer semantics, or output identity.

One local all-JSON command exceeded a 30-second tool timeout. It was rerun
unchanged with a longer timeout and passed `1499/1499`.

## Validation and commands actually run

Local:

```text
T4 focused unittest                                  4/4
complete repository unittest                      559/559
Python compile / compileall                            PASS
repository JSON parse                           1499/1499
git diff and line-length checks                        PASS
downloaded SHA-256 checks                              PASS
independent aggregate/bound recomputation              PASS
```

Server:

```text
HOME/PWD/project/virtualenv and exact-path preflight
three staging script SHA-256 checks
Python compile and exact staging import
authenticated T3/baseline reconstruction
single exact PID monitoring to completion
strict JSON, row count, rank, bounds, and aggregate recomputation
stage process and gotsc absence checks
direct compact-file scp without archives
```

Actual Ray/TSC task count was zero. No trajectory, snapshot, controller
source, or server-project source file was created or changed.

## Decision

Reject amplitude-only continuation within the prospectively bounded `2×`
diagnostic. Do not increase coefficients again after seeing this result and
do not launch R3c4.

The next zero-new-TSC route discriminator is a separable nonlinear-response
audit, but only if all eight exact signed plus/minus trajectories can form
authenticated even-response terms:

```text
baseline + sum(c_i * odd_i + c_i^2 * even_i)
```

Such an audit remains an interaction-free approximation: it cannot validate
cross terms, combined-action safety, or a controller. If it also fails, the
next real campaign must identify genuinely new target-relevant temporal or
actuator directions rather than larger versions of the same eight columns.

BC, DAgger, and bounded residual RL remain prohibited.
