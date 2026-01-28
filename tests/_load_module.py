from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _ensure_package(pkg_name: str) -> None:
    if pkg_name in sys.modules:
        return
    pkg = ModuleType(pkg_name)
    pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules[pkg_name] = pkg


def load_module(dotted_name: str, rel_path: str) -> ModuleType:
    """Load a module from a file path while supporting relative imports.

    We register parent packages in sys.modules so modules like
    `custom_components.beestat.api` can resolve `from .const import ...`.
    """
    parts = dotted_name.split(".")
    for i in range(1, len(parts)):
        _ensure_package(".".join(parts[:i]))

    root = Path(__file__).resolve().parents[1]
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module
