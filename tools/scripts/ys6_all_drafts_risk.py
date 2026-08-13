#!/usr/bin/env python3
"""Prepare and analyze an all-drafts-as-override workspace without touching source data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_translation_workspace import validate
except ModuleNotFoundError:
    from ys6_translation_workspace import validate


CONTROL_RE = re.compile(r"<(?P<tag>color|scale):[^>]*>|\\x(?P<code>[1-9][0-9]*)")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff]")
UNRESOLVED_RE = re.compile(r"\{[0-9A-F]{4}\}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def prepare(workspace_path: Path, output_path: Path, valid_output_path: Path | None = None,
            catalog_path: Path | None = None, runtime_map_path: Path | None = None,
            buildable_output_path: Path | None = None) -> dict:
    document = load(workspace_path)
    promoted = []
    for row in document["records"]:
        if row.get("status") == "draft" and row.get("translation", "").strip():
            row["status"] = "override"
            promoted.append((row["iso_path"], int(row["string_index"])))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = validate(document)
    invalid_positions = sorted({int(match.group(1)) for error in report["errors"] if (match := re.match(r"record\[(\d+)\]", error))})
    valid_summary = None
    if valid_output_path is not None:
        valid_document = json.loads(json.dumps(document, ensure_ascii=False))
        for position in invalid_positions:
            valid_document["records"][position]["status"] = "draft"
        valid_report = validate(valid_document)
        if not valid_report["valid"]:
            raise ValueError("failed to produce a valid maximum override subset")
        valid_output_path.parent.mkdir(parents=True, exist_ok=True)
        valid_output_path.write_text(json.dumps(valid_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        valid_summary = {
            "path": str(valid_output_path),
            "sha256": sha256(valid_output_path),
            "override_count": valid_report["override_count"],
            "excluded_invalid_record_count": len(invalid_positions),
        }
    buildable_summary = None
    if buildable_output_path is not None:
        if valid_output_path is None or catalog_path is None or runtime_map_path is None:
            raise ValueError("buildable output requires valid output, catalog, and runtime map")
        buildable = load(valid_output_path)
        catalog = load(catalog_path)
        runtime_map = load(runtime_map_path)
        file_hashes = {row["iso_path"]: row["xso_sha256"] for row in catalog["files"]}
        mappings = {row["xso_sha256"]: row for row in runtime_map["mappings"]}
        excluded = Counter()
        for row in buildable["records"]:
            if row.get("status") != "override":
                continue
            digest = file_hashes.get(row["iso_path"])
            mapping = mappings.get(digest)
            if not mapping or mapping.get("status") not in {"exact_one_to_one", "standalone_duplicate", "standalone_only", "many_to_many"}:
                row["status"] = "draft"
                excluded[mapping.get("status", "missing") if mapping else "missing"] += 1
        grouped: dict[tuple[str, int], list[dict]] = {}
        for row in buildable["records"]:
            if row.get("status") != "override":
                continue
            digest = file_hashes[row["iso_path"]]
            grouped.setdefault((digest, int(row["string_index"])), []).append(row)
        conflict_groups = 0
        conflict_records = 0
        for _key, shared in grouped.items():
            if len({row["translation"] for row in shared}) <= 1:
                continue
            conflict_groups += 1
            for row in shared:
                row["status"] = "draft"
                conflict_records += 1
        buildable_output_path.parent.mkdir(parents=True, exist_ok=True)
        buildable_output_path.write_text(json.dumps(buildable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        buildable_report = validate(buildable)
        if not buildable_report["valid"]:
            raise ValueError("buildable subset unexpectedly failed workspace validation")
        buildable_summary = {
            "path": str(buildable_output_path),
            "sha256": sha256(buildable_output_path),
            "override_count": buildable_report["override_count"],
            "excluded_runtime_mapping_counts": dict(excluded),
            "shared_payload_conflict_group_count": conflict_groups,
            "shared_payload_conflict_record_count": conflict_records,
        }
    return {
        "source_sha256": sha256(workspace_path),
        "output_sha256": sha256(output_path),
        "record_count": len(document["records"]),
        "promoted_count": len(promoted),
        "remaining_draft_count": sum(row.get("status") == "draft" for row in document["records"]),
        "override_count": sum(row.get("status") == "override" for row in document["records"]),
        "validation_error_count": len(report["errors"]),
        "invalid_record_count": len(invalid_positions),
        "valid_subset": valid_summary,
        "buildable_subset": buildable_summary,
    }


def controls(text: str) -> list[str]:
    return [match.group(0) for match in CONTROL_RE.finditer(text)]


def exclude_characters(workspace_path: Path, output_path: Path, characters: str) -> dict:
    document = load(workspace_path)
    excluded = []
    character_set = set(characters)
    for row in document["records"]:
        found = sorted(character_set.intersection(row.get("translation", "")))
        if row.get("status") == "override" and found:
            row["status"] = "draft"
            excluded.append({"iso_path": row["iso_path"], "string_index": row["string_index"], "characters": found})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = validate(document)
    if not report["valid"]:
        raise ValueError("character-excluded workspace is invalid")
    return {"override_count": report["override_count"], "excluded_record_count": len(excluded), "characters": sorted(character_set)}


def display_width(line: str) -> int:
    # Approximation for the PSP fixed-cell renderer: ASCII occupies roughly half a CJK cell.
    plain = re.sub(r"<[^>]+>", "", line)
    plain = re.sub(r"\\x[1-9][0-9]*", "아돌", plain)
    return sum(1 if ord(character) < 128 else 2 for character in plain)


def analyze(workspace_path: Path, match_path: Path, preflight_dir: Path, output_path: Path, samples_path: Path) -> dict:
    workspace = load(workspace_path)
    match = load(match_path)
    match_by_key = {
        (row["psp_iso_path"].lower(), int(row["string_index"])): row for row in match["matches"]
    }
    rows = [row for row in workspace["records"] if row.get("status") == "override"]
    risks = Counter()
    samples = []
    for row in rows:
        source = row.get("source_text", "")
        translation = row.get("translation", "")
        key = (row["iso_path"].lower(), int(row["string_index"]))
        matched = match_by_key.get(key)
        categories = []
        if not matched or matched.get("match_status") != "exact":
            categories.append("non_exact_windows_match")
        if controls(source) != controls(translation):
            categories.append("control_token_difference")
        if "\\x1" in source and "\\x1" not in translation:
            categories.append("player_name_variable_expanded")
        if "<ruby:" in source and "<ruby:" not in translation:
            categories.append("ruby_removed")
        source_lines = source.split("\\n")
        translated_lines = translation.split("\\n")
        if len(translated_lines) > len(source_lines):
            categories.append("line_count_increased")
        maximum_width = max((display_width(line) for line in translated_lines), default=0)
        if maximum_width > 48:
            categories.append("long_line_over_24_cjk_cells")
        if JAPANESE_RE.search(translation):
            categories.append("japanese_remaining")
        if UNRESOLVED_RE.search(translation):
            categories.append("unresolved_code_marker")
        for category in categories:
            risks[category] += 1
        if categories:
            samples.append({
                "iso_path": row["iso_path"],
                "string_index": row["string_index"],
                "roles": " | ".join(row.get("roles", [])),
                "categories": " | ".join(categories),
                "source_text": source,
                "translation": translation,
                "source_byte_length": len(bytes.fromhex(row["source_raw_hex"])),
                "translation_utf8_length": len(translation.encode("utf-8")),
                "max_display_width": maximum_width,
            })

    preflight = load(preflight_dir / "preflight-report.json") if (preflight_dir / "preflight-report.json").exists() else None
    xso_rows = []
    xso_csv = preflight_dir / "xso-report.csv"
    if xso_csv.exists():
        with xso_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            xso_rows = list(csv.DictReader(stream))
    remaining = [int(row["remaining_slack"]) for row in xso_rows if row.get("remaining_slack", "") not in ("", None)]
    report = {
        "schema_version": 1,
        "workspace_sha256": sha256(workspace_path),
        "stats": {
            "override_count": len(rows),
            "risk_counts": dict(risks),
            "risk_record_count": len(samples),
            "xso_report_count": len(xso_rows),
            "minimum_remaining_slack": min(remaining) if remaining else None,
        },
        "preflight": preflight,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    samples.sort(key=lambda row: ("non_exact_windows_match" not in row["categories"], -row["max_display_width"]))
    with samples_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ("iso_path", "string_index", "roles", "categories", "source_text", "translation", "source_byte_length", "translation_utf8_length", "max_display_width")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(samples)
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparing = commands.add_parser("prepare")
    preparing.add_argument("--workspace", type=Path, required=True)
    preparing.add_argument("--output", type=Path, required=True)
    preparing.add_argument("--valid-output", type=Path)
    preparing.add_argument("--catalog", type=Path)
    preparing.add_argument("--runtime-map", type=Path)
    preparing.add_argument("--buildable-output", type=Path)
    analyzing = commands.add_parser("analyze")
    analyzing.add_argument("--workspace", type=Path, required=True)
    analyzing.add_argument("--match", type=Path, required=True)
    analyzing.add_argument("--preflight", type=Path, required=True)
    analyzing.add_argument("--output", type=Path, required=True)
    analyzing.add_argument("--samples", type=Path, required=True)
    excluding = commands.add_parser("exclude-characters")
    excluding.add_argument("--workspace", type=Path, required=True)
    excluding.add_argument("--output", type=Path, required=True)
    excluding.add_argument("--characters", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.workspace, args.output, args.valid_output, args.catalog, args.runtime_map, args.buildable_output)
    elif args.command == "analyze":
        result = analyze(args.workspace, args.match, args.preflight, args.output, args.samples)
    else:
        result = exclude_characters(args.workspace, args.output, args.characters)
    print(json.dumps(result.get("stats", result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
