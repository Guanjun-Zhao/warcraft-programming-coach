# -*- coding: utf-8 -*-
"""Build data/versionN/sections.json from warcraft chapter + code markdown."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PLANNING_TITLE = "\u529f\u80fd\u8bbe\u8ba1"

VERSIONS: dict[str, dict[str, object]] = {
    "version1": {
        "chapter": "reference/version1/warcraft1_chapter.md",
        "code": "reference/version1/warcraft1_code.md",
        "chapter_no": 1,
        "outline": "reference/version1/warcraft1_outline.json",
    },
    "version2": {
        "chapter": "reference/version2/warcraft2_chapter.md",
        "code": "reference/version2/warcraft2_code.md",
        "chapter_no": 2,
        "outline": "reference/version2/warcraft2_outline.json",
    },
    "version3": {
        "chapter": "reference/version3/warcraft3_chapter.md",
        "code": "reference/version3/warcraft3_code.md",
        "chapter_no": 3,
        "outline": "reference/version3/warcraft3_outline.json",
    },
    "version4": {
        "chapter": "reference/version4/warcraft4_chapter.md",
        "code": "reference/version4/warcraft4_code.md",
        "chapter_no": 4,
        "outline": "reference/version4/warcraft4_outline.json",
    },
}
SPECIAL_SOURCE_REFS = {"__intro_planning__"}


def _read_text_best_effort(path: Path) -> str:
    """Read text with utf-8 first, then common legacy encodings."""
    encodings = ("utf-8", "gbk", "cp936")
    last_exc: Exception | None = None
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    return path.read_text(encoding="utf-8")


def _strip_heading_line(block: str) -> str:
    lines = block.splitlines()
    if not lines:
        return ""
    if lines[0].startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def parse_chapter(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_key
        if current_key is not None:
            parts[current_key] = _strip_heading_line("\n".join(buf))
        buf = []

    for line in text.splitlines():
        m2 = re.match(r"^##\s+(\d+\.\d+)\s+(.+)$", line)
        m3 = re.match(r"^###\s+(\d+\.\d+\.\d+)\s+(.+)$", line)
        if m3:
            flush()
            current_key = m3.group(1)
            buf = [line]
            continue
        if m2:
            flush()
            current_key = m2.group(1)
            buf = [line]
            continue
        if current_key is not None:
            buf.append(line)
    flush()
    return parts


def parse_heading_titles(text: str) -> tuple[dict[str, str], dict[str, str]]:
    h2: dict[str, str] = {}
    h3: dict[str, str] = {}
    for line in text.splitlines():
        m2 = re.match(r"^##\s+(\d+\.\d+)\s+(.+)$", line)
        m3 = re.match(r"^###\s+(\d+\.\d+\.\d+)\s+(.+)$", line)
        if m2:
            h2[m2.group(1)] = m2.group(2).strip()
        if m3:
            h3[m3.group(1)] = m3.group(2).strip()
    return h2, h3


def parse_intro_and_planning(text: str, chapter_no: int) -> str:
    lines = text.splitlines()
    intro: list[str] = []
    planning: list[str] = []
    mode = "intro"
    planning_heading = re.compile(rf"^##\s+{chapter_no}\.1\s+")
    next_heading = re.compile(rf"^##\s+{chapter_no}\.2\s+")
    for line in lines:
        if line.startswith("# ") and not line.startswith("##"):
            continue
        if planning_heading.match(line):
            mode = "planning"
            continue
        if next_heading.match(line):
            break
        if mode == "intro":
            if line.strip():
                intro.append(line)
        else:
            if line.strip():
                planning.append(line)
    return "\n\n".join(["\n".join(intro).strip(), "\n".join(planning).strip()]).strip()


def parse_code_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for m in re.finditer(
        r"^##\s+\S+\s+(\d+(?:\.\d+)*(?:[a-z])?)\s+.+?\n+```cpp\n(.*?)```",
        text,
        flags=re.MULTILINE | re.DOTALL,
    ):
        blocks[m.group(1)] = m.group(2).rstrip("\n")
    return blocks


def _code_sort_key(key: str) -> tuple[tuple[int, ...], str]:
    m = re.match(r"^(\d+(?:\.\d+)*)([a-z]*)$", key)
    if not m:
        return ((0,), key)
    parts = tuple(int(part) for part in m.group(1).split("."))
    return (parts, m.group(2))


def collect_code(codes: dict[str, str], section_id: str) -> str:
    keys = [
        key
        for key in codes
        if key == section_id
        or (
            key.startswith(section_id)
            and key[len(section_id) :].isalpha()
            and key[len(section_id) :].isascii()
        )
    ]
    keys.sort(key=_code_sort_key)
    return "\n\n".join(codes[key] for key in keys)


def collect_code_by_refs(codes: dict[str, str], refs: list[str]) -> str:
    pieces: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        chunk = collect_code(codes, ref).strip()
        if not chunk or chunk in seen:
            continue
        seen.add(chunk)
        pieces.append(chunk)
    return "\n\n".join(pieces).strip()


def section_id_to_task_id(section_id: str) -> str:
    return "task_" + section_id.replace(".", "_")


def leaf_description(chapter_no: int, sections: dict[str, str], section_id: str) -> str:
    if chapter_no == 1 and section_id == "1.4.1":
        return "\n\n".join(
            part
            for part in (sections.get("1.4", "").strip(), sections.get("1.4.1", "").strip())
            if part
        ).strip()
    return sections.get(section_id, "").strip()


def ordered_h2_ids(chapter_text: str, chapter_no: int) -> list[str]:
    planning_id = f"{chapter_no}.1"
    ids: list[str] = []
    for line in chapter_text.splitlines():
        m2 = re.match(rf"^##\s+({chapter_no}\.\d+)\s+", line)
        if not m2:
            continue
        h2_id = m2.group(1)
        if h2_id != planning_id:
            ids.append(h2_id)
    return ids


def child_section_ids(h2_id: str, sections: dict[str, str]) -> list[str]:
    pattern = re.compile(rf"^{re.escape(h2_id)}\.\d+$")
    return sorted(
        (key for key in sections if pattern.match(key)),
        key=lambda key: [int(part) for part in key.split(".")],
    )


def build_groups(
    chapter_text: str,
    chapter_no: int,
    sections: dict[str, str],
    h2_titles: dict[str, str],
    h3_titles: dict[str, str],
    codes: dict[str, str],
) -> list[dict]:
    groups: list[dict] = []
    for h2_id in ordered_h2_ids(chapter_text, chapter_no):
        child_ids = child_section_ids(h2_id, sections)
        leaf_ids = child_ids if child_ids else [h2_id]
        group_sections: list[dict] = []
        for section_id in leaf_ids:
            group_sections.append(
                {
                    "section_id": section_id,
                    "task_id": section_id_to_task_id(section_id),
                    "title": h3_titles.get(section_id)
                    or h2_titles.get(section_id, section_id),
                    "description": leaf_description(chapter_no, sections, section_id),
                    "code": collect_code(codes, section_id),
                }
            )
        groups.append(
            {
                "h2_id": h2_id,
                "h2_title": h2_titles[h2_id],
                "sections": group_sections,
            }
        )
    return groups


def _require_str_list(raw: Any, field_name: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
        raise ValueError(f"{field_name} must be a list[str]")
    return [x.strip() for x in raw if x.strip()]


def _resolve_source_description(
    sections: dict[str, str],
    intro_planning_text: str,
    refs: list[str],
) -> str:
    blocks: list[str] = []
    for ref in refs:
        if ref == "__intro_planning__":
            if intro_planning_text.strip():
                blocks.append(intro_planning_text.strip())
            continue
        text = sections.get(ref, "").strip()
        if text:
            blocks.append(text)
    return "\n\n".join(blocks).strip()


def _validate_outline(
    outline: dict[str, Any],
    sections: dict[str, str],
    codes: dict[str, str],
    intro_planning_text: str,
) -> None:
    planning = outline.get("planning")
    groups = outline.get("groups")
    debug_task_id = str(outline.get("debug_task_id", "task_debug")).strip() or "task_debug"
    if not isinstance(planning, dict):
        raise ValueError("outline.planning must be an object")
    if not isinstance(groups, list):
        raise ValueError("outline.groups must be a list")
    all_task_ids: set[str] = set()

    def _check_task(task: dict[str, Any], prefix: str) -> None:
        task_id = str(task.get("task_id", "")).strip()
        if not task_id:
            raise ValueError(f"{prefix}.task_id is required")
        if task_id in all_task_ids:
            raise ValueError(f"duplicate task_id: {task_id}")
        all_task_ids.add(task_id)
        src_refs = _require_str_list(task.get("source_section_refs"), f"{prefix}.source_section_refs")
        code_refs = _require_str_list(task.get("code_block_refs"), f"{prefix}.code_block_refs")
        for ref in src_refs:
            if ref in SPECIAL_SOURCE_REFS:
                if ref == "__intro_planning__" and not intro_planning_text.strip():
                    raise ValueError(f"{prefix} references empty {ref}")
                continue
            if ref not in sections:
                raise ValueError(f"{prefix} source_section_ref not found: {ref}")
        for ref in code_refs:
            if not collect_code(codes, ref).strip():
                raise ValueError(f"{prefix} code_block_ref not found: {ref}")

    _check_task(planning, "planning")
    for gi, g in enumerate(groups):
        if not isinstance(g, dict):
            raise ValueError(f"groups[{gi}] must be an object")
        secs = g.get("sections")
        if not isinstance(secs, list):
            raise ValueError(f"groups[{gi}].sections must be a list")
        for si, sec in enumerate(secs):
            if not isinstance(sec, dict):
                raise ValueError(f"groups[{gi}].sections[{si}] must be an object")
            _check_task(sec, f"groups[{gi}].sections[{si}]")

    if debug_task_id in all_task_ids:
        raise ValueError("debug_task_id conflicts with existing task_id")

    for gi, g in enumerate(groups):
        for si, sec in enumerate(g.get("sections") or []):
            pres = _require_str_list(
                sec.get("prerequisites"), f"groups[{gi}].sections[{si}].prerequisites"
            )
            for dep in pres:
                if dep not in all_task_ids:
                    raise ValueError(
                        f"groups[{gi}].sections[{si}] prerequisite not found: {dep}"
                    )


def build_spec_from_outline(
    chapter_text: str,
    chapter_no: int,
    sections: dict[str, str],
    codes: dict[str, str],
    outline: dict[str, Any],
) -> dict[str, Any]:
    intro_planning_text = parse_intro_and_planning(chapter_text, chapter_no)
    _validate_outline(outline, sections, codes, intro_planning_text)

    planning_raw = outline["planning"]
    planning_source_refs = _require_str_list(
        planning_raw.get("source_section_refs"), "planning.source_section_refs"
    )
    planning_code_refs = _require_str_list(
        planning_raw.get("code_block_refs"), "planning.code_block_refs"
    )
    planning_desc = (
        str(planning_raw.get("description", "")).strip()
        or _resolve_source_description(
            sections, intro_planning_text, planning_source_refs
        )
    )
    planning_task_id = str(planning_raw.get("task_id")).strip()
    planning_section_id = str(
        planning_raw.get("section_id") or f"{chapter_no}.1"
    ).strip()

    groups_out: list[dict[str, Any]] = []
    for group in outline.get("groups") or []:
        group_id = str(group.get("h2_id", "")).strip()
        group_title = str(group.get("h2_title", "")).strip()
        sections_out: list[dict[str, Any]] = []
        for sec in group.get("sections") or []:
            src_refs = _require_str_list(sec.get("source_section_refs"), "section.source_section_refs")
            code_refs = _require_str_list(sec.get("code_block_refs"), "section.code_block_refs")
            learning_goal = str(sec.get("learning_goal", "")).strip()
            desc_body = str(sec.get("description", "")).strip() or _resolve_source_description(
                sections, intro_planning_text, src_refs
            )
            if learning_goal:
                desc = f"学习目标：{learning_goal}\n\n{desc_body}".strip()
            else:
                desc = desc_body
            sections_out.append(
                {
                    "section_id": str(
                        sec.get("section_id") or sec.get("task_id")
                    ).strip(),
                    "task_id": str(sec.get("task_id")).strip(),
                    "title": str(sec.get("title", "")).strip(),
                    "description": desc,
                    "code": collect_code_by_refs(codes, code_refs),
                    "learning_goal": learning_goal,
                    "source_section_refs": src_refs,
                    "code_block_refs": code_refs,
                    "prerequisites": _require_str_list(
                        sec.get("prerequisites"), "section.prerequisites"
                    ),
                }
            )
        groups_out.append(
            {
                "h2_id": group_id,
                "h2_title": group_title,
                "sections": sections_out,
            }
        )

    return {
        "planning": {
            "section_id": planning_section_id,
            "task_id": planning_task_id,
            "title": str(planning_raw.get("title", PLANNING_TITLE)).strip(),
            "description": planning_desc,
            "code": collect_code_by_refs(codes, planning_code_refs),
            "skip_code_verify": True,
            "role": "planning",
            "learning_goal": str(planning_raw.get("learning_goal", "")).strip(),
            "source_section_refs": planning_source_refs,
            "code_block_refs": planning_code_refs,
        },
        "groups": groups_out,
        "debug_task_id": str(outline.get("debug_task_id", "task_debug")).strip()
        or "task_debug",
    }


def build_spec(version_id: str, outline_override: str | None = None) -> dict:
    cfg = VERSIONS[version_id]
    chapter_no = int(cfg["chapter_no"])
    chapter_path = ROOT / str(cfg["chapter"])
    code_path = ROOT / str(cfg["code"])
    chapter_text = _read_text_best_effort(chapter_path)
    code_text = _read_text_best_effort(code_path)
    sections = parse_chapter(chapter_text)
    h2_titles, h3_titles = parse_heading_titles(chapter_text)
    codes = parse_code_blocks(code_text)
    outline_path_str = outline_override or str(cfg.get("outline") or "").strip()
    if outline_path_str:
        outline_path = ROOT / outline_path_str
        if outline_path.is_file():
            outline = json.loads(_read_text_best_effort(outline_path))
            if not isinstance(outline, dict):
                raise ValueError(f"outline must be a JSON object: {outline_path}")
            return build_spec_from_outline(
                chapter_text, chapter_no, sections, codes, outline
            )
    planning_id = f"{chapter_no}.1"
    return {
        "planning": {
            "section_id": planning_id,
            "task_id": section_id_to_task_id(planning_id),
            "title": PLANNING_TITLE,
            "description": parse_intro_and_planning(chapter_text, chapter_no),
            "code": "",
            "skip_code_verify": True,
            "role": "planning",
        },
        "groups": build_groups(
            chapter_text, chapter_no, sections, h2_titles, h3_titles, codes
        ),
        "debug_task_id": "task_debug",
    }


def write_version(version_id: str, outline_override: str | None = None) -> Path:
    out_path = ROOT / "data" / version_id / "sections.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            build_spec(version_id, outline_override=outline_override),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build version sections.json files.")
    parser.add_argument(
        "versions",
        nargs="*",
        default=[],
        metavar="VERSION",
    )
    parser.add_argument(
        "--outline",
        dest="outline",
        default="",
        help="Optional outline JSON path (relative to repo root). Only valid when one VERSION is provided.",
    )
    args = parser.parse_args()
    outline_override = args.outline.strip() or None
    if outline_override and len(args.versions) != 1:
        parser.error("--outline requires exactly one VERSION.")
    raw_versions = [v for v in args.versions if v and v != "[]"]
    invalid = [v for v in raw_versions if v not in VERSIONS]
    if invalid:
        parser.error(
            "invalid VERSION: "
            + ", ".join(invalid)
            + f" (choose from {', '.join(sorted(VERSIONS))})"
        )
    selected = raw_versions if raw_versions else sorted(VERSIONS)
    skipped = [vid for vid in sorted(VERSIONS) if vid not in selected]
    if skipped:
        print(f"Skipped versions: {', '.join(skipped)}")
    for version_id in selected:
        path = write_version(
            version_id,
            outline_override=outline_override if len(selected) == 1 else None,
        )
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
