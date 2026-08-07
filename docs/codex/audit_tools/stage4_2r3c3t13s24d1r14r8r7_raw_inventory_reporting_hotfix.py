#!/usr/bin/env python3
"""Reporting-only R8R7 independent raw-inventory digest compatibility hotfix."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r7_independent_forensics as independent,
)


def primary_compatible_inventory(path: Path) -> dict[str, Any]:
    """Independently reproduce the frozen primary name/NUL/size/NUL/hash digest."""

    digest = hashlib.sha256()
    rows = []
    for value in sorted(path.glob("*.json.gz"), key=lambda item: item.name):
        size = value.stat().st_size
        sha = independent._sha(value)
        digest.update(f"{value.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": value.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def main() -> None:
    independent._inventory = primary_compatible_inventory
    independent.main()


if __name__ == "__main__":
    main()
