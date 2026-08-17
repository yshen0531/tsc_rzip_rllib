# ID-2G1R1 compact model evidence

This directory retains the corrected ID-2G1R1 primary result, independent
raw-re-extraction/refit result and selected causal-TCN model artifact.

Source revision: `ebdb42a01e5ddcc49317df940cdec21abf698795`.

Hashes:

- `result.json`: `6d2389d7d7a5d86eea221cadd4fe386b6f95a734405496b36eab07a372856afa`
- `independent_audit.json`: `614b01bdc8b422bc1ced2472da1ccac3f5d9445ca8baed1c431f8a0dbc1ad83e`
- `selected_model.pt`: `14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`

The server-only allowed-causal dataset has canonical content digest
`bfb01c258160c55533ae9ec9fc2580c2f1a556c48df3e7067f80021e5ceaaf85`
and file hash
`8d1d8edbbef6021f5b140837bd6934aaa8ab8ad0e0f1989c174af6782bbc9d28`.
It was not downloaded and is forbidden as a repository fixture.

The earlier `7841a173` output is retained on the server as a reporting/
evaluator bug record: its action-blind recursive current accidentally used
the true future issued action.  It is not the final result.  The selected
TCN weights themselves were unchanged, but only this corrected `ebdb42a0`
result is evidence for the calibration route.

This is development selection only.  It is not calibrated uncertainty,
holdout, controller, tube, authority or closed-loop evidence.
