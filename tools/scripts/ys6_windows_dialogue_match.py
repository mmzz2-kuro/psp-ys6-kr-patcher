#!/usr/bin/env python3
"""Match decoded Windows Korean XSO strings to the PSP dialogue workspace."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path


DIALOGUE_ROLES = {"dialogue", "choice", "choice_prompt", "speaker"}
CONTROL_PATTERN = re.compile(r"<(?P<tag>color|scale):[^>]*>|\\x(?P<control>[1-9][0-9]*)")
HANGUL_PATTERN = re.compile(r"[가-힣]")


def structural_tokens(text: str) -> list[str]:
    tokens = []
    for match in CONTROL_PATTERN.finditer(text):
        if match.group("tag"):
            token = match.group(0)
            tokens.append("<color:>" if token == "<color:>" else token)
        elif match.group("control") not in {"1"}:  # Windows translation legitimately expands the player name.
            tokens.append("\\x" + match.group("control"))
    return tokens


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def execute(windows_path: Path, catalog_path: Path, translations_path: Path) -> dict:
    windows = load_json(windows_path)
    catalog = load_json(catalog_path)
    translations = load_json(translations_path)
    psp_records = {(row["iso_path"].lower(), int(row["string_index"])): row for row in catalog["strings"]}
    psp_file_counts = Counter(row["iso_path"].lower() for row in catalog["strings"])
    translation_records = {
        (row["iso_path"].lower(), int(row["string_index"])): row for row in translations["records"]
    }
    windows_file_counts = {
        row["psp_iso_path_candidate"].lower(): int(row["string_count"]) for row in windows["files"]
    }

    rows = []
    match_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    for source in windows["records"]:
        path = source["psp_iso_path_candidate"].lower()
        index = int(source["string_index"])
        key = (path, index)
        target = psp_records.get(key)
        if target is None:
            match_status = "unmatched"
            warnings = ["PSP path/index not found"]
            roles = []
        else:
            roles = list(target.get("roles", []))
            same_count = windows_file_counts[path] == psp_file_counts[path]
            source_tokens = structural_tokens(source["text"])
            target_tokens = structural_tokens(target["text"])
            warnings = []
            if not same_count:
                warnings.append(
                    f"string count differs: Windows={windows_file_counts[path]}, PSP={psp_file_counts[path]}"
                )
            if source_tokens != target_tokens:
                warnings.append(f"control tokens differ: Windows={source_tokens}, PSP={target_tokens}")
            match_status = "exact" if same_count and not warnings else "review"

        current = translation_records.get(key)
        if match_status != "exact":
            action = "review_only"
        elif not DIALOGUE_ROLES.intersection(roles):
            action = "ignored_role"
        elif current is None:
            action = "missing_workspace_record"
        elif current.get("status") == "override":
            action = "preserve_override"
        elif current.get("translation") or current.get("status") == "draft":
            action = "preserve_existing_draft"
        elif not source["text"].strip():
            action = "ignored_empty"
        elif not HANGUL_PATTERN.search(source["text"]):
            action = "ignored_non_korean"
        else:
            action = "draft_candidate"

        match_counts[match_status] += 1
        action_counts[action] += 1
        rows.append({
            "psp_iso_path": source["psp_iso_path_candidate"],
            "windows_archive_path": source["windows_archive_path"],
            "string_index": index,
            "roles": roles,
            "psp_source_text": target["text"] if target else None,
            "windows_translation": source["text"],
            "windows_raw_hex": source["raw_hex"],
            "match_status": match_status,
            "warnings": warnings,
            "action": action,
            "current_status": current.get("status") if current else None,
            "current_translation": current.get("translation") if current else None,
        })
    return {
        "schema_version": 1,
        "source": {
            "windows_dialogues": str(windows_path).replace("\\", "/"),
            "psp_catalog": str(catalog_path).replace("\\", "/"),
            "translations": str(translations_path).replace("\\", "/"),
        },
        "stats": {
            "windows_record_count": len(windows["records"]),
            "match_status_counts": dict(match_counts),
            "action_counts": dict(action_counts),
        },
        "matches": rows,
    }


def apply_drafts(report: dict, translations_path: Path, output_path: Path) -> dict:
    document = load_json(translations_path)
    records = {(row["iso_path"].lower(), int(row["string_index"])): row for row in document["records"]}
    applied = []
    for match in report["matches"]:
        if match["action"] != "draft_candidate":
            continue
        key = (match["psp_iso_path"].lower(), int(match["string_index"]))
        target = records[key]
        if target.get("translation") or target.get("status") not in (None, "", "untranslated"):
            raise ValueError(f"workspace changed after preview: {target['iso_path']}#{target['string_index']}")
        target["translation"] = match["windows_translation"]
        target["status"] = "draft"
        target["notes"] = "Windows 한국어 패치 exact path/index draft import (issue 035)"
        applied.append({"iso_path": target["iso_path"], "string_index": target["string_index"]})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"applied_count": len(applied), "output": str(output_path), "applied": applied}


def replace_existing_translations(
    report: dict,
    translations_path: Path,
    output_path: Path,
    comparison_path: Path,
    backup_path: Path,
) -> dict:
    document = load_json(translations_path)
    records = {(row["iso_path"].lower(), int(row["string_index"])): row for row in document["records"]}
    changes = []
    status_counts: Counter[str] = Counter()
    for match in report["matches"]:
        if match["match_status"] != "exact":
            continue
        if not DIALOGUE_ROLES.intersection(match["roles"]):
            continue
        replacement = match["windows_translation"]
        if not replacement.strip():
            continue
        key = (match["psp_iso_path"].lower(), int(match["string_index"]))
        target = records.get(key)
        if target is None or not target.get("translation"):
            continue
        previous_translation = target["translation"]
        previous_status = target.get("status", "")
        status_counts[previous_status] += 1
        target["translation"] = replacement
        target["status"] = "draft"
        target["notes"] = "Windows 한국어 패치 전체 번역 교체; 재검수 필요 (issue 036)"
        changes.append({
            "iso_path": target["iso_path"],
            "string_index": target["string_index"],
            "previous_status": previous_status,
            "previous_translation": previous_translation,
            "windows_translation": replacement,
            "text_changed": previous_translation != replacement,
            "status_changed": previous_status != "draft",
        })
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(translations_path, backup_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comparison = {
        "schema_version": 1,
        "source_workspace": str(translations_path).replace("\\", "/"),
        "backup": str(backup_path).replace("\\", "/"),
        "output": str(output_path).replace("\\", "/"),
        "stats": {
            "selected_count": len(changes),
            "text_changed_count": sum(row["text_changed"] for row in changes),
            "status_changed_count": sum(row["status_changed"] for row in changes),
            "previous_status_counts": dict(status_counts),
        },
        "changes": changes,
    }
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**comparison["stats"], "backup": str(backup_path), "comparison": str(comparison_path)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="match report JSON")
    parser.add_argument("--apply-drafts", type=Path, help="write an updated translation workspace to this path")
    parser.add_argument("--replace-existing", type=Path, help="replace exact existing translations and write here")
    parser.add_argument("--backup", type=Path, help="required with --replace-existing")
    parser.add_argument("--comparison", type=Path, help="required with --replace-existing")
    args = parser.parse_args()
    report = execute(args.windows, args.catalog, args.translations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"report": str(args.output), "stats": report["stats"]}
    if args.apply_drafts:
        summary["draft_apply"] = apply_drafts(report, args.translations, args.apply_drafts)
        summary["draft_apply"].pop("applied", None)
    if args.replace_existing:
        if args.apply_drafts:
            parser.error("--apply-drafts and --replace-existing cannot be used together")
        if not args.backup or not args.comparison:
            parser.error("--replace-existing requires --backup and --comparison")
        summary["replacement"] = replace_existing_translations(
            report, args.translations, args.replace_existing, args.comparison, args.backup
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
