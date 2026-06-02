# -*- coding: utf-8 -*-
"""Load data/sections.json: planning leaf, H2 groups, coding leaves, debug task id."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SECTIONS_PATH = ROOT_DIR / "data" / "sections.json"

_SECTIONS_CACHE: tuple[int, dict[str, Any]] | None = None
_VERSION_SPEC_CACHE: dict[str, tuple[int, dict[str, Any]]] = {}


def _version_sections_path(version_id: str) -> Path:
    return ROOT_DIR / "data" / version_id / "sections.json"


def load_sections() -> dict[str, Any]:
    """Read sections.json; cache by file mtime (same pattern as samples)."""
    global _SECTIONS_CACHE
    if not SECTIONS_PATH.is_file():
        _SECTIONS_CACHE = None
        return {}
    try:
        mtime_ns = SECTIONS_PATH.stat().st_mtime_ns
        if _SECTIONS_CACHE is not None and _SECTIONS_CACHE[0] == mtime_ns:
            return _SECTIONS_CACHE[1]
        text = SECTIONS_PATH.read_text(encoding="utf-8")
        parsed: dict[str, Any] = json.loads(text) if text.strip() else {}
        _SECTIONS_CACHE = (mtime_ns, parsed)
        return parsed
    except (json.JSONDecodeError, OSError):
        _SECTIONS_CACHE = None
        return {}


def get_version_spec(version_id: str) -> dict[str, Any]:
    path = _version_sections_path(version_id)
    if path.is_file():
        global _VERSION_SPEC_CACHE
        try:
            mtime_ns = path.stat().st_mtime_ns
            cached = _VERSION_SPEC_CACHE.get(version_id)
            if cached is not None and cached[0] == mtime_ns:
                return cached[1]
            text = path.read_text(encoding="utf-8")
            parsed: dict[str, Any] = json.loads(text) if text.strip() else {}
            _VERSION_SPEC_CACHE[version_id] = (mtime_ns, parsed)
            return parsed
        except (json.JSONDecodeError, OSError):
            _VERSION_SPEC_CACHE.pop(version_id, None)
            return {}
    return load_sections().get(version_id) or {}


def ensure_tree_state(state: dict[str, Any]) -> dict[str, Any]:
    """Return _tree dict (h2_expanded, h2_completed) on a version state object."""
    state.setdefault("_tree", {"h2_expanded": {}, "h2_completed": {}})
    tree = state["_tree"]
    tree.setdefault("h2_expanded", {})
    tree.setdefault("h2_completed", {})
    return tree


def get_leaf_section(version_id: str, task_id: str) -> dict[str, Any] | None:
    """Return section dict for a leaf task_id, or None if unknown."""
    spec = get_version_spec(version_id)
    planning = spec.get("planning") or {}
    if planning.get("task_id") == task_id:
        return planning
    for g in spec.get("groups") or []:
        for sec in g.get("sections") or []:
            if sec.get("task_id") == task_id:
                return sec
    if spec.get("debug_task_id") == task_id:
        return {
            "task_id": task_id,
            "section_id": "debug",
            "title": "Debug",
            "description": "",
            "code": "",
            "skip_code_verify": True,
            "role": "debug",
        }
    return None


def progress_denominator(version_id: str) -> int:
    """All checkbox rows: planning + each H2 + each leaf + debug."""
    spec = get_version_spec(version_id)
    if not spec:
        return 1
    n = 0
    if spec.get("planning"):
        n += 1
    for g in spec.get("groups") or []:
        n += 1 + len(g.get("sections") or [])
    if spec.get("debug_task_id"):
        n += 1
    return max(n, 1)


def iter_coding_leaf_task_ids(version_id: str) -> list[str]:
    spec = get_version_spec(version_id)
    debug_tid = spec.get("debug_task_id")
    ids: list[str] = []
    for g in spec.get("groups") or []:
        for sec in g.get("sections") or []:
            tid = sec.get("task_id")
            if tid and tid != debug_tid:
                ids.append(str(tid))
    return ids


def all_coding_leaves_completed(state: dict[str, Any], version_id: str) -> bool:
    ids = iter_coding_leaf_task_ids(version_id)
    if not ids:
        return True
    for tid in ids:
        if not (state.get(tid) or {}).get("completed"):
            return False
    return True


def progress_numerator(state: dict[str, Any], version_id: str) -> int:
    spec = get_version_spec(version_id)
    if not spec:
        return 0
    tree = ensure_tree_state(state)
    h2_done = tree.get("h2_completed") or {}
    done = 0
    if spec.get("planning"):
        tid = spec["planning"]["task_id"]
        if (state.get(tid) or {}).get("completed"):
            done += 1
    for g in spec.get("groups") or []:
        h2_id = g.get("h2_id")
        if h2_id and h2_done.get(h2_id):
            done += 1
        for sec in g.get("sections") or []:
            tid = sec.get("task_id")
            if tid and (state.get(tid) or {}).get("completed"):
                done += 1
    dt = spec.get("debug_task_id")
    if dt and (state.get(dt) or {}).get("completed"):
        done += 1
    return done


def first_leaf_task_id(version_id: str) -> str | None:
    spec = get_version_spec(version_id)
    if spec.get("planning") and spec["planning"].get("task_id"):
        return spec["planning"]["task_id"]
    for g in spec.get("groups") or []:
        for sec in g.get("sections") or []:
            tid = sec.get("task_id")
            if tid:
                return tid
    return spec.get("debug_task_id")
