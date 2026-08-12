#!/usr/bin/env python3
"""Allocate and use deterministic two-byte Ys VI codes for Korean characters."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def unique_characters(text: str) -> list[str]:
    return list(dict.fromkeys(character for character in text if not character.isspace()))


def allocate_mapping(usage_document: dict, text: str) -> list[dict]:
    characters = unique_characters(text)
    records = usage_document["records"]
    by_code = {int(record["game_code"], 0): record for record in records}
    reserved = {"한": 0x98FC}
    mapping: list[dict] = []
    assigned_codes: set[int] = set()

    for character in characters:
        if character not in reserved:
            continue
        code = reserved[character]
        record = by_code.get(code)
        if record is None or record["duplicate_code_count"] != 1:
            raise ValueError(f"reserved code 0x{code:04X} is unavailable")
        mapping.append(_mapping_row(character, record, "poc_reserved"))
        assigned_codes.add(code)

    candidates = [
        record
        for record in records
        if record["status"] == "unused_candidate"
        and record["duplicate_code_count"] == 1
        and record["original_character"]
        and int(record["game_code"], 0) not in assigned_codes
    ]
    candidates.sort(key=lambda record: record["font_index"], reverse=True)
    remaining = [character for character in characters if character not in reserved]
    if len(candidates) < len(remaining):
        raise ValueError(f"not enough safe slots: need={len(remaining)}, have={len(candidates)}")
    for character, record in zip(remaining, candidates):
        mapping.append(_mapping_row(character, record, "poc_assigned"))
    order = {character: index for index, character in enumerate(characters)}
    mapping.sort(key=lambda row: order[row["character"]])
    return mapping


def _mapping_row(character: str, record: dict, status: str) -> dict:
    return {
        "unicode": f"U+{ord(character):04X}",
        "character": character,
        "game_code": record["game_code"],
        "font_index": record["font_index"],
        "original_character": record["original_character"],
        "original_usage_count": record["usage_count"],
        "status": status,
    }


def encode_text(text: str, mapping: list[dict]) -> bytes:
    codes = {row["character"]: int(row["game_code"], 0) for row in mapping}
    output = bytearray()
    for character in text:
        if character == " ":
            output.extend("　".encode("cp932"))
        elif character in codes:
            output.extend(codes[character].to_bytes(2, "big"))
        else:
            raise ValueError(f"unmapped character: {character!r}")
    return bytes(output)


FULLWIDTH_PUNCTUATION = {",": "，", ".": "．", "?": "？", "!": "！"}
GAME_CP932_PUNCTUATION = set(FULLWIDTH_PUNCTUATION.values()) | {"…", "　"}


def normalize_game_punctuation(text: str) -> str:
    normalized = re.sub(r"\.{2,}", "……", text)
    normalized = "".join(FULLWIDTH_PUNCTUATION.get(character, character) for character in normalized)
    normalized = re.sub(r"([，．？！…]) +", r"\1", normalized)
    normalized = re.sub(r"(?<=[가-힣])(?=……)", " ", normalized)
    return normalized


def encode_translation(text: str, mapping: list[dict]) -> bytes:
    text = normalize_game_punctuation(text)
    codes = {row["character"]: int(row["game_code"], 0) for row in mapping}
    output = bytearray()
    for character in text:
        if character in codes:
            output.extend(codes[character].to_bytes(2, "big"))
        elif ord(character) < 0x80:
            output.append(ord(character))
        elif character in GAME_CP932_PUNCTUATION:
            output.extend(character.encode("cp932"))
        else:
            raise ValueError(f"unmapped character: {character!r}")
    return bytes(output)


def extend_mapping(usage_document: dict, existing: list[dict], text: str) -> list[dict]:
    result = [dict(row) for row in existing]
    mapped_characters = {row["character"] for row in result}
    assigned_codes = {int(row["game_code"], 0) for row in result}
    needed = [
        character for character in unique_characters(text)
        if ord(character) >= 0x80 and character not in mapped_characters
    ]
    candidates = [
        record for record in usage_document["records"]
        if record["status"] == "unused_candidate"
        and record["duplicate_code_count"] == 1
        and record["original_character"]
        and int(record["game_code"], 0) not in assigned_codes
    ]
    candidates.sort(key=lambda record: record["font_index"], reverse=True)
    if len(candidates) < len(needed):
        raise ValueError(f"not enough safe slots: need={len(needed)}, have={len(candidates)}")
    for character, record in zip(needed, candidates):
        result.append(_mapping_row(character, record, "translation_assigned"))
    return result


def write_mapping(mapping: list[dict], json_path: Path, csv_path: Path) -> None:
    document = {"schema_version": 1, "mappings": mapping}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(mapping[0]))
        writer.writeheader()
        writer.writerows(mapping)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("usage_json", type=Path)
    parser.add_argument("text")
    parser.add_argument("output_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--existing", type=Path)
    args = parser.parse_args()
    usage = json.loads(args.usage_json.read_text(encoding="utf-8"))
    if args.existing:
        existing = json.loads(args.existing.read_text(encoding="utf-8-sig"))["mappings"]
        mapping = extend_mapping(usage, existing, args.text)
    else:
        mapping = allocate_mapping(usage, args.text)
    write_mapping(mapping, args.output_json, args.output_csv)
    encoded = encode_translation(args.text, mapping) if args.existing else encode_text(args.text, mapping)
    print(json.dumps({"characters": len(mapping), "encoded_hex": encoded.hex().upper()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
