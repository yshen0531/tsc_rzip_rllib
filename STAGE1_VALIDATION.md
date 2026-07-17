# Validation performed before release

The package was checked without running the proprietary/local TSC executable.

Completed checks:

- Python `py_compile` and `compileall` for all shipped Python files;
- JSON parsing for all shipped configurations;
- Bash `bash -n` for all run/stop/resume scripts;
- synthetic exact-recovery test for the response-tensor fitter;
- synthetic SVD mode generation;
- synthetic 100 ms reachable-set linear programs;
- constrained optimizer test with per-step ±3 A limits;
- configuration path and coil-order checks;
- clean archive extraction and repeated validation from the extracted archive.

Not performed here:

- actual `gotsc` execution;
- 192-worker Ray/TSC integration;
- server-specific Intel/NetCDF/HDF5 library loading;
- empirical wall-time measurement.

The first real run should therefore begin with the supplied default configuration and be monitored for early worker or filesystem errors. Completed experiment files are resumable after an immediate hard stop.
