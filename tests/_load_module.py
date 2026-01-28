from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_module(name: str, rel_path: str) -> ModuleType:
    """Load a module directly from a file path (bypasses package __init__)."""
    root = Path(__file__).resolve().parents[1]
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
