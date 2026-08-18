#!/usr/bin/env python3
"""Fail-closed package verifier for the frozen E1 exploration identity.

The verifier is deliberately zero-plant.  It authenticates an externally
named manifest and checksum file before parsing either, verifies the complete
declared payload, checks the local Python import closure, and loads the frozen
stage/evidence with every runner entry point instrumented to fail on use.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable, Mapping
from unittest import mock


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4e1-package-verification-v1"
PACKAGE_IDENTITY = "rgeo-zgeo-1ms-nr2r2c2aa4e1-single-successor-exploration-v1"
MANIFEST_SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4e1-package-manifest-v1"
RUNTIME_REVISION = "145ab1f77c20c8a324274d39be38bbfdf3dc4009"
STAGE_CONFIG_SHA256 = "f218774252ce044cefd067754f301a87028be114bd73fdf320788ea82fbaedd3"

MANIFEST_PATH = "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_package_manifest.json"
CHECKSUM_PATH = "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_package_sha256sums.txt"
STAGE_CONFIG_PATH = "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_single_successor_exploration.json"
VERIFIER_PATH = "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_verify_package.py"
VERIFIER_LAUNCHER_PATH = "run_rgeo_zgeo_1ms_nr2r2c2aa4e1_verify_package.sh"
FOCUSED_TEST_PATH = "tests/test_rgeo_zgeo_1ms_nr2r2c2aa4e1_exploration.py"

RUNTIME_ENTRYPOINT_FILES = (
    "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_exploration.py",
    "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_independent.py",
)
LEGACY_RUNTIME_FILES = (
    "scripts/rgeo_zgeo_1ms_nr1_qualification.py",
    "scripts/rgeo_zgeo_1ms_nr1_independent.py",
    "scripts/rgeo_zgeo_1ms_nr2r2c1a_source_replay.py",
    "scripts/rgeo_zgeo_1ms_nr2r2c2a_search.py",
    "scripts/rgeo_zgeo_1ms_nr2r2c2aa1_authority.py",
)
TSC_PACKAGE_RUNTIME_FILES = (
    "tsc_rzip_rllib/__init__.py",
    "tsc_rzip_rllib/control/__init__.py",
    "tsc_rzip_rllib/control/causal_observer.py",
    "tsc_rzip_rllib/control/quantized_actuator.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_contract.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_nr1.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_nr2_spec.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_1ms_contract.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_1ms_nr1.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_1ms_nr2_spec.py",
    "tsc_rzip_rllib/control/rgeo_zgeo_1ms_nr2_models.py",
    "tsc_rzip_rllib/control/transition_tube.py",
    "tsc_rzip_rllib/core/__init__.py",
    "tsc_rzip_rllib/core/coil_order.py",
    "tsc_rzip_rllib/core/gfile.py",
    "tsc_rzip_rllib/core/inputa.py",
    "tsc_rzip_rllib/core/runner.py",
)
STAGE_AND_EVIDENCE_FILES = (
    "run_rgeo_zgeo_1ms_nr2r2c2aa4e1.sh",
    STAGE_CONFIG_PATH,
    "docs/codex/reports/RGEO_ZGEO_1MS_NR2R2C2AA4E1_SINGLE_SUCCESSOR_EXPLORATION_DESIGN.md",
    "configs/rgeo_zgeo_1ms_nr1_safety_effect.json",
    "configs/rgeo_zgeo_1ms_nr2r2c2aa3_p03_cumulative_level2.json",
    "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/result.json",
    "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/independent_audit.json",
    "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/p03_cumulative_level2_r0.json",
    "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/p03_cumulative_level2_r1.json",
    "configs/rgeo_zgeo_1ms_nr2r2c2aa4_p03_level2_dwell_hold.json",
    "docs/codex/reports/RGEO_ZGEO_1MS_NR2R2C2AA4_P03_LEVEL2_DWELL_HOLD_DESIGN.md",
    "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa4_support_20260814_49faa8b9/result.json",
)
PACKAGE_TOOL_REVISION_FILES = frozenset(
    (VERIFIER_PATH, VERIFIER_LAUNCHER_PATH, FOCUSED_TEST_PATH)
)
EXPECTED_PAYLOAD_FILES = tuple(sorted({
    *RUNTIME_ENTRYPOINT_FILES,
    *LEGACY_RUNTIME_FILES,
    *TSC_PACKAGE_RUNTIME_FILES,
    *STAGE_AND_EVIDENCE_FILES,
    VERIFIER_PATH,
    VERIFIER_LAUNCHER_PATH,
    FOCUSED_TEST_PATH,
}))
EXPECTED_RUNTIME_PYTHON_FILES = frozenset(
    (*RUNTIME_ENTRYPOINT_FILES, *LEGACY_RUNTIME_FILES, *TSC_PACKAGE_RUNTIME_FILES)
)
EXPECTED_CHECKSUM_FILES = (MANIFEST_PATH, *EXPECTED_PAYLOAD_FILES)

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_CHECKSUM_LINE = re.compile(r"([0-9a-f]{64})  ([^\r\n]+)\Z")


class PackageVerificationError(RuntimeError):
    """The package identity or standalone closure is invalid."""

    phase = "package_validation"


class ExternalIdentityError(PackageVerificationError):
    """An externally supplied bootstrap identity does not authenticate."""

    phase = "external_identity"


class RunnerInvocationError(PackageVerificationError):
    """Stage loading attempted to cross the verifier's zero-plant boundary."""

    def __init__(self, message: str, counters: Mapping[str, int]) -> None:
        super().__init__(message)
        self.runner_counters = dict(counters)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_oid(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _strict_json_bytes(data: bytes, label: str) -> Any:
    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in rows:
            if key in result:
                raise PackageVerificationError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise PackageVerificationError(f"non-finite JSON constant in {label}: {value}")

    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageVerificationError(f"invalid UTF-8 JSON in {label}: {exc}") from exc


def _validate_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PackageVerificationError(f"{label} is not a non-empty path string")
    if "\\" in value or value.startswith("/"):
        raise PackageVerificationError(f"{label} is not a canonical POSIX relative path: {value}")
    parsed = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in parsed.parts) or parsed.as_posix() != value:
        raise PackageVerificationError(f"{label} is not canonical: {value}")
    return value


