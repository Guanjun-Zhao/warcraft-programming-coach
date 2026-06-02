"""
Per-version persistence under data/versionN/: state.json, code.cpp, history/*.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SAMPLES_PATH = ROOT_DIR / "data" / "samples.json"
APP_SETTINGS_PATH = ROOT_DIR / "data" / "app_settings.json"
DEFAULT_APP_MODEL = "deepseek-v4-flash"

_SAMPLES_FILE_CACHE: tuple[int, dict[str, Any]] | None = None
_VERSION_SAMPLES_CACHE: dict[str, tuple[int, list[dict[str, Any]]]] = {}
_LAST_HISTORY_IO_ERROR: str = ""


def load_app_settings() -> dict[str, str]:
    defaults = {"api_key": "", "model": DEFAULT_APP_MODEL}
    path = APP_SETTINGS_PATH
    if not path.is_file():
        return defaults
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return defaults
        raw = json.loads(text)
        if not isinstance(raw, dict):
            return defaults
        api_key = raw.get("api_key", "")
        model = raw.get("model", DEFAULT_APP_MODEL)
        return {
            "api_key": api_key if isinstance(api_key, str) else "",
            "model": model if isinstance(model, str) and model.strip() else DEFAULT_APP_MODEL,
        }
    except (json.JSONDecodeError, OSError):
        return defaults


def save_app_settings(settings: dict[str, str]) -> None:
    model = settings.get("model", DEFAULT_APP_MODEL)
    if not isinstance(model, str) or not model.strip():
        model = DEFAULT_APP_MODEL
    api_key = settings.get("api_key", "")
    if not isinstance(api_key, str):
        api_key = ""
    payload = {"api_key": api_key, "model": model.strip()}
    APP_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def version_dir(version_id: str) -> Path:
    return ROOT_DIR / "data" / version_id


def version_state_path(version_id: str) -> Path:
    return version_dir(version_id) / "state.json"


def version_code_path(version_id: str) -> Path:
    return version_dir(version_id) / "code.cpp"


def version_history_dir(version_id: str) -> Path:
    return version_dir(version_id) / "history"


def version_samples_path(version_id: str) -> Path:
    return version_dir(version_id) / "samples.json"


def history_filename(task_id: str) -> str:
    if task_id == "task_debug":
        return "debug.json"
    return f"{task_id}.json"


def _history_candidate_filenames(task_id: str) -> list[str]:
    primary = history_filename(task_id)
    names = [primary]
    # 兼容旧数据：Debug 历史可能曾写入 task_debug.json
    if task_id == "task_debug":
        names.append("task_debug.json")
    if "debug" in task_id.lower():
        names.extend([f"{task_id}.json", "debug.json", "task_debug.json"])
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def history_path(version_id: str, task_id: str) -> Path:
    return version_history_dir(version_id) / history_filename(task_id)


def load_version_state(version_id: str) -> dict[str, Any]:
    path = version_state_path(version_id)
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        raw = json.loads(text)
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_version_state(version_id: str, state: dict[str, Any]) -> None:
    path = version_state_path(version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ensure_tree_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("_tree", {"h2_expanded": {}, "h2_completed": {}})
    tree = state["_tree"]
    tree.setdefault("h2_expanded", {})
    tree.setdefault("h2_completed", {})
    return tree


def ensure_task_state(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    state.setdefault(task_id, {"completed": False})
    slot = state[task_id]
    slot.setdefault("completed", False)
    if task_id == "task_debug":
        slot.setdefault("current_sample_index", 0)
    return slot


def load_task_history(version_id: str, task_id: str) -> list[dict[str, Any]]:
    primary = history_path(version_id, task_id)
    history_dir = version_history_dir(version_id)
    for fname in _history_candidate_filenames(task_id):
        path = history_dir / fname
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                continue
            raw = json.loads(text)
            if not isinstance(raw, list):
                continue
            parsed = [
                m
                for m in raw
                if isinstance(m, dict)
                and m.get("role") in ("user", "assistant")
                and isinstance(m.get("content"), str)
            ]
            if parsed and path != primary:
                save_task_history(version_id, task_id, parsed)
            return parsed
        except (json.JSONDecodeError, OSError):
            continue
    return []


def save_task_history(
    version_id: str, task_id: str, messages: list[dict[str, Any]]
) -> None:
    global _LAST_HISTORY_IO_ERROR
    _LAST_HISTORY_IO_ERROR = ""
    path = history_path(version_id, task_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(messages, ensure_ascii=False, indent=2)
        path.write_text(payload, encoding="utf-8")
        verify = path.read_text(encoding="utf-8")
        verify_raw = json.loads(verify)
        if not isinstance(verify_raw, list):
            raise ValueError("history file is not a list")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _LAST_HISTORY_IO_ERROR = (
            f"history write failed: version={version_id}, task={task_id}, "
            f"path={path}, error={type(exc).__name__}: {exc}"
        )


def clear_task_history(version_id: str, task_id: str) -> None:
    history_dir = version_history_dir(version_id)
    for fname in _history_candidate_filenames(task_id):
        path = history_dir / fname
        if not path.is_file():
            continue
        try:
            path.unlink()
        except OSError:
            continue


def get_last_history_io_error() -> str:
    return _LAST_HISTORY_IO_ERROR


def clear_version_local_records(version_id: str) -> None:
    """Clear per-version checklist state and all chat history files."""
    save_version_state(version_id, {"_tree": {"h2_expanded": {}, "h2_completed": {}}})
    history_dir = version_history_dir(version_id)
    if not history_dir.is_dir():
        return
    for item in history_dir.glob("*.json"):
        if not item.is_file():
            continue
        try:
            item.unlink()
        except OSError:
            continue


def load_version_code(version_id: str) -> str:
    path = version_code_path(version_id)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def save_version_code(version_id: str, text: str) -> None:
    path = version_code_path(version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_program_output(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""
    return "\n".join(line.rstrip() for line in normalized.split("\n"))


_DEBUG_QUESTION_MARKERS = (
    "?",
    "？",
    "为什么",
    "为何",
    "怎么",
    "如何",
    "哪里",
    "请问",
    "帮我",
    "看一下",
    "看下",
    "解释",
    "分析",
    "报错",
    "错误",
    "崩溃",
    "未响应",
)
_DEBUG_CODE_MARKERS = (
    "#include",
    "int main",
    "using namespace",
    "std::",
    "cout",
    "cin",
    "printf(",
    "scanf(",
    "->",
    "::",
)


def _contains_question_intent(text: str) -> bool:
    lower = text.lower()
    return any(marker in text or marker in lower for marker in _DEBUG_QUESTION_MARKERS)


def _line_is_code_like(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    lower = s.lower()
    if s.startswith("```") or s.startswith("//"):
        return True
    if any(marker in s or marker in lower for marker in _DEBUG_CODE_MARKERS):
        return True
    if ("{" in s or "}" in s) and len(s) <= 200:
        return True
    if re.match(r"^(int|long|void|char|bool|double|float|string)\s+\w+\s*\(", s):
        return True
    if s.endswith(";") and not re.search(r"\d", s):
        return True
    return False


def _contains_code_intent(text: str) -> bool:
    lines = normalize_program_output(text).split("\n")
    code_like = sum(1 for line in lines if _line_is_code_like(line))
    return code_like >= 2


def _looks_like_output_text(text: str) -> bool:
    normalized = normalize_program_output(text)
    if not normalized:
        return False
    lines = normalized.split("\n")
    if len(lines) > 80:
        return False
    code_like = sum(1 for line in lines if _line_is_code_like(line))
    if code_like >= max(2, len(lines) // 3):
        return False
    return True


def extract_likely_program_output(text: str) -> str:
    """
    从 Debug 输入中尽量提取“像程序输出”的内容：
    - 优先取“输出/结果/output/result”提示词之后的文本；
    - 否则剔除明显代码行与提问句，保留可比对片段。
    """
    normalized = normalize_program_output(text)
    if not normalized:
        return ""
    lines = normalized.split("\n")
    markers = ("输出", "结果", "output", "result")
    start = -1
    for i, line in enumerate(lines):
        low = line.strip().lower()
        if any(m in line or m in low for m in markers):
            if ":" in line or "：" in line:
                suffix = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                if suffix and not _line_is_code_like(suffix):
                    return normalize_program_output(suffix + "\n" + "\n".join(lines[i + 1 :]))
            start = i + 1
            break
    if start != -1:
        tail = normalize_program_output("\n".join(lines[start:]))
        if _looks_like_output_text(tail):
            return tail

    kept: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _line_is_code_like(s):
            continue
        if _contains_question_intent(s):
            continue
        kept.append(s)
    candidate = normalize_program_output("\n".join(kept))
    if _looks_like_output_text(candidate):
        return candidate
    return ""


def classify_debug_user_input(text: str) -> str:
    """
    返回: question | outputSubmission | mixedOrCode
    """
    normalized = normalize_program_output(text)
    if not normalized:
        return "question"
    has_question = _contains_question_intent(normalized)
    has_code = _contains_code_intent(normalized)
    extracted = extract_likely_program_output(normalized)
    if has_question and not extracted:
        return "question"
    if has_code:
        return "mixedOrCode"
    if extracted or _looks_like_output_text(normalized):
        return "outputSubmission"
    if has_question:
        return "question"
    return "outputSubmission"


def load_samples() -> dict[str, Any]:
    global _SAMPLES_FILE_CACHE
    if not SAMPLES_PATH.is_file():
        _SAMPLES_FILE_CACHE = None
        return {}
    try:
        mtime_ns = SAMPLES_PATH.stat().st_mtime_ns
        if _SAMPLES_FILE_CACHE is not None and _SAMPLES_FILE_CACHE[0] == mtime_ns:
            return _SAMPLES_FILE_CACHE[1]
        text = SAMPLES_PATH.read_text(encoding="utf-8")
        if not text.strip():
            parsed: dict[str, Any] = {}
        else:
            parsed = json.loads(text)
        _SAMPLES_FILE_CACHE = (mtime_ns, parsed)
        return parsed
    except (json.JSONDecodeError, OSError):
        _SAMPLES_FILE_CACHE = None
        return {}


def load_version_samples(version_id: str) -> list[dict[str, Any]]:
    global _VERSION_SAMPLES_CACHE
    path = version_samples_path(version_id)
    if not path.is_file():
        _VERSION_SAMPLES_CACHE.pop(version_id, None)
        return []
    try:
        mtime_ns = path.stat().st_mtime_ns
        cached = _VERSION_SAMPLES_CACHE.get(version_id)
        if cached is not None and cached[0] == mtime_ns:
            return cached[1]
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            parsed: list[dict[str, Any]] = []
        else:
            raw = json.loads(text)
            if not isinstance(raw, list):
                parsed = []
            else:
                parsed = [x for x in raw if isinstance(x, dict)]
        _VERSION_SAMPLES_CACHE[version_id] = (mtime_ns, parsed)
        return parsed
    except (json.JSONDecodeError, OSError):
        _VERSION_SAMPLES_CACHE.pop(version_id, None)
        return []
