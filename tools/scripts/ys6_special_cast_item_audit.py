#!/usr/bin/env python3
"""Audit issue-116 cast/item resources and appended glyphs in a built ISO."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

try:
    from tools.scripts.ys12_ys2_event_disasm import elf_layout
    from tools.scripts.ys6_arc import parse_archive
    from tools.scripts.ys6_castinfo import NAME_SIZE, parse_records as parse_cast
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_special_cast_item import CAST_ENTRY, CAST_PATH, INIT_PATH, ITEM_ENTRY, ITEM_PATH, unpack
    from tools.scripts.ys6_special_font_expand import NEW_VADDR, RECORD_SIZE
    from tools.scripts.ys6_special_font_expand_proof_iso import read_iso
    from tools.scripts.ys6_special_font_proof import render_glyph
    from tools.scripts.ys6_special_nondialogue_audit import parse_items
except ModuleNotFoundError:
    from ys12_ys2_event_disasm import elf_layout
    from ys6_arc import parse_archive
    from ys6_castinfo import NAME_SIZE, parse_records as parse_cast
    from ys6_hangul_codec import encode_translation
    from ys6_special_cast_item import CAST_ENTRY, CAST_PATH, INIT_PATH, ITEM_ENTRY, ITEM_PATH, unpack
    from ys6_special_font_expand import NEW_VADDR, RECORD_SIZE
    from ys6_special_font_expand_proof_iso import read_iso
    from ys6_special_font_proof import render_glyph
    from ys6_special_nondialogue_audit import parse_items


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def payloads(iso: Path) -> tuple[bytes, bytes]:
    cast = unpack(read_iso(iso, CAST_PATH)[0], "cast")
    items = unpack(read_iso(iso, ITEM_PATH)[0], "items")
    init = read_iso(iso, INIT_PATH)[0]; entries = parse_archive(init)
    cast_entry = next(row for row in entries if (row.index, row.name) == CAST_ENTRY)
    item_entry = next(row for row in entries if (row.index, row.name) == ITEM_ENTRY)
    if unpack(init[cast_entry.offset:cast_entry.offset + cast_entry.size], "runtime cast") != cast:
        raise ValueError("cast standalone/runtime mismatch")
    if unpack(init[item_entry.offset:item_entry.offset + item_entry.size], "runtime items") != items:
        raise ValueError("item standalone/runtime mismatch")
    return cast, items


def audit(args: argparse.Namespace) -> dict:
    workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig")); mapping = mapping_doc["mappings"]
    original_cast, original_items = payloads(args.original_iso)
    output_cast, output_items = payloads(args.output_iso)
    cast_records = {row.identifier: row for row in parse_cast(output_cast)}
    for row in workspace["cast"]:
        target = cast_records[row["identifier"]]
        encoded = encode_translation(row["translation"], mapping)
        field = output_cast[target.name_offset:target.name_offset + NAME_SIZE]
        if field != encoded + bytes(NAME_SIZE - len(encoded)):
            raise ValueError(f"cast encoding mismatch: {row['identifier']}")
    output_item_rows = {row["resource_id"]: row for row in parse_items(output_items)}
    original_item_rows = {row["resource_id"]: row for row in parse_items(original_items)}
    for row in workspace["items"]:
        target = output_item_rows[row["resource_id"]]; offset = 16 + target["index"] * 184
        name = encode_translation(row["translation_name"], mapping)
        description = encode_translation(row["translation_description"].replace("\n", "\r\n"), mapping)
        if output_items[offset:offset + 32] != name + bytes(32 - len(name)):
            raise ValueError(f"item name mismatch: {row['resource_id']}")
        if output_items[offset + 76:offset + 184] != description + bytes(108 - len(description)):
            raise ValueError(f"item description mismatch: {row['resource_id']}")
        if target["metadata_sha256"] != original_item_rows[row["resource_id"]]["metadata_sha256"]:
            raise ValueError(f"item metadata mismatch: {row['resource_id']}")
    for row in workspace["excluded_items"]:
        resource_id = row["resource_id"]
        if output_item_rows[resource_id]["record_sha256"] != original_item_rows[resource_id]["record_sha256"]:
            raise ValueError(f"excluded item changed: {resource_id}")

    boot = read_iso(args.output_iso, "PSP_GAME/SYSDIR/BOOT.BIN")[0]
    segments, _sections = elf_layout(boot); segment = next(row for row in segments if row["vaddr"] == NEW_VADDR)
    glyph_rows = [row for row in mapping if row.get("status") == "special_116_cast_item_append"]
    glyphs = []
    for row in glyph_rows:
        offset = segment["offset"] + int(row["font_index"]) * RECORD_SIZE
        record = boot[offset:offset + RECORD_SIZE]; bitmap, _preview = render_glyph(row["character"], args.font)
        if struct.unpack_from("<H", record)[0] != int(row["game_code"], 0) or record[2:] != bitmap:
            raise ValueError(f"glyph mismatch: {row['character']}")
        glyphs.append({"character": row["character"], "game_code": row["game_code"],
                       "font_index": row["font_index"], "bitmap_sha256": sha(bitmap)})
    report = {"valid": True, "mapping_revision": mapping_doc["mapping_revision"],
              "mapping_count": len(mapping), "cast_verified_count": len(workspace["cast"]),
              "item_verified_count": len(workspace["items"]),
              "excluded_item_preserved_count": len(workspace["excluded_items"]),
              "standalone_runtime_payload_pairs_verified": 2, "glyph_verified_count": len(glyphs),
              "glyphs": glyphs, "cast_payload_sha256": sha(output_cast), "item_payload_sha256": sha(output_items)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_iso", type=Path); parser.add_argument("output_iso", type=Path)
    parser.add_argument("workspace", type=Path); parser.add_argument("mapping", type=Path)
    parser.add_argument("report", type=Path); parser.add_argument("--font", type=Path, required=True)
    audit(parser.parse_args()); return 0


if __name__ == "__main__": raise SystemExit(main())