def _checked_regular_file(root: Path, relative: str, label: str) -> Path:
    relative = _validate_relative_path(relative, label)
    root = root.absolute()
    if not root.is_dir() or root.is_symlink():
        raise PackageVerificationError(f"repository root is missing, non-directory, or symlinked: {root}")
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise PackageVerificationError(f"{label} contains a symlink component: {relative}")
    if not current.is_file():
        raise PackageVerificationError(f"{label} is missing or not a regular file: {relative}")
    resolved_root = root.resolve(strict=True)
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise PackageVerificationError(f"{label} leaves repository root: {relative}")
    return current


def _expected_role(path: str) -> str:
    if path == VERIFIER_PATH:
        return "package_verifier"
    if path == VERIFIER_LAUNCHER_PATH:
        return "package_verifier_launcher"
    if path == FOCUSED_TEST_PATH:
        return "package_focused_test"
    if path == RUNTIME_ENTRYPOINT_FILES[0]:
        return "stage_primary_entrypoint"
    if path == RUNTIME_ENTRYPOINT_FILES[1]:
        return "stage_independent_entrypoint"
    if path in LEGACY_RUNTIME_FILES or path in TSC_PACKAGE_RUNTIME_FILES:
        return "runtime_import_closure"
    if path == STAGE_CONFIG_PATH:
        return "stage_config"
    if path.endswith("SINGLE_SUCCESSOR_EXPLORATION_DESIGN.md"):
        return "stage_design"
    if path == "run_rgeo_zgeo_1ms_nr2r2c2aa4e1.sh":
        return "stage_launcher"
    return "frozen_stage_evidence"


