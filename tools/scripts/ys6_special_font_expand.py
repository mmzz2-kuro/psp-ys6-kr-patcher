#!/usr/bin/env python3
"""Expand the Ys VI SPECIAL VERSION embedded font table in a new ELF load segment."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.ys12_ys2_event_disasm import apply_psp_relocations, elf_layout
    from tools.scripts.ys6_special_font_proof import render_glyph
except ModuleNotFoundError:
    from ys12_ys2_event_disasm import apply_psp_relocations, elf_layout
    from ys6_special_font_proof import render_glyph


LEGACY_VISIBLE_OFFSET = 0x15EB2A
INTERNAL_RECORDS = 3
RECORD_SIZE = 30
LEGACY_COUNT = 1774
TABLE_OFFSET = LEGACY_VISIBLE_OFFSET - INTERNAL_RECORDS * RECORD_SIZE
NEW_VADDR = 0x360000
PSP_RELOCATION_PHDR = 0x74
PHDR_SLOT = 0x94
REFERENCE_PAIRS = ((0x2D518, 0x2D520), (0x2D72C, 0x2D730), (0x2D7A8, 0x2D7B0))
COUNT_OFFSETS = (0x2D534, 0x2D744, 0x2D7C4)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def relocation_entries(data: bytes) -> dict[int, int]:
    _segments, sections = elf_layout(data)
    found = {}
    wanted = {offset - 0xC0 for pair in REFERENCE_PAIRS for offset in pair}
    for section in sections:
        for position in range(section["offset"], section["offset"] + section["size"], section["entry_size"]):
            relative, _info = struct.unpack_from("<II", data, position)
            if relative in wanted:
                if relative in found:
                    raise ValueError(f"duplicate relocation for 0x{relative:X}")
                found[relative] = position
    if set(found) != wanted:
        raise ValueError(f"font reference relocation set mismatch: {sorted(set(wanted) - set(found))}")
    return found


def validate_source(data: bytes) -> None:
    if len(data) < TABLE_OFFSET + LEGACY_COUNT * RECORD_SIZE:
        raise ValueError("executable is shorter than the legacy font table")
    if data[LEGACY_VISIBLE_OFFSET:LEGACY_VISIBLE_OFFSET + 2] != b"\x40\x81":
        raise ValueError("legacy visible font signature mismatch")
    phoff = struct.unpack_from("<I", data, 0x1C)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 0x2A)
    if (phoff, phentsize, phnum) != (0x34, 0x20, 3):
        raise ValueError(f"unexpected program header layout: {phoff:#x}/{phentsize}/{phnum}")
    if any(data[PHDR_SLOT:0xC0]):
        raise ValueError("program-header expansion slot is not empty")
    if struct.unpack_from("<I", data, PSP_RELOCATION_PHDR)[0] != 0x700000A0:
        raise ValueError("PSP relocation program header is not at index 2")
    relocated, _counts = apply_psp_relocations(data)
    for hi_offset, lo_offset in REFERENCE_PAIRS:
        hi = struct.unpack_from("<I", relocated, hi_offset)[0] & 0xFFFF
        lo = struct.unpack_from("<I", relocated, lo_offset)[0] & 0xFFFF
        lo = lo - 0x10000 if lo & 0x8000 else lo
        if (hi << 16) + lo != TABLE_OFFSET - 0xC0:
            raise ValueError(f"legacy table reference mismatch at 0x{hi_offset:X}")
    for offset in COUNT_OFFSETS:
        word = struct.unpack_from("<I", data, offset)[0]
        if word >> 26 != 10 or word & 0xFFFF != LEGACY_COUNT:
            raise ValueError(f"legacy font count instruction mismatch at 0x{offset:X}")


def allocate_codes(existing_codes: set[int], count: int) -> list[int]:
    candidates = []
    for lead in range(0xF0, 0xFA):
        for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            code = lead << 8 | trail
            if code not in existing_codes:
                candidates.append(code)
                if len(candidates) == count:
                    return candidates
    raise ValueError("not enough unused Shift-JIS user-defined codes")


def expand(data: bytes, characters: list[str], font: Path) -> tuple[bytes, list[dict], Image.Image, dict]:
    validate_source(data)
    legacy_table = data[TABLE_OFFSET:TABLE_OFFSET + LEGACY_COUNT * RECORD_SIZE]
    existing_codes = {struct.unpack_from("<H", legacy_table, index * RECORD_SIZE)[0]
                      for index in range(LEGACY_COUNT)}
    codes = allocate_codes(existing_codes, len(characters))
    records = bytearray(legacy_table)
    rows = []
    atlas = Image.new("L", (16 * max(1, len(characters)), 14), 0)
    for index, (character, code) in enumerate(zip(characters, codes)):
        bitmap, preview = render_glyph(character, font)
        records.extend(struct.pack("<H", code)); records.extend(bitmap)
        atlas.paste(preview, (index * 16, 0))
        rows.append({"unicode": f"U+{ord(character):04X}", "character": character,
                     "game_code": f"0x{code:04X}", "font_index": LEGACY_COUNT + index,
                     "status": "special_110_expanded_append"})
    output = bytearray(data)
    table_file_offset = align(len(output), 0x40)
    output.extend(bytes(table_file_offset - len(output))); output.extend(records)
    struct.pack_into("<H", output, 0x2C, 4)
    output[PHDR_SLOT:PHDR_SLOT + 0x20] = data[PSP_RELOCATION_PHDR:PSP_RELOCATION_PHDR + 0x20]
    struct.pack_into("<8I", output, PSP_RELOCATION_PHDR, 1, table_file_offset, NEW_VADDR, 0,
                     len(records), len(records), 4, 0x40)
    relocations = relocation_entries(data)
    for hi_offset, lo_offset in REFERENCE_PAIRS:
        hi_word = struct.unpack_from("<I", output, hi_offset)[0]
        lo_word = struct.unpack_from("<I", output, lo_offset)[0]
        struct.pack_into("<I", output, hi_offset, hi_word & 0xFFFF0000)
        struct.pack_into("<I", output, lo_offset, lo_word & 0xFFFF0000)
        for source_offset in (hi_offset, lo_offset):
            relocation = relocations[source_offset - 0xC0]
            relative, info = struct.unpack_from("<II", output, relocation)
            info = (info & ~0x00FF0000) | (2 << 16)
            struct.pack_into("<II", output, relocation, relative, info)
    new_count = LEGACY_COUNT + len(characters)
    if new_count > 0x7FFF:
        raise ValueError("expanded count does not fit slti immediate")
    for offset in COUNT_OFFSETS:
        word = struct.unpack_from("<I", output, offset)[0]
        struct.pack_into("<I", output, offset, (word & 0xFFFF0000) | new_count)
    result = bytes(output)
    relocated, relocation_counts = apply_psp_relocations(result)
    segments, _sections = elf_layout(result)
    if len(segments) != 3 or segments[2]["vaddr"] != NEW_VADDR:
        raise ValueError("expanded load segment was not parsed")
    for hi_offset, lo_offset in REFERENCE_PAIRS:
        hi = struct.unpack_from("<I", relocated, hi_offset)[0] & 0xFFFF
        lo = struct.unpack_from("<I", relocated, lo_offset)[0] & 0xFFFF
        lo = lo - 0x10000 if lo & 0x8000 else lo
        if (hi << 16) + lo != NEW_VADDR:
            raise ValueError("expanded relocated table reference mismatch")
    report = {"input_size": len(data), "output_size": len(result), "input_sha256": sha(data),
              "output_sha256": sha(result), "legacy_table_file_offset": f"0x{TABLE_OFFSET:X}",
              "legacy_count": LEGACY_COUNT, "expanded_count": new_count,
              "new_segment_file_offset": f"0x{table_file_offset:X}",
              "new_segment_vaddr": f"0x{NEW_VADDR:X}", "new_segment_size": len(records),
              "relocation_counts": relocation_counts, "glyphs": rows}
    return result, rows, atlas, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--characters", required=True)
    parser.add_argument("--atlas", type=Path)
    args = parser.parse_args()
    characters = list(dict.fromkeys(args.characters))
    if not 16 <= len(characters) <= 32:
        raise ValueError("minimal proof must append 16 to 32 unique characters")
    mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    existing = {row["character"] for row in mapping_doc["mappings"]}
    if existing.intersection(characters):
        raise ValueError("proof characters already exist in the mapping")
    result, rows, atlas, report = expand(args.executable.read_bytes(), characters, args.font)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(result)
    report["mapping_revision"] = int(mapping_doc.get("mapping_revision", 3)) + 1
    report["mapping_count"] = len(mapping_doc["mappings"]) + len(rows)
    report["mappings"] = [*mapping_doc["mappings"], *rows]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.atlas:
        args.atlas.parent.mkdir(parents=True, exist_ok=True)
        atlas.resize((atlas.width * 6, atlas.height * 6), Image.Resampling.NEAREST).save(args.atlas)
    print(json.dumps({key: value for key, value in report.items() if key not in ("mappings", "glyphs")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
