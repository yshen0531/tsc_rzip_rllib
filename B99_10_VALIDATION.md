# B99.10 Train-First — Validation Performed

The package was not run against TSC/gotsc and was not run on a 192-worker Ray cluster in this environment.

Completed checks:

1. Python `py_compile` / `compileall` for all Python files.
2. JSON parsing for every configuration.
3. MPO config → train config → TSC config reference validation.
4. Bash `-n` validation for all launch, resume, probe and immediate-stop scripts.
5. Static confirmation that no graceful SIGTERM/SIGINT handler was added.
6. Stage override check confirming the new soft R/Z reward values are identical at top level and in the active curriculum stage.
7. Environment-factory check confirming all new reward parameters are passed to `TscRzipEnv`.
8. Synthetic reward-direction checks:
   - decreasing R/Z distance produces positive soft progress;
   - outward R/Z velocity produces a larger penalty;
   - near-target velocity produces a braking penalty.
9. Checkpoint compatibility check:
   - cost dimension remains five;
   - the new R/Z velocity auxiliary changes existing R/Z costs without adding output heads.
10. Adaptive-alpha checks confirming at most four candidates after boundary expansion, interior refinement and rejection contraction.
11. Lightweight transaction test:
   - rank-1 fixed candidate fails the hard-target velocity gate;
   - rank 2 is then evaluated and accepted;
   - the rank-1 actor does not remain loaded;
   - normal fallback case uses eight synthetic scenario episodes, while rank-1 success would use seven on the first transaction and five after baseline caching.
12. Low-frequency audit test:
   - the third prospective accepted update triggers the five additional audit scenarios;
   - audit details are attached to the accepted cache;
   - online fixed-plus-hard aggregate remains the comparable public best score.
13. Atomic checkpoint implementation review.
14. Immediate-stop launcher review: SIGKILL is used and no final save is promised.

Synthetic test output:

```text
config linkage: PASS
soft reward directions: PASS
checkpoint-compatible velocity cost: PASS
four-candidate adaptive bracket: PASS
light transaction fallback: PASS
low-frequency seven-scenario audit: PASS
ALL TRAIN-FIRST SYNTHETIC TESTS PASS
```

Limitations:

- no real B99.9 checkpoint was loaded here;
- no observation/action tensor compatibility was tested against the user’s server checkpoint file;
- no gotsc episode was executed;
- no Ray scheduling or 192-worker integration test was run;
- reward magnitudes must be judged from the first real rollout logs and may require adjustment if they dominate or are negligible.
