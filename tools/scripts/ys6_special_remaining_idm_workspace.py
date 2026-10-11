#!/usr/bin/env python3
"""Create a deduplicated workspace for untranslated SPECIAL VERSION IDM text."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
ACTION_PREFIX = "<color:0xffacdae8>"
CHOICE_TEXT = {"はい", "いいえ", "やめる", "戻る", "再開", "何も受け取らない", "選んでください", "何処から始める？"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def classify(text: str, candidate_roles: set[str]) -> str:
    if text.startswith(ACTION_PREFIX): return "action_narration"
    if text in CHOICE_TEXT or "choice" in candidate_roles: return "choice"
    if "dialogue" in candidate_roles: return "dialogue"
    if "resource_name" in candidate_roles and len(candidate_roles) == 1: return "resource_or_identifier"
    if all(not character.isalnum() and not JAPANESE.match(character) for character in text.replace("\\n", "")):
        return "punctuation_only"
    if any(token in text for token in ("選べません", "獲得した", "MAX", "Level", "再開")):
        return "system_prompt"
    return "dialogue"


def normalized_player_text(text: str) -> str:
    text = text.replace("アドル", "\\x1").replace("　", "")
    return re.sub(r"<ruby:[^>]+>.*?<endruby>", "", text)


def build(catalog_path: Path, resolution_path: Path, translation_path: Path, output: Path) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    resolution = json.loads(resolution_path.read_text(encoding="utf-8-sig"))
    translations = json.loads(translation_path.read_text(encoding="utf-8-sig"))
    applied = {(row["target_iso_path"], int(row["target_flat_index"])) for row in resolution["all_resolved"]}
    source_by_raw = defaultdict(list)
    source_by_normalized_text = defaultdict(list)
    for row in translations["records"]:
        source_by_raw[row["source_raw_hex"].upper()].append(row)
        source_by_normalized_text[normalized_player_text(row["source_text"])].append(row)
    grouped = defaultdict(list); non_japanese = []
    for resource in catalog["files"]:
        for string in resource["strings"]:
            key = resource["iso_path"], int(string["flat_index"])
            if key in applied: continue
            occurrence = {"map_id": resource["map_id"], "target_iso_path": resource["iso_path"],
                          "target_flat_index": int(string["flat_index"]),
                          "target_record_index": int(string["record_index"]),
                          "target_record_id": int(string["record_id"]),
                          "target_string_index": int(string["string_index"])}
            if not JAPANESE.search(string["text"]):
                non_japanese.append({**occurrence, "source_text": string["text"], "source_raw_hex": string["raw_hex"]})
                continue
            grouped[string["raw_hex"].upper()].append({**occurrence, "source_text": string["text"]})
    units = []
    for unit_index, (raw_hex, occurrences) in enumerate(sorted(grouped.items(), key=lambda item: (item[1][0]["source_text"], item[0]))):
        candidates = source_by_raw.get(raw_hex, [])
        override = [row for row in candidates if row["status"] == "override" and row["translation"]]
        candidate_translations = sorted({row["translation"] for row in override})
        reuse_method = "exact_raw" if len(candidate_translations) == 1 else ""
        if not candidates:
            normalized_candidates = source_by_normalized_text.get(normalized_player_text(occurrences[0]["source_text"]), [])
            normalized_override = [row for row in normalized_candidates if row["status"] == "override" and row["translation"]]
            normalized_translations = sorted({row["translation"].replace("\\x1", "아돌") for row in normalized_override})
            if len(normalized_translations) == 1:
                candidates = normalized_candidates; override = normalized_override
                candidate_translations = normalized_translations; reuse_method = "normalized_player_name"
        roles = {role for row in candidates for role in row.get("roles", [])}
        category = classify(occurrences[0]["source_text"], roles)
        if len(candidate_translations) == 1:
            status = "reused"; translation = candidate_translations[0]
        elif len(candidate_translations) > 1:
            status = "ambiguous_review"; translation = ""
        elif category in ("punctuation_only", "resource_or_identifier"):
            status = "excluded"; translation = ""
        else:
            status = "needs_translation"; translation = ""
        units.append({"unit_id": f"idm_{unit_index:04d}", "category": category, "status": status,
                      "source_text": occurrences[0]["source_text"], "source_raw_hex": raw_hex,
                      "source_sha256": sha(bytes.fromhex(raw_hex)), "translation": translation,
                      "occurrence_count": len(occurrences), "candidate_count": len(candidates),
                      "candidate_translations": candidate_translations,
                      "candidate_roles": sorted(roles), "reuse_method": reuse_method, "occurrences": occurrences})
    summary = {"unresolved_occurrence_count": sum(len(value) for value in grouped.values()) + len(non_japanese),
               "japanese_occurrence_count": sum(len(value) for value in grouped.values()),
               "non_japanese_occurrence_count": len(non_japanese), "unique_unit_count": len(units),
               "status_counts": dict(Counter(row["status"] for row in units)),
               "category_unit_counts": dict(Counter(row["category"] for row in units)),
               "category_occurrence_counts": dict(Counter({category: sum(row["occurrence_count"] for row in units if row["category"] == category)
                                                            for category in {row["category"] for row in units}}))}
    document = {"schema_version": 1, "profile": "ULJM-05155", "source": {
        "catalog_sha256": sha(catalog_path.read_bytes()), "resolution_sha256": sha(resolution_path.read_bytes()),
        "translation_workspace_sha256": sha(translation_path.read_bytes())}, "summary": summary,
        "units": units, "non_japanese_unresolved": non_japanese}
    output.mkdir(parents=True, exist_ok=True)
    (output / "remaining-idm-workspace.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "remaining-idm-workspace.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("unit_id", "category", "status", "occurrence_count", "candidate_count", "source_text", "translation"))
        writer.writeheader()
        for row in units: writer.writerow({key: row[key] for key in writer.fieldnames})
    (output / "inventory-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path); parser.add_argument("resolution", type=Path)
    parser.add_argument("translations", type=Path); parser.add_argument("output", type=Path); args = parser.parse_args()
    print(json.dumps(build(args.catalog, args.resolution, args.translations, args.output), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
