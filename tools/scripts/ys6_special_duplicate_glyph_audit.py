#!/usr/bin/env python3
"""Audit the issue-114 쩔/코 mapping in a built SPECIAL VERSION ISO."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

try:
    from tools.scripts.ys12_ys2_event_disasm import elf_layout
    from tools.scripts.ys6_idm import parse_idm
    from tools.scripts.ys6_special_font_expand import LEGACY_COUNT, NEW_VADDR, RECORD_SIZE
    from tools.scripts.ys6_special_font_expand_proof_iso import read_iso
    from tools.scripts.ys6_special_font_proof import render_glyph
    from tools.scripts.ys6_special_remaining_idm_preflight import target_rows
except ModuleNotFoundError:
    from ys12_ys2_event_disasm import elf_layout
    from ys6_idm import parse_idm
    from ys6_special_font_expand import LEGACY_COUNT, NEW_VADDR, RECORD_SIZE
    from ys6_special_font_expand_proof_iso import read_iso
    from ys6_special_font_proof import render_glyph
    from ys6_special_remaining_idm_preflight import target_rows


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def audit(args: argparse.Namespace) -> dict:
    mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    mappings = mapping_doc["mappings"]
    selected = {row["character"]: row for row in mappings if row["character"] in {"쩔", "코"}}
    expected = {
        "쩔": {"game_code": "0xF2DB", "font_index": 2304},
        "코": {"game_code": "0x817E", "font_index": 60},
    }
    if {key: {"game_code": row["game_code"], "font_index": int(row["font_index"])}
        for key, row in selected.items()} != expected:
        raise ValueError("issue-114 mapping assignment mismatch")

    base = json.loads(args.base_translations.read_text(encoding="utf-8-sig"))
    remaining = json.loads(args.remaining.read_text(encoding="utf-8-sig"))
    rows = target_rows(base, remaining)
    resources: dict[str, dict] = {}
    for row in rows:
        if not any(character in row["translation"] for character in expected):
            continue
        resources.setdefault(row["target_iso_path"], {})[int(row["target_flat_index"])] = row

    counts = {character: {"string_count": 0, "character_count": 0, "encoded_code_count": 0}
              for character in expected}
    verified_strings = 0
    for path, targets in resources.items():
        payload, _record = read_iso(args.iso, path)
        parsed = parse_idm(payload)
        for index, row in targets.items():
            raw = parsed["strings"][index]["raw"]
            for character, assignment in expected.items():
                occurrences = row["translation"].count(character)
                if not occurrences:
                    continue
                code = int(assignment["game_code"], 16).to_bytes(2, "big")
                actual = raw.count(code)
                if actual != occurrences:
                    raise ValueError(f"encoded code mismatch: {path}#{index} {character}: {actual}/{occurrences}")
                counts[character]["string_count"] += 1
                counts[character]["character_count"] += occurrences
                counts[character]["encoded_code_count"] += actual
            verified_strings += 1

    boot, _record = read_iso(args.iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    segments, _sections = elf_layout(boot)
    segment = next(row for row in segments if row["vaddr"] == NEW_VADDR)
    glyphs = {}
    for character, assignment in expected.items():
        font_index = assignment["font_index"]
        if font_index < LEGACY_COUNT:
            continue
        offset = segment["offset"] + font_index * RECORD_SIZE
        record = boot[offset:offset + RECORD_SIZE]
        code = struct.unpack_from("<H", record)[0]
        bitmap, _preview = render_glyph(character, args.font)
        if code != int(assignment["game_code"], 16) or record[2:] != bitmap:
            raise ValueError(
                f"expanded glyph record mismatch: {character}: "
                f"code=0x{code:04X}/{assignment['game_code']}, "
                f"bitmap={digest(record[2:])}/{digest(bitmap)}, offset=0x{offset:X}"
            )
        glyphs[character] = {
            "font_index": font_index,
            "game_code": assignment["game_code"],
            "record_offset": f"0x{offset:X}",
            "bitmap_sha256": digest(bitmap),
        }

    report = {
        "valid": True,
        "mapping_revision": mapping_doc["mapping_revision"],
        "mapping_count": len(mappings),
        "mapping_code_duplicate_count": len(mappings) - len({row["game_code"] for row in mappings}),
        "verified_string_count": verified_strings,
        "counts": counts,
        "expanded_glyphs": glyphs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("base_translations", type=Path)
    parser.add_argument("remaining", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path, required=True)
    audit(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
