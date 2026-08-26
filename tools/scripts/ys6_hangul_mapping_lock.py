#!/usr/bin/env python3
"""Recover and audit an append-only Ys VI Hangul mapping from a known-good EBOOT."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FONT_OFFSET = 0x13E88C
RECORD_SIZE = 0x1A
GLYPH_SIZE = 24
BASELINE_EBOOT_SHA256 = "9ABBCC83C717259FA6F1791E270A23618E8B34C2254AAB2C301D94FFAA81C0A5"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def bitmap(data: bytes, index: int) -> bytes:
    start = FONT_OFFSET + index * RECORD_SIZE + 2
    return data[start:start + GLYPH_SIZE]


def recover(baseline_eboot: Path, reference_eboot: Path, reference_mapping: Path,
            usage_path: Path, output: Path, report_path: Path) -> dict:
    baseline = baseline_eboot.read_bytes(); reference = reference_eboot.read_bytes()
    if sha(baseline) != BASELINE_EBOOT_SHA256:
        raise ValueError(f"102 baseline EBOOT SHA-256 mismatch: {sha(baseline)}")
    mappings = json.loads(reference_mapping.read_text(encoding="utf-8-sig"))["mappings"]
    usage = json.loads(usage_path.read_text(encoding="utf-8-sig")); usage_by_index = {int(row["font_index"]): row for row in usage["records"]}
    by_bitmap: dict[bytes, list[str]] = defaultdict(list)
    for row in mappings: by_bitmap[bitmap(reference, int(row["font_index"]))].append(row["character"])
    duplicates = {sha(key): value for key, value in by_bitmap.items() if len(value) != 1}
    if duplicates: raise ValueError(f"reference glyph bitmaps are ambiguous: {duplicates}")
    recovered_by_character = {}; audit = []
    for candidate in mappings:
        index = int(candidate["font_index"]); characters = by_bitmap.get(bitmap(baseline, index), [])
        if len(characters) != 1: raise ValueError(f"baseline glyph cannot be identified at font index {index}")
        character = characters[0]; usage_row = usage_by_index[index]
        recovered_by_character[character] = {
            "unicode": f"U+{ord(character):04X}", "character": character,
            "game_code": usage_row["game_code"], "font_index": index,
            "original_character": usage_row["original_character"],
            "original_usage_count": usage_row["usage_count"], "status": "stable_102_baseline",
        }
        audit.append({"character": character, "game_code": usage_row["game_code"], "font_index": index,
                      "bitmap_sha256": sha(bitmap(baseline, index))})
    if len(recovered_by_character) != len(mappings): raise ValueError("recovered mapping character count mismatch")
    recovered = [recovered_by_character[row["character"]] for row in mappings]
    codes = [row["game_code"] for row in recovered]; indices = [row["font_index"] for row in recovered]
    if len(set(codes)) != len(codes) or len(set(indices)) != len(indices): raise ValueError("duplicate recovered code or index")
    document = {"schema_version": 2, "profile": "ULJM-05009", "mapping_revision": 1,
                "baseline": {"issue": 102, "eboot_sha256": sha(baseline)}, "mappings": recovered}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    changed = sum((row["game_code"], row["font_index"]) !=
                  (recovered_by_character[row["character"]]["game_code"], recovered_by_character[row["character"]]["font_index"])
                  for row in mappings)
    report = {"valid": True, "mapping_count": len(recovered), "changed_from_reference_count": changed,
              "baseline_eboot": str(baseline_eboot), "baseline_eboot_sha256": sha(baseline),
              "reference_eboot_sha256": sha(reference), "canonical_mapping": str(output),
              "canonical_mapping_sha256": sha(output.read_bytes()), "records": audit}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_eboot", type=Path); parser.add_argument("reference_eboot", type=Path)
    parser.add_argument("reference_mapping", type=Path); parser.add_argument("usage", type=Path)
    parser.add_argument("output", type=Path); parser.add_argument("report", type=Path); args = parser.parse_args()
    print(json.dumps(recover(args.baseline_eboot, args.reference_eboot, args.reference_mapping,
                             args.usage, args.output, args.report), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
