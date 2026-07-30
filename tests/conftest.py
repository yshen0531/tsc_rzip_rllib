"""Pytest portability shim for the Windows repository validation host."""
from __future__ import annotations

import sys
import types


if sys.platform == "win32":
    try:
        import resource as _resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource
