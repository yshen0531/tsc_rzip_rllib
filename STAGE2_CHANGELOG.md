# Stage2 change log

- Default TSC runtime workspace moved to `/tmp/tsc_workspace`.
- Default TSC episode root moved to `/tmp/tsc_workspace/episode_runs`.
- Each candidate now removes its episode directory immediately.
- Ray actors are closed at the end of every generation so private runtime copies are deleted before actor termination.
- Fresh launch removes stale Stage2 temporary directories.
- CEM, SVD modes, objective, gates, population and confirmation logic are unchanged.
