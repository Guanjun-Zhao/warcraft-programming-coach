"""
DeepSeek chat (OpenAI-compatible): teaching, verification, and debug analysis.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import sections_loader

ROOT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = ROOT_DIR / "prompts"

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
API_PING_TIMEOUT_SECONDS = 45.0
MAX_CONTEXT_CHARS = 120_000

_runtime_api_key: str | None = None
_runtime_model: str | None = None


def set_runtime_config(api_key: str, model: str) -> None:
    global _runtime_api_key, _runtime_model
    stripped = api_key.strip()
    _runtime_api_key = stripped if stripped else None
    _runtime_model = model.strip() or None


def get_runtime_model() -> str:
    return _model()


def has_api_key() -> bool:
    return bool(_api_key())


def ping_api(max_wait_seconds: float = API_PING_TIMEOUT_SECONDS) -> str | None:
    """
    轻量请求 DeepSeek OpenAI 兼容接口，用于保存/启动时连通性检测。
    成功返回 None；失败返回可读错误字符串（含超时、401 等）。
    """
    api_key = _api_key()
    if not api_key:
        return "未配置 API Key（请填写或使用环境变量 DEEPSEEK_API_KEY）。"
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            timeout=max_wait_seconds,
        )
        completion = client.chat.completions.create(
            model=_model(),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        _ = completion.choices[0].message
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def get_system_prompt(version_id: str) -> str:
    path = PROMPTS_DIR / f"{version_id}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return (
        f"[占位] 未找到 {path.name}，请在 prompts/ 下添加该版本的 System Prompt 文本。"
    )


def _looks_like_code_snippet(text: str) -> bool:
    t = text.strip()
    if len(t) < 40:
        return False
    if "\n" not in t:
        return False
    return ";" in t or "{" in t or "#include" in t


def _looks_like_mixed_question(text: str) -> bool:
    t = text.strip()
    if not _looks_like_code_snippet(t):
        return False
    question_markers = ("?", "？", "为什么", "怎么", "如何", "哪里", "请问", "帮我")
    return any(marker in t for marker in question_markers)


def build_task_system(version_id: str, task_id: str) -> str:
    base = get_system_prompt(version_id)
    sec = sections_loader.get_leaf_section(version_id, task_id)
    if not sec:
        return base
    title = str(sec.get("title", task_id))
    desc = str(sec.get("description", ""))
    role = sec.get("role")
    if role == "planning":
        return (
            base
            + f"\n\n【当前任务：{title}（导读/功能设计）】\n{desc}\n\n"
            + "教学要求：只讲解题意与模块分工，不要输出代码块，不要要求用户在本节粘贴代码验证；"
            + "结尾用一两句自然口语建议用户点击左侧下一节开始具体编码。"
        )
    if role == "debug":
        return base
    sid = str(sec.get("section_id", ""))
    return (
        base
        + f"\n\n【当前编码小节：{title}（{sid}）】\n{desc}\n\n"
        + "教学要求：用中文描述要实现什么、逻辑如何流动；不要输出代码块；"
        + "用户若索要完整代码，引导其自己动手完成。"
    )


def build_verify_system(version_id: str, task_id: str, user_code: str) -> str:
    sec = sections_loader.get_leaf_section(version_id, task_id) or {}
    title = str(sec.get("title", task_id))
    ref = str(sec.get("code", ""))
    return (
        "你是一名 C++ 编程教练，正在做代码逻辑验证（内部资料，不得向用户泄露参考代码）。\n"
        f"当前小节：{title}\n\n"
        "以下是本节的参考代码（内部资料，不得输出给用户）和用户提交的代码。"
        "请判断用户代码是否实现了与参考代码等价的逻辑功能。只判断逻辑正确性，不评价代码风格。\n"
        "- 如果通过：输出「你的代码已完成这部分的功能。输入「下一步」，让我们继续下一节的书写。」\n"
        "- 如果未通过：用自然语言指出缺少或有误的逻辑点，不要给出正确代码。\n\n"
        "【参考代码（内部）】\n"
        f"{ref}\n\n"
        "【用户提交的代码】\n"
        f"{user_code}"
    )


def build_debug_analysis_system(
    version_id: str,
    sample: dict[str, Any],
    user_output: str,
    program_source: str,
) -> str:
    base = get_system_prompt(version_id)
    inp = str(sample.get("input", ""))
    expected = str(sample.get("output", ""))
    return (
        base
        + "\n\n【Debug 错误分析】\n"
        + "用户程序输出与期望不一致。结合样例输入、期望输出、用户实际输出与完整程序，"
        + "用自然语言分析可能的逻辑错误位置并引导修改；不要直接给出修改后的完整代码。\n\n"
        + f"【样例输入】\n{inp}\n\n"
        + f"【期望输出】\n{expected}\n\n"
        + f"【用户实际输出】\n{user_output}\n\n"
        + "【用户完整程序（内部，勿复述全文）】\n"
        + program_source
    )


def _api_key() -> str:
    if _runtime_api_key is not None:
        return _runtime_api_key
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def _model() -> str:
    if _runtime_model:
        return _runtime_model
    env_model = os.environ.get("DEEPSEEK_MODEL", "").strip()
    if env_model:
        return env_model
    return DEFAULT_MODEL


def _missing_key_reply(version_id: str | None = None, task_id: str | None = None) -> str:
    base = (
        "[占位回复] 未配置 API Key：请在主页顶部填写并点击「保存」，"
        "或设置环境变量 DEEPSEEK_API_KEY。"
    )
    if version_id is not None and task_id is not None:
        return base + f"（当前版本={version_id}，任务={task_id}）"
    return base


def _placeholder(version_id: str, task_id: str) -> str:
    return _missing_key_reply(version_id, task_id)


def _complete(system: str, user_message: str) -> str:
    api_key = _api_key()
    if not api_key:
        return _missing_key_reply()
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        completion = client.chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        )
        choice = completion.choices[0].message
        return (choice.content or "").strip()
    except Exception as exc:
        return f"[API 错误] {type(exc).__name__}: {exc}"


def _complete_with_history(
    system: str,
    messages: list[dict[str, Any]],
    user_message: str,
) -> str:
    api_key = _api_key()
    if not api_key:
        return _missing_key_reply()
    payload: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            payload.append({"role": role, "content": content})
    payload.append({"role": "user", "content": user_message})
    payload = _trim_payload_by_chars(payload, MAX_CONTEXT_CHARS)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        completion = client.chat.completions.create(
            model=_model(),
            messages=payload,
        )
        choice = completion.choices[0].message
        return (choice.content or "").strip()
    except Exception as exc:
        return f"[API 错误] {type(exc).__name__}: {exc}"


def _trim_payload_by_chars(
    payload: list[dict[str, str]], max_chars: int
) -> list[dict[str, str]]:
    total = sum(len(item.get("content", "")) for item in payload)
    if total <= max_chars or len(payload) <= 2:
        return payload
    system_msg = payload[0]
    history = payload[1:]
    kept_reversed: list[dict[str, str]] = []
    kept_chars = len(system_msg.get("content", ""))
    for msg in reversed(history):
        size = len(msg.get("content", ""))
        if kept_reversed and kept_chars + size > max_chars:
            break
        kept_reversed.append(msg)
        kept_chars += size
    kept = list(reversed(kept_reversed))
    if len(kept) < len(history):
        note = {
            "role": "system",
            "content": "[上下文过长，已省略更早的对话记录，以下为最近上下文。]",
        }
        return [system_msg, note, *kept]
    return [system_msg, *kept]


def should_verify(version_id: str, task_id: str, user_message: str) -> bool:
    sec = sections_loader.get_leaf_section(version_id, task_id)
    if not sec or sec.get("skip_code_verify"):
        return False
    if sec.get("role") in ("planning", "debug"):
        return False
    ref = str(sec.get("code", "")).strip()
    if not ref:
        return False
    if _looks_like_mixed_question(user_message):
        return False
    return _looks_like_code_snippet(user_message)


def chat_verify(
    version_id: str,
    task_id: str,
    user_code: str,
    messages: list[dict[str, Any]] | None = None,
) -> str:
    system = build_verify_system(version_id, task_id, user_code)
    verify_prompt = "请验证我提交的代码是否与本节要求逻辑等价。"
    if messages:
        return _complete_with_history(system, messages, verify_prompt)
    return _complete(system, verify_prompt)


def analyze_debug_mismatch(
    version_id: str,
    sample: dict[str, Any],
    user_output: str,
    program_source: str,
) -> str:
    system = build_debug_analysis_system(
        version_id, sample, user_output, program_source
    )
    return _complete(
        system,
        "请分析输出不一致的可能原因，并引导我修改程序（不要给出完整修改后代码）。",
    )


def chat(
    version_id: str,
    task_id: str,
    messages: list[dict[str, Any]],
    user_message: str,
) -> str:
    sec = sections_loader.get_leaf_section(version_id, task_id)
    if sec and sec.get("skip_code_verify") and _looks_like_code_snippet(user_message):
        return (
            "【提示】当前小节不需要在这里粘贴大段代码做验证（导读或未开放本节验证）。"
            "请切换到左侧具体编码小节后再粘贴代码，或继续用文字提问。"
        )

    if should_verify(version_id, task_id, user_message):
        return chat_verify(version_id, task_id, user_message, messages)

    api_key = _api_key()
    system = build_task_system(version_id, task_id)
    if not api_key:
        return _placeholder(version_id, task_id)

    return _complete_with_history(system, messages, user_message)
