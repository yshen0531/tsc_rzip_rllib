# B99.9 Validation Performed

Completed in the build environment:

- Python `py_compile` for all Python sources;
- JSON parsing for all configuration files;
- Bash syntax checking for all run scripts;
- synthetic learner test:
  - regular critic update leaves actor unchanged;
  - forced proposal executes exactly one actor update;
  - state interpolation is correct;
  - actor, optimizer and update count restore exactly;
- synthetic transaction state-machine test:
  - a verified `alpha=0.5` candidate is accepted;
  - a later non-improving proposal is rejected;
  - baseline actor remains unchanged after rejection.

Not performed here:

- real TSC/gotsc execution;
- Ray 192-worker integration run;
- real deterministic candidate evaluation.

Those require the user's server and TSC installation.
