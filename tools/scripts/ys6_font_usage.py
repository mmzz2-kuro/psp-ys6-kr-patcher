#!/usr/bin/env python3
"""Inventory Ys VI font records and CP932 usage in the extracted XSO catalog."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_font_table import DEFAULT_COUNT, DEFAULT_OFFSET, parse_table
except ModuleNotFoundError:
    from ys6_font_table import DEFAULT_COUNT, DEFAULT_OFFSET, parse_table


def iter_cp932_codes(data: bytes):
    index = 0
    while index < len(data):
        first = data[index]
        if (0x81 <= first <= 0x9F) or (0xE0 <= first <= 0xFC):
            if index + 1 >= len(data):
                raise ValueError(f"truncated CP932 lead byte at offset {index}")
            yield (first << 8) | data[index + 1]
            index += 2
        else:
            index += 1


def load_usage(catalog_path: Path) -> tuple[Counter[int], int]:
    document = json.loads(catalog_path.read_text(encoding="utf-8"))
    usage: Counter[int] = Counter()
    strings = document.get("strings")
    if not isinstance(strings, list):
        raise ValueError("catalog does not contain a strings list")
    for item in strings:
        raw_hex = item.get("raw_hex")
        if not isinstance(raw_hex, str):
            raise ValueError("catalog string is missing raw_hex")
        raw = bytes.fromhex(raw_hex)
        usage.update(iter_cp932_codes(raw))
    return usage, len(strings)


def decode_code(code: int) -> str:
    try:
        return code.to_bytes(2, "big").decode("cp932")
    except UnicodeDecodeError:
        return ""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def build_inventory(eboot_data: bytes, catalog_path: Path) -> dict:
    glyphs = parse_table(eboot_data, DEFAULT_OFFSET, DEFAULT_COUNT)
    usage, string_count = load_usage(catalog_path)
    code_counts = Counter(glyph.code for glyph in glyphs)
    records = []
    for glyph in glyphs:
        count = usage[glyph.code]
        if glyph.code == 0x98FC:
            status = "poc_reserved"
        elif count:
            status = "protected_used"
        else:
            status = "unused_candidate"
        records.append(
            {
                "font_index": glyph.index,
                "game_code": f"0x{glyph.code:04X}",
                "original_character": decode_code(glyph.code),
                "usage_count": count,
                "status": status,
                "duplicate_code_count": code_counts[glyph.code],
                "blank_glyph": not any(glyph.bitmap),
                "bitmap_sha256": sha256(glyph.bitmap),
            }
        )
    table_codes = set(code_counts)
    missing_used = sorted(code for code in usage if code not in table_codes)
    status_counts = Counter(record["status"] for record in records)
    return {
        "schema_version": 1,
        "source": {
            "eboot_sha256": sha256(eboot_data),
            "catalog": str(catalog_path),
            "catalog_string_count": string_count,
        },
        "summary": {
            "font_record_count": len(glyphs),
            "unique_font_code_count": len(code_counts),
            "duplicate_font_code_count": sum(1 for value in code_counts.values() if value > 1),
            "used_double_byte_code_count": len(usage),
            "used_double_byte_occurrences": sum(usage.values()),
            "used_codes_missing_from_font": [f"0x{code:04X}" for code in missing_used],
            "status_counts": dict(sorted(status_counts.items())),
        },
        "records": records,
    }


def write_csv(document: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "font_index",
        "game_code",
        "original_character",
        "usage_count",
        "status",
        "duplicate_code_count",
        "blank_glyph",
        "bitmap_sha256",
    )
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(document["records"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eboot", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()

    document = build_inventory(args.eboot.read_bytes(), args.catalog)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(document, args.output_csv)
    print(json.dumps(document["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
