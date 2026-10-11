#!/usr/bin/env python3
"""Allocate safe legacy-font aliases for SPECIAL VERSION system messages."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

try:
    from tools.scripts.ys6_special_font_expand import (
        LEGACY_COUNT,
        RECORD_SIZE,
        TABLE_OFFSET,
    )
    from tools.scripts.ys6_system_message_workspace import encode_system_translation
except ModuleNotFoundError:
    from ys6_special_font_expand import LEGACY_COUNT, RECORD_SIZE, TABLE_OFFSET
    from ys6_system_message_workspace import encode_system_translation


def required_alias_characters(workspace: dict, mapping: list[dict]) -> list[str]:
    result = []
    for row in workspace["records"]:
        if row.get("status") not in {"override", "draft"} or not row.get("translation"):
            continue
        for character in row["translation"]:
            if character in result:
                continue
            try:
                encode_system_translation(character, mapping)
            except ValueError:
                result.append(character)
    return result


def build(args: argparse.Namespace) -> dict:
    executable = args.seed_boot.read_bytes()
    mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    mapping = mapping_doc["mappings"]
    workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    protected_text = args.audit_report.read_text(encoding="utf-8-sig")
    for path in args.protected:
        protected_text += path.read_text(encoding="utf-8-sig", errors="ignore")
    required = required_alias_characters(workspace, mapping)
    previous = json.loads(args.previous.read_text(encoding="utf-8-sig")) if args.previous.exists() else {"aliases": []}
    preserve = set(args.preserve_characters)
    previous_by_character = {
        row["character"]: row for row in previous["aliases"] if row["character"] in preserve
    }
    canonical_codes = {int(row["game_code"], 0) for row in mapping}
    canonical_indices = {int(row["font_index"]) for row in mapping if int(row["font_index"]) < LEGACY_COUNT}

    candidates = []
    for record_index in range(3, LEGACY_COUNT):
        font_index = record_index - 3
        code = struct.unpack_from("<H", executable, TABLE_OFFSET + record_index * RECORD_SIZE)[0]
        if code in canonical_codes or font_index in canonical_indices:
            continue
        raw = code.to_bytes(2, "big")
        try:
            replaced = raw.decode("cp932")
            euc = replaced.encode("euc_jp")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
        if len(replaced) != 1 or len(euc) != 2 or replaced in protected_text:
            continue
        # Prefer obscure kanji over punctuation and Latin/Japanese syllabaries.
        priority = 0 if "\u4e00" <= replaced <= "\u9fff" else 1
        candidates.append((priority, -record_index, code, font_index, record_index, replaced, euc))
    candidates.sort()

    aliases = []
    preserved_codes = {int(row["game_code"], 0) for row in previous_by_character.values()}
    preserved_indices = {int(row["font_index"]) for row in previous_by_character.values()}
    if len(preserved_codes) != len(previous_by_character) or len(preserved_indices) != len(previous_by_character):
        raise ValueError("duplicate preserved system alias")
    occupied_codes = set(canonical_codes) | preserved_codes
    occupied_indices = set(canonical_indices) | preserved_indices
    for character in required:
        old = previous_by_character.get(character)
        if old:
            code = int(old["game_code"], 0)
            font_index = int(old["font_index"])
            record_index = int(old["record_index"])
            actual = struct.unpack_from("<H", executable, TABLE_OFFSET + record_index * RECORD_SIZE)[0]
            if actual != code or code in canonical_codes or font_index in canonical_indices:
                raise ValueError(f"invalid preserved system alias: {character}")
            row = dict(old)
            row["status"] = "validated"
        else:
            selected = next(
                (item for item in candidates if item[2] not in occupied_codes and item[3] not in occupied_indices),
                None,
            )
            if selected is None:
                raise ValueError("not enough protected legacy glyph aliases")
            _priority, _negative_record, code, font_index, record_index, replaced, euc = selected
            row = {
                "character": character,
                "game_code": f"0x{code:04X}",
                "font_index": font_index,
                "record_index": record_index,
                "replaced_character": replaced,
                "euc_bytes_hex": euc.hex().upper(),
                "status": "validated",
            }
        occupied_codes.add(int(row["game_code"], 0))
        occupied_indices.add(int(row["font_index"]))
        aliases.append(row)

    output = {
        "schema_version": 2,
        "profile": "ULJM-05155",
        "purpose": "117번 시스템 메시지 전용 글리프 별칭",
        "selection_policy": "115 audit source characters protected; obscure unused legacy kanji preferred",
        "summary": {
            "required_character_count": len(required),
            "alias_count": len(aliases),
            "candidate_count": len(candidates),
            "preserved_proof_alias_count": sum(character in previous_by_character for character in required),
        },
        "required_characters": "".join(required),
        "aliases": aliases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "valid": True,
        **output["summary"],
        "required_characters": output["required_characters"],
        "replaced_characters": "".join(row["replaced_character"] for row in aliases),
        "aliases": aliases,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed_boot", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("audit_report", type=Path)
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--protected", type=Path, action="append", default=[])
    parser.add_argument("--preserve-characters", default="점검좌")
    report = build(parser.parse_args())
    print(json.dumps({key: value for key, value in report.items() if key != "aliases"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