def _expected_source_revision(path: str, package_tool_revision: str) -> str:
    return package_tool_revision if path in PACKAGE_TOOL_REVISION_FILES else RUNTIME_REVISION


def _parse_checksums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackageVerificationError(f"checksum file is not UTF-8: {exc}") from exc
    if "\r" in text or not text.endswith("\n"):
        raise PackageVerificationError("checksum file must use LF and end with one newline")
    rows: dict[str, str] = {}
    order: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = _CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise PackageVerificationError(f"invalid checksum line {number}")
        digest, path = match.groups()
        path = _validate_relative_path(path, f"checksum line {number}")
        if path in rows:
            raise PackageVerificationError(f"duplicate checksum path: {path}")
        rows[path] = digest
        order.append(path)
    if tuple(order) != EXPECTED_CHECKSUM_FILES:
        raise PackageVerificationError("checksum fileset/order differs from frozen 40-entry contract")
    if CHECKSUM_PATH in rows:
        raise PackageVerificationError("checksum file must not contain itself")
    return rows


def _validate_manifest(
    manifest: Any, package_tool_revision: str
) -> list[dict[str, Any]]:
    expected_keys = {
        "schema_version",
        "package_identity",
        "runtime_revision",
        "package_tool_revision",
        "stage_config_path",
        "stage_config_sha256",
        "manifest_path",
        "checksum_path",
        "payload_file_count",
        "checksum_entry_count",
        "checksum_self_included",
        "zero_plant_package_verification",
        "files",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise PackageVerificationError("manifest top-level schema keys differ")
    exact = {
        "schema_version": MANIFEST_SCHEMA,
        "package_identity": PACKAGE_IDENTITY,
        "runtime_revision": RUNTIME_REVISION,
        "package_tool_revision": package_tool_revision,
        "stage_config_path": STAGE_CONFIG_PATH,
        "stage_config_sha256": STAGE_CONFIG_SHA256,
        "manifest_path": MANIFEST_PATH,
        "checksum_path": CHECKSUM_PATH,
        "payload_file_count": len(EXPECTED_PAYLOAD_FILES),
        "checksum_entry_count": len(EXPECTED_CHECKSUM_FILES),
        "checksum_self_included": False,
        "zero_plant_package_verification": True,
    }
    for key, value in exact.items():
        if manifest.get(key) != value:
            raise PackageVerificationError(f"manifest identity mismatch: {key}")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(EXPECTED_PAYLOAD_FILES):
        raise PackageVerificationError("manifest payload count mismatch")
    expected_entry_keys = {
        "path", "role", "source_revision", "git_blob_oid", "size_bytes", "sha256"
    }
    paths: list[str] = []
    for index, row in enumerate(files):
        if not isinstance(row, dict) or set(row) != expected_entry_keys:
            raise PackageVerificationError(f"manifest file entry schema mismatch: {index}")
        path = _validate_relative_path(row.get("path"), f"manifest file {index}")
        if row.get("role") != _expected_role(path):
            raise PackageVerificationError(f"manifest role mismatch: {path}")
        if row.get("source_revision") != _expected_source_revision(path, package_tool_revision):
            raise PackageVerificationError(f"manifest source revision mismatch: {path}")
        if not isinstance(row.get("git_blob_oid"), str) or _HEX40.fullmatch(
            row["git_blob_oid"]
        ) is None:
            raise PackageVerificationError(f"manifest Git blob OID is invalid: {path}")
        if (
            not isinstance(row.get("size_bytes"), int)
            or isinstance(row.get("size_bytes"), bool)
            or row["size_bytes"] < 0
        ):
            raise PackageVerificationError(f"manifest size is invalid: {path}")
        if not isinstance(row.get("sha256"), str) or _HEX64.fullmatch(row["sha256"]) is None:
            raise PackageVerificationError(f"manifest SHA-256 is invalid: {path}")
        paths.append(path)
    if tuple(paths) != EXPECTED_PAYLOAD_FILES or len(paths) != len(set(paths)):
        raise PackageVerificationError("manifest fileset/order differs from frozen payload")
    return files


def _module_name_for_file(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.name == "__init__.py":
        return ".".join(pure.parent.parts)
    return ".".join((*pure.parent.parts, pure.stem))


def _module_file(module: str) -> str:
    file_path = module.replace(".", "/") + ".py"
    init_path = module.replace(".", "/") + "/__init__.py"
    if file_path in EXPECTED_RUNTIME_PYTHON_FILES:
        return file_path
    if init_path in EXPECTED_RUNTIME_PYTHON_FILES:
        return init_path
    if module == "scripts" or module.startswith("scripts.") or module == "tsc_rzip_rllib" or module.startswith("tsc_rzip_rllib."):
        raise PackageVerificationError(f"undeclared or missing local import: {module}")
    return ""


def _implicit_package_files(module: str) -> set[str]:
    rows: set[str] = set()
    parts = module.split(".")
    for end in range(1, len(parts)):
        candidate = "/".join(parts[:end]) + "/__init__.py"
        if candidate in EXPECTED_RUNTIME_PYTHON_FILES:
            rows.add(candidate)
    return rows


def _relative_import_module(current_file: str, node: ast.ImportFrom) -> str:
    module_name = _module_name_for_file(current_file)
    if current_file.endswith("/__init__.py"):
        package_parts = module_name.split(".")
    else:
        package_parts = module_name.split(".")[:-1]
    up = node.level - 1
    if up > len(package_parts):
        raise PackageVerificationError(f"relative import leaves package: {current_file}")
    base = package_parts[: len(package_parts) - up]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _verify_import_closure(root: Path) -> tuple[list[str], list[str]]:
    adjacency: dict[str, set[str]] = {}
    for relative in sorted(EXPECTED_RUNTIME_PYTHON_FILES):
        path = _checked_regular_file(root, relative, "runtime Python source")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise PackageVerificationError(f"Python parse failed for {relative}: {exc}") from exc
        imports: set[str] = set()
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(
                    _relative_import_module(relative, node) if node.level else (node.module or "")
                )
            for module in modules:
                if not module:
                    continue
                target = _module_file(module)
                if target:
                    imports.add(target)
                    imports.update(_implicit_package_files(module))
        adjacency[relative] = imports

    reached: set[str] = set()
    stack = list(RUNTIME_ENTRYPOINT_FILES)
    while stack:
        current = stack.pop()
        if current in reached:
            continue
        reached.add(current)
        stack.extend(sorted(adjacency[current] - reached))
    if reached != EXPECTED_RUNTIME_PYTHON_FILES:
        missing = sorted(EXPECTED_RUNTIME_PYTHON_FILES - reached)
        extra = sorted(reached - EXPECTED_RUNTIME_PYTHON_FILES)
        raise PackageVerificationError(
            f"runtime import closure mismatch; unreachable={missing}; extra={extra}"
        )
    edges = sorted(f"{source}->{target}" for source, targets in adjacency.items() for target in targets)
    return sorted(reached), edges


def _import_runtime_modules(root: Path) -> list[str]:
    root_string = str(root.resolve(strict=True))
    if root_string not in sys.path:
        sys.path.insert(0, root_string)
    sys.dont_write_bytecode = True
    imported: list[str] = []
    for relative in sorted(EXPECTED_RUNTIME_PYTHON_FILES):
        module_name = _module_name_for_file(relative)
        module = importlib.import_module(module_name)
        module_path = Path(getattr(module, "__file__", "")).resolve(strict=True)
        expected = (root / relative).resolve(strict=True)
        if module_path != expected:
            raise PackageVerificationError(
                f"module imported from undeclared source tree: {module_name}: {module_path}"
            )
        imported.append(module_name)
    return imported


def _load_stage_without_plant(
    root: Path, *, require_runtime_paths: bool
) -> tuple[dict[str, int], dict[str, Any]]:
    runner_module = importlib.import_module("tsc_rzip_rllib.core.runner")
    primary = importlib.import_module(
        "scripts.rgeo_zgeo_1ms_nr2r2c2aa4e1_exploration"
    )
    independent = importlib.import_module(
        "scripts.rgeo_zgeo_1ms_nr2r2c2aa4e1_independent"
    )
    counters = {"reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0}

    def blocked(counter: str):
        def call(*_args: Any, **_kwargs: Any) -> Any:
            counters[counter] += 1
            raise RunnerInvocationError(
                f"zero-plant verifier reached runner method: {counter}", counters
            )

        return call

    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(runner_module.TSCStepRunner, "reset", blocked("reset_calls")))
        for name in ("step_current_a", "step_delta_current_a", "step", "step_delta"):
            stack.enter_context(
                mock.patch.object(runner_module.TSCStepRunner, name, blocked("advance_attempts"))
            )
        stack.enter_context(
            mock.patch.object(
                runner_module.TSCStepRunner, "_run_tsc", blocked("plant_advance_gotsc_calls")
            )
        )
        stack.enter_context(
            mock.patch.object(
                primary.CountingTSCStepRunner,
                "_run_tsc",
                blocked("plant_advance_gotsc_calls"),
            )
        )
        if not require_runtime_paths:
            # TSCConfig.validate also enforces all non-path schema/current rules.
            # In a local empty-package simulation only, make exactly the three
            # hash-bound server runtime paths appear present while retaining
            # every other Path.exists result.  No external path is opened.
            base = _strict_json_bytes(
                (root / "configs/rgeo_zgeo_1ms_nr1_safety_effect.json").read_bytes(),
                "base TSC config",
            )
            allowed = {
                str(Path(base["tsc"]["executable"]).expanduser()),
                str(Path(base["tsc"]["fortran_dir"]).expanduser()),
                str(Path(base["simulation_root"]).expanduser()),
            }
            original_exists = Path.exists

            def frozen_runtime_exists(path: Path) -> bool:
                return str(path) in allowed or original_exists(path)

            stack.enter_context(mock.patch.object(Path, "exists", frozen_runtime_exists))
        stage, cfg, evidence = primary.load(root / STAGE_CONFIG_PATH)
    if any(counters.values()):
        raise PackageVerificationError(f"stage load touched the runner: {counters}")
    if primary.SCHEMA != PACKAGE_IDENTITY:
        raise PackageVerificationError("primary schema differs from package identity")
    if independent.STAGE_SHA256 != STAGE_CONFIG_SHA256:
        raise PackageVerificationError("independent stage hash constant mismatch")
    if stage.get("schema_version") != PACKAGE_IDENTITY or set(evidence) != set(
        stage.get("evidence", {})
    ):
        raise PackageVerificationError("stage/evidence load returned an unexpected identity")
    details = {
        "stage_schema_version": stage["schema_version"],
        "evidence_keys": sorted(evidence),
        "dt_ms": cfg.dt_ms,
        "start_folder": cfg.start_folder,
        "project_root": str(cfg.project_root),
        "simulation_root": str(cfg.simulation_root),
        "executable": str(cfg.executable),
        "tsc_dir": str(cfg.tsc_dir),
        "library_path": cfg.library_path,
    }
    return counters, details


def _verify_runtime_paths(details: Mapping[str, Any]) -> list[str]:
    checked: list[str] = []
    directories = (
        Path(str(details["project_root"])),
        Path(str(details["simulation_root"])),
        Path(str(details["tsc_dir"])),
        Path(str(details["simulation_root"])) / str(details["start_folder"]),
    )
    for path in directories:
        if not path.is_dir():
            raise PackageVerificationError(f"required server runtime directory is missing: {path}")
        checked.append(str(path))
    executable = Path(str(details["executable"]))
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise PackageVerificationError(f"required gotsc executable is missing/non-executable: {executable}")
    checked.append(str(executable))
    source = Path(str(details["simulation_root"])) / str(details["start_folder"])
    for name in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina"):
        path = source / name
        if not path.is_file():
            raise PackageVerificationError(f"required 1100 ms source artifact is missing: {path}")
        checked.append(str(path))
    for raw in str(details["library_path"]).split(":"):
        if not raw:
            continue
        path = Path(raw)
        if not path.is_dir():
            raise PackageVerificationError(f"required TSC library directory is missing: {path}")
        checked.append(str(path))
    return checked


def verify_package(
    *,
    repo_root: Path,
    expected_manifest_sha256: str,
    expected_checksum_sha256: str,
    expected_package_tool_revision: str,
    require_runtime_paths: bool,
) -> dict[str, Any]:
    if _HEX64.fullmatch(expected_manifest_sha256) is None:
        raise ExternalIdentityError("external expected manifest SHA-256 is invalid")
    if _HEX64.fullmatch(expected_checksum_sha256) is None:
        raise ExternalIdentityError("external expected checksum SHA-256 is invalid")
    if _HEX40.fullmatch(expected_package_tool_revision) is None:
        raise ExternalIdentityError("external package-tool revision is invalid")

    root = repo_root.absolute()
    manifest_path = _checked_regular_file(root, MANIFEST_PATH, "manifest")
    checksum_path = _checked_regular_file(root, CHECKSUM_PATH, "checksum file")
    actual_manifest_sha256 = sha256(manifest_path)
    actual_checksum_sha256 = sha256(checksum_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise ExternalIdentityError("external manifest SHA-256 mismatch")
    if actual_checksum_sha256 != expected_checksum_sha256:
        raise ExternalIdentityError("external checksum SHA-256 mismatch")

    # Only after both externally supplied identities match may either file be parsed.
    manifest = _strict_json_bytes(manifest_path.read_bytes(), MANIFEST_PATH)
    manifest_rows = _validate_manifest(manifest, expected_package_tool_revision)
    checksums = _parse_checksums(checksum_path.read_bytes())
    if checksums[MANIFEST_PATH] != actual_manifest_sha256:
        raise PackageVerificationError("checksum file does not authenticate the manifest")

    by_path = {row["path"]: row for row in manifest_rows}
    for relative in EXPECTED_PAYLOAD_FILES:
        path = _checked_regular_file(root, relative, "payload")
        row = by_path[relative]
        actual_size = path.stat().st_size
        actual_sha = sha256(path)
        actual_blob = git_blob_oid(path)
        if actual_size != row["size_bytes"]:
            raise PackageVerificationError(f"payload size mismatch: {relative}")
        if actual_sha != row["sha256"] or checksums[relative] != actual_sha:
            raise PackageVerificationError(f"payload SHA-256 mismatch: {relative}")
        if actual_blob != row["git_blob_oid"]:
            raise PackageVerificationError(f"payload Git blob OID mismatch: {relative}")

    json_files = [MANIFEST_PATH] + [
        path for path in EXPECTED_PAYLOAD_FILES if path.endswith(".json")
    ]
    for relative in json_files:
        _strict_json_bytes(_checked_regular_file(root, relative, "JSON payload").read_bytes(), relative)

    python_files = [path for path in EXPECTED_PAYLOAD_FILES if path.endswith(".py")]
    for relative in python_files:
        source = _checked_regular_file(root, relative, "Python payload").read_bytes()
        try:
            compile(source, relative, "exec")
        except (SyntaxError, ValueError) as exc:
            raise PackageVerificationError(f"Python compile failed: {relative}: {exc}") from exc

    reached, import_edges = _verify_import_closure(root)
    imported_modules = _import_runtime_modules(root)
    third_party_versions = {
        name: str(getattr(importlib.import_module(name), "__version__", "unknown"))
        for name in ("numpy", "pandas", "torch")
    }
    counters, runtime_details = _load_stage_without_plant(
        root, require_runtime_paths=require_runtime_paths
    )
    runtime_paths = _verify_runtime_paths(runtime_details) if require_runtime_paths else []
    return {
        "schema_version": SCHEMA,
        "package_identity": PACKAGE_IDENTITY,
        "passed": True,
        "route": "ONE_MS_NR2R2C2AA4E1_PACKAGE_VERIFICATION_PASS_ZERO_TSC",
        "failure_phase": None,
        "failures": [],
        "runtime_revision": RUNTIME_REVISION,
        "package_tool_revision": expected_package_tool_revision,
        "manifest_path": MANIFEST_PATH,
        "manifest_sha256": actual_manifest_sha256,
        "checksum_path": CHECKSUM_PATH,
        "checksum_sha256": actual_checksum_sha256,
        "payload_files_verified": len(EXPECTED_PAYLOAD_FILES),
        "checksum_entries_verified": len(EXPECTED_CHECKSUM_FILES),
        "json_files_parsed": len(json_files),
        "python_files_compiled": len(python_files),
        "runtime_import_files_reached": len(reached),
        "runtime_import_edges": len(import_edges),
        "imported_modules": imported_modules,
        "third_party_versions": third_party_versions,
        "stage_config_sha256": STAGE_CONFIG_SHA256,
        "stage_evidence_keys": runtime_details["evidence_keys"],
        "runtime_paths_required": require_runtime_paths,
        "runtime_paths_checked": runtime_paths,
        **counters,
        "new_tsc_or_plant_advances": 0,
        "claim_boundary": (
            "package/import/stage-evidence verification only; zero reset, plant advance, "
            "gotsc, controller, model, hold, recovery, or qualification"
        ),
    }


def _failure_result(
    *,
    phase: str,
    error: Exception,
    expected_manifest_sha256: str,
    expected_checksum_sha256: str,
    expected_package_tool_revision: str,
) -> dict[str, Any]:
    counters = getattr(
        error,
        "runner_counters",
        {"reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0},
    )
    return {
        "schema_version": SCHEMA,
        "package_identity": PACKAGE_IDENTITY,
        "passed": False,
        "route": "ONE_MS_NR2R2C2AA4E1_PACKAGE_VERIFICATION_FAIL_NO_TSC",
        "failure_phase": phase,
        "failures": [f"{type(error).__name__}:{error}"],
        "runtime_revision": RUNTIME_REVISION,
        "package_tool_revision": expected_package_tool_revision,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_checksum_sha256": expected_checksum_sha256,
        "reset_calls": int(counters["reset_calls"]),
        "advance_attempts": int(counters["advance_attempts"]),
        "plant_advance_gotsc_calls": int(counters["plant_advance_gotsc_calls"]),
        "new_tsc_or_plant_advances": 0,
        "claim_boundary": "package verification failure; no TSC or plant action attempted",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-checksum-sha256", required=True)
    parser.add_argument("--expected-package-tool-revision", required=True)
    parser.add_argument("--require-runtime-paths", action="store_true")
    args = parser.parse_args(argv)
    phase = "external_identity"
    try:
        # The function authenticates both identity files before parsing them.
        result = verify_package(
            repo_root=args.repo_root,
            expected_manifest_sha256=args.expected_manifest_sha256,
            expected_checksum_sha256=args.expected_checksum_sha256,
            expected_package_tool_revision=args.expected_package_tool_revision,
            require_runtime_paths=args.require_runtime_paths,
        )
    except Exception as exc:  # fail closed with a machine-readable record
        result = _failure_result(
            phase=getattr(exc, "phase", phase),
            error=exc,
            expected_manifest_sha256=args.expected_manifest_sha256,
            expected_checksum_sha256=args.expected_checksum_sha256,
            expected_package_tool_revision=args.expected_package_tool_revision,
        )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
