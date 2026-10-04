"""Fingerprint of the code that produces a /api/prediction_series row.

The series cache (sbc.series_cache) stores this with every row and ignores
rows written by a different version, so changing the prediction engine
invalidates cached days automatically instead of serving stale overlays.

What is hashed (found statically, nothing is imported):
- sbc/engine.py (build_response, ANCHORS and the time helpers);
- chart_bp.prediction_series, which shapes the cached payload;
- transitively, every first-party module those import (module-level or
  inside functions, e.g. market_calendar -> muhurta -> kp_ephemeris).

Unrelated modules (DOCX export, KP intraday, forecast ledger...) are not in the
closure, so editing them leaves the cache alone.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHART_BP_FILE = ROOT / "sbc" / "api" / "blueprints" / "chart_bp.py"
ENGINE_MODULE = "sbc.engine"
PAYLOAD_FUNCTION = "prediction_series"
FIRST_PARTY = ("sbc",)
# Storage, not engine: changing how rows are cached must not invalidate them.
EXCLUDED_MODULES = {"sbc.series_cache", "sbc.engine_version"}

# Bump to force a rebuild without touching engine code (e.g. data-file fixes).
MANUAL_EPOCH = 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_file(module: str) -> Path | None:
    parts = module.split(".")
    candidate = ROOT.joinpath(*parts)
    if candidate.with_suffix(".py").is_file():
        return candidate.with_suffix(".py")
    if (candidate / "__init__.py").is_file():
        return candidate / "__init__.py"
    return None


def _resolve(module: str | None, level: int, current: str) -> str | None:
    """Absolute module name for an ImportFrom inside `current`."""
    if not level:
        return module
    base = current.split(".")
    is_pkg = (_module_file(current) or Path()).name == "__init__.py"
    base = base if is_pkg else base[:-1]
    base = base[: len(base) - (level - 1)] if level > 1 else base
    return ".".join([*base, module]) if module else ".".join(base)


def _first_party_imports(tree: ast.AST, current: str) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = _resolve(node.module, node.level, current)
            if not mod:
                continue
            for alias in node.names:  # `from pkg import submodule`
                sub = f"{mod}.{alias.name}"
                if sub.split(".")[0] in FIRST_PARTY and _module_file(sub):
                    found.add(sub)
            if mod.split(".")[0] in FIRST_PARTY:
                found.add(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FIRST_PARTY:
                    found.add(alias.name)
    return found


def _function_source(src: str, name: str) -> str:
    tree = ast.parse(src)
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return ast.get_source_segment(src, n) or ""
    raise LookupError(f"{name} not found")


def dependency_closure(read: Callable[[Path], str] = _read) -> tuple[str, list[Path]]:
    """(chart_bp payload-builder source, sorted module files in the closure)."""
    chart_src = read(CHART_BP_FILE)
    payload_src = _function_source(chart_src, PAYLOAD_FUNCTION)
    start = {ENGINE_MODULE} | _first_party_imports(ast.parse(payload_src), "sbc.api.blueprints.chart_bp")
    return payload_src, module_closure(start, read)


def module_closure(start: Iterable[str], read: Callable[[Path], str] = _read,
                   excluded: frozenset[str] = frozenset(EXCLUDED_MODULES)) -> list[Path]:
    """Sorted files of the first-party modules reachable from `start`."""
    files: dict[str, Path] = {}
    todo = list(start)
    while todo:
        mod = todo.pop()
        path = _module_file(mod)
        # Package __init__ files only re-export (sbc/__init__ imports nearly
        # every module); following them would make the closure the whole repo.
        if (path is None or path.name == "__init__.py" or mod in excluded
                or path in files.values()):
            continue
        files[mod] = path
        todo.extend(_first_party_imports(ast.parse(read(path)), mod) - set(files))
    return sorted(set(files.values()))


def module_version(module: str, read: Callable[[Path], str] = _read,
                   excluded: frozenset[str] = frozenset()) -> str:
    """Hash of `module` and every first-party module it imports.

    For stores keyed by something other than the prediction series (e.g. the
    fingerprint store versions rows by module_version("sbc.fingerprint")).
    """
    h = hashlib.sha256(f"module={module}\n".encode())
    for p in module_closure({module}, read, frozenset(excluded)):
        h.update(f"\n--- {p.relative_to(ROOT).as_posix()}\n".encode())
        h.update(read(p).encode())
    return h.hexdigest()[:12]


def compute_engine_version(read: Callable[[Path], str] = _read) -> str:
    slice_src, paths = dependency_closure(read)
    h = hashlib.sha256(f"epoch={MANUAL_EPOCH}\n".encode())
    h.update(slice_src.encode())
    for p in paths:
        h.update(f"\n--- {p.relative_to(ROOT).as_posix()}\n".encode())
        h.update(read(p).encode())
    return h.hexdigest()[:12]


@lru_cache(maxsize=1)
def engine_version() -> str:
    """Cached for the process: code changes need a restart to take effect anyway."""
    return compute_engine_version()
