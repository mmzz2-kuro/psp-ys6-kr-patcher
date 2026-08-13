#!/usr/bin/env python3
"""Normalize approved Ys VI draft control, ruby, and unsupported characters."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_translation_workspace import MARKUP_PATTERN, TOKEN_PATTERN, validate
except ModuleNotFoundError:
    from ys6_translation_workspace import MARKUP_PATTERN, TOKEN_PATTERN, validate

RUBY_PATTERN = re.compile(r"<ruby:[^<>]+>.*?<endruby>")
LONE_BACKSLASH = re.compile(r"\\(?!x[0-9A-Fa-f]+|[A-Za-z]+|[0-9]+)")
CHARACTER_CANDIDATES = {
    "─": "-", "～": "~", "《": "[", "》": "]",
    "①": "(1)", "②": "(2)", "③": "(3)", "ㆍ": ".", "★": "*",
}

# Context-reviewed corrections that cannot be decided safely by token counts alone.
EXPLICIT_CORRECTIONS = {
    ("PSP_GAME/USRDIR/data/map/s_00/s_0000/seltalk.xso.z", 34): (
        "나나 자네와 같은 처지의 사람들이\\마을을 쌓아 올려, \\n그럭저럭 생활을 하고 있다.",
        "나나 자네와 같은 처지의 사람들이\\n마을을 쌓아 올려, \\n그럭저럭 생활을 하고 있다.",
    ),
    ("PSP_GAME/USRDIR/data/map/s_05/s_0550/bikini.xso.z", 5): (
        "아돌 씨, \\n\\참 잘해 주셨어요.", "아돌 씨, \\n참 잘해 주셨어요.",
    ),
    ("PSP_GAME/USRDIR/data/map/s_40/s_4011/talkbasuramu.xso.z", 50): (
        "가지고 있으면, 물 속에서도\\n자유롭게 행동할 수 있게 해주는\\멋진 물건이라고.",
        "가지고 있으면, 물 속에서도\\n자유롭게 행동할 수 있게 해주는\\n멋진 물건이라고.",
    ),
    ("PSP_GAME/USRDIR/data/map/s_02/s_020a/adolsleep.xso.z", 18): (
        "<color:0xffacdae8>아돌은 이름을 밝히고\\n치료해 준 데 대해 감사를 표했다.",
        "<color:0xffacdae8>아돌은 이름을 밝히고 치료해 준 데 대해 감사를 표했다.",
    ),
    ("PSP_GAME/USRDIR/data/map/s_05/s_0550/bikini.xso.z", 8): (
        "역시 다르시네요, n아돌 씨.", "역시 다르시네요, \\n아돌 씨.",
    ),
    ("PSP_GAME/USRDIR/data/map/s_40/s_4080/meetingagainraba.xso.z", 8): (
        "아돌이여. 이 늙은이를 기억하고 있는가?", "아돌이여.\\n이 늙은이를 기억하고 있는가?",
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ruby_only_change(source: str, translation: str) -> bool:
    source_markup = MARKUP_PATTERN.findall(source)
    target_markup = MARKUP_PATTERN.findall(translation)
    removed = list(source_markup)
    for tag in target_markup:
        if tag not in removed:
            return False
        removed.remove(tag)
    return bool(removed) and all(tag.startswith("<ruby:") or tag == "<endruby>" for tag in removed)


def normalize(document: dict) -> tuple[dict, dict]:
    result = json.loads(json.dumps(document, ensure_ascii=False))
    changes: list[dict] = []
    deferred: list[dict] = []
    counts = Counter()
    for row in result.get("records", []):
        if row.get("status") != "draft" or not row.get("translation"):
            continue
        source = row.get("source_text", "")
        before = row["translation"]
        translation = before
        kinds = []

        identity = (row["iso_path"], int(row["string_index"]))
        correction = EXPLICIT_CORRECTIONS.get(identity)
        if correction and translation == correction[0]:
            translation = correction[1]
            kinds.append("context_reviewed_control_correction")
            counts["context_reviewed_control_correction"] += 1

        source_tokens = TOKEN_PATTERN.findall(source)
        target_tokens = TOKEN_PATTERN.findall(translation)
        missing_names = source_tokens.count("\\x1") - target_tokens.count("\\x1")
        source_other = sorted(token for token in source_tokens if token != "\\x1")
        target_other = sorted(token for token in target_tokens if token != "\\x1")
        if missing_names > 0 and source_other == target_other and translation.count("아돌") >= missing_names:
            if not row.get("allow_player_name_expansion", False):
                row["allow_player_name_expansion"] = True
                kinds.append("player_name_expansion")
                counts["player_name_expansion"] += 1

        lone_positions = [match.start() for match in LONE_BACKSLASH.finditer(translation)]
        if lone_positions:
            source_newlines = source.count("\\n")
            target_newlines = translation.count("\\n")
            if source_newlines - target_newlines == len(lone_positions):
                translation = LONE_BACKSLASH.sub(r"\\n", translation)
                kinds.append("lone_backslash_to_newline")
                counts["lone_backslash_to_newline"] += 1
            else:
                deferred.append({"iso_path": row["iso_path"], "string_index": row["string_index"], "reason": "ambiguous_lone_backslash", "source_text": source, "translation": translation})

        if MARKUP_PATTERN.findall(source) != MARKUP_PATTERN.findall(translation):
            if ruby_only_change(source, translation):
                if not row.get("allow_markup_change", False):
                    row["allow_markup_change"] = True
                    kinds.append("japanese_ruby_removed")
                    counts["japanese_ruby_removed"] += 1
            else:
                deferred.append({"iso_path": row["iso_path"], "string_index": row["string_index"], "reason": "non_ruby_or_mixed_markup_change", "source_text": source, "translation": translation})

        replacements = []
        for character, candidate in CHARACTER_CANDIDATES.items():
            occurrences = translation.count(character)
            if occurrences:
                translation = translation.replace(character, candidate)
                replacements.append({"from": character, "to": candidate, "count": occurrences})
                counts[f"character_{ord(character):04X}"] += occurrences
        if replacements:
            kinds.append("unsupported_character_candidate")

        row["translation"] = translation
        if kinds or translation != before:
            note = "normalized 039: " + ", ".join(kinds)
            row["notes"] = (row.get("notes", "") + " | " + note).strip(" |")
            changes.append({
                "iso_path": row["iso_path"], "string_index": row["string_index"],
                "kinds": kinds, "before": before, "after": translation,
                "replacements": replacements,
            })
    return result, {"counts": dict(counts), "change_count": len(changes), "deferred_count": len(deferred), "changes": changes, "deferred": deferred}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if (args.output.exists() or args.report.exists()) and not args.overwrite:
        raise FileExistsError("output exists; pass --overwrite")
    source = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    normalized, report = normalize(source)
    report["source_sha256"] = digest(args.workspace)
    report["record_count"] = len(normalized.get("records", []))
    report["draft_count"] = sum(row.get("status") == "draft" for row in normalized.get("records", []))
    report["workspace_validation"] = validate(normalized)
    if args.backup:
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.workspace, args.backup)
        report["backup"] = str(args.backup)
        report["backup_sha256"] = digest(args.backup)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["output_sha256"] = digest(args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("record_count", "draft_count", "change_count", "deferred_count", "counts", "workspace_validation")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
