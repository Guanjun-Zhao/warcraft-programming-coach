# -*- coding: utf-8 -*-
"""Build data/versionN/samples.json from warriors teacher in/out files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent

CaseStyle = Literal["colon", "space"]

VERSIONS: dict[str, dict[str, str | int]] = {
    "version1": {
        "in": "data/warriors1_data/data.in",
        "out": "data/warriors1_data/data.out",
        "lines_per_case": 2,
        "case_style": "colon",
    },
    "version2": {
        "in": "data/warriors2_data/data.in",
        "out": "data/warriors2_data/data.out",
        "lines_per_case": 2,
        "case_style": "colon",
    },
    "version3": {
        "in": "data/warriors3_data/data.in",
        "out": "data/warriors3_data/data.out",
        "lines_per_case": 3,
        "case_style": "space",
    },
    "version4": {
        "in": "data/warriors4_data/Warcraft.in",
        "out": "data/warriors4_data/Warcraft.out",
        "lines_per_case": 3,
        "case_style": "space",
    },
}

SOURCE = "\u8001\u5e08\u6837\u4f8b"
CASE_HEADER_COLON = re.compile(r"^Case:\d+$")
CASE_HEADER_SPACE = re.compile(r"^Case \d+:$")


def parse_input_cases(text: str, lines_per_case: int) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    count = int(lines[0])
    idx = 1
    cases: list[str] = []
    for _ in range(count):
        block = lines[idx : idx + lines_per_case]
        if len(block) != lines_per_case:
            raise ValueError(
                f"expected {lines_per_case} input lines per case, got {len(block)}"
            )
        idx += lines_per_case
        cases.append("1\n" + "\n".join(block) + "\n")
    return cases


def parse_output_cases(text: str, case_style: CaseStyle) -> list[str]:
    header = CASE_HEADER_COLON if case_style == "colon" else CASE_HEADER_SPACE
    header_line = "Case:1" if case_style == "colon" else "Case 1:"
    bodies: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if header.match(line):
            if current:
                bodies.append(current)
            current = []
            continue
        if line.strip():
            current.append(line)
    if current:
        bodies.append(current)
    return [header_line + "\n" + "\n".join(body) + "\n" for body in bodies]


def build_samples(version_id: str) -> list[dict[str, object]]:
    cfg = VERSIONS[version_id]
    input_text = (ROOT / str(cfg["in"])).read_text(encoding="utf-8")
    output_text = (ROOT / str(cfg["out"])).read_text(encoding="utf-8")
    lines_per_case = int(cfg["lines_per_case"])
    case_style = str(cfg["case_style"])
    if case_style not in ("colon", "space"):
        raise ValueError(f"{version_id}: unknown case_style {case_style!r}")
    inputs = parse_input_cases(input_text, lines_per_case)
    outputs = parse_output_cases(output_text, case_style)  # type: ignore[arg-type]
    if len(inputs) != len(outputs):
        raise ValueError(
            f"{version_id}: input case count {len(inputs)} != output case count {len(outputs)}"
        )
    samples: list[dict[str, object]] = []
    for inp, out in zip(inputs, outputs, strict=True):
        if not inp.strip() or not out.strip():
            raise ValueError(f"{version_id}: empty input or output in a sample")
        samples.append(
            {
                "input": inp,
                "output": out,
                "tags": [],
                "source": SOURCE,
            }
        )
    return samples


def write_version(version_id: str) -> tuple[Path, int]:
    samples = build_samples(version_id)
    out_path = ROOT / "data" / version_id / "samples.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(samples, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path, len(samples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build version samples.json files.")
    parser.add_argument(
        "versions",
        nargs="*",
        default=["version2", "version3", "version4"],
        choices=sorted(VERSIONS),
        metavar="VERSION",
    )
    args = parser.parse_args()
    for version_id in args.versions:
        path, count = write_version(version_id)
        print(f"Wrote {path} ({count} samples)")


if __name__ == "__main__":
    main()
