#!/usr/bin/env python3
"""Preflight the canonical SPECIAL font mapping and all translated IDM resources."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE
    from tools.scripts.ys6_arc import parse_archive, replace_file
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_idm import parse_idm, rebuild_idm, sha256
    from tools.scripts.ys6_special_font_expand import LEGACY_COUNT, RECORD_SIZE, expand
    from tools.scripts.ys6_special_font_proof import render_glyph
    from tools.scripts.ys6_special_font_expand_proof_iso import (
        append_extent, read_iso, update_volume_space, write_fixed,
    )
    from tools.scripts.ys6_special_cast_item import prepare as prepare_cast_items
    from tools.scripts.ys6_system_message_workspace import patch_overrides as patch_system_messages
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE
    from ys6_arc import parse_archive, replace_file
    from ys6_hangul_codec import encode_translation
    from ys6_idm import parse_idm, rebuild_idm, sha256
    from ys6_special_font_expand import LEGACY_COUNT, RECORD_SIZE, expand
    from ys6_special_font_proof import render_glyph
    from ys6_special_font_expand_proof_iso import append_extent, read_iso, update_volume_space, write_fixed
    from ys6_special_cast_item import prepare as prepare_cast_items
    from ys6_system_message_workspace import patch_overrides as patch_system_messages


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def duplicate_values(rows: list[dict], key: str) -> list[dict]:
    grouped: dict[object, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return [
        {key: value, "characters": [row["character"] for row in matches]}
        for value, matches in grouped.items() if len(matches) > 1
    ]


def target_rows(base_doc: dict, remaining_doc: dict) -> list[dict]:
    rows = [
        {
            "target_iso_path": row["target_iso_path"],
            "target_flat_index": int(row["target_flat_index"]),
            "translation": row["translation"],
            "source": "issue_111",
        }
        for row in base_doc["records"]
    ]
    for unit in remaining_doc["units"]:
        if unit["status"] not in ("reused", "translated") or not unit.get("translation"):
            raise ValueError(f"unfinished remaining IDM unit: {unit['unit_id']}")
        for occurrence in unit["occurrences"]:
            rows.append(
                {
                    "target_iso_path": occurrence["target_iso_path"],
                    "target_flat_index": int(occurrence["target_flat_index"]),
                    "translation": unit["translation"],
                    "source": unit["unit_id"],
                }
            )
    return rows


def save_new_atlas(raw_atlas: Image.Image, start: int, count: int, output: Path) -> None:
    columns = 18
    rows = max(1, math.ceil(count / columns))
    tiled = Image.new("L", (columns * 16, rows * 14), 0)
    for index in range(count):
        source_index = start + index
        tile = raw_atlas.crop((source_index * 16, 0, source_index * 16 + 16, 14))
        tiled.paste(tile, ((index % columns) * 16, (index // columns) * 14))
    tiled.resize((tiled.width * 4, tiled.height * 4), Image.Resampling.NEAREST).save(output)


def apply_system_aliases(executable: bytes, expand_report: dict, aliases: list[dict],
                         font: Path) -> tuple[bytes, list[dict]]:
    output = bytearray(executable)
    table_offset = int(expand_report["new_segment_file_offset"], 16)
    applied = []
    for row in aliases:
        index = int(row["font_index"])
        record_index = int(row["record_index"])
        if not 0 <= record_index < LEGACY_COUNT:
            raise ValueError(f"system alias is not a legacy font record: {record_index}")
        offset = table_offset + record_index * RECORD_SIZE
        code = int.from_bytes(output[offset:offset + 2], "little")
        expected = int(row["game_code"], 0)
        if code != expected:
            raise ValueError(
                f"system alias source code mismatch: {row['character']} "
                f"0x{code:04X}/0x{expected:04X}"
            )
        bitmap, _preview = render_glyph(row["character"], font)
        output[offset + 2:offset + RECORD_SIZE] = bitmap
        applied.append({
            "character": row["character"], "game_code": row["game_code"],
            "font_index": index, "record_index": record_index,
            "record_offset": f"0x{offset:X}",
        })
    return bytes(output), applied


def preflight(args: argparse.Namespace) -> dict:
    args.work.mkdir(parents=True, exist_ok=True)
    mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    base_doc = json.loads(args.base_translations.read_text(encoding="utf-8-sig"))
    remaining_doc = json.loads(args.remaining.read_text(encoding="utf-8-sig"))
    runtime_doc = json.loads(args.runtime_map.read_text(encoding="utf-8-sig"))
    canonical_mapping = mapping_doc["mappings"]
    mapping_revision = int(mapping_doc["mapping_revision"])
    if mapping_revision != 7 or len(canonical_mapping) != 975:
        raise ValueError("issue-116 canonical mapping revision/count mismatch")
    for key in ("character", "game_code", "font_index"):
        duplicates = duplicate_values(canonical_mapping, key)
        if duplicates:
            raise ValueError(f"duplicate canonical mapping {key}: {duplicates}")

    rows = target_rows(base_doc, remaining_doc)
    if len(base_doc["records"]) != 4127 or len(rows) != 6156:
        raise ValueError(f"translation assignment count mismatch: {len(rows)}")
    by_target: dict[tuple[str, int], dict] = {}
    for row in rows:
        key = row["target_iso_path"], row["target_flat_index"]
        previous = by_target.get(key)
        if previous and previous["translation"] != row["translation"]:
            raise ValueError(f"shared target translation conflict: {key}: {previous['source']} vs {row['source']}")
        by_target[key] = row

    mapped = {row["character"] for row in canonical_mapping}
    needed = sorted(
        {character for row in rows for character in row["translation"]
         if "가" <= character <= "힣" and character not in mapped},
        key=ord,
    )
    if needed:
        raise ValueError(f"canonical mapping is missing translated Hangul: {''.join(needed)}")
    expanded_mapping = sorted(
        (row for row in canonical_mapping if int(row["font_index"]) >= LEGACY_COUNT),
        key=lambda row: int(row["font_index"]),
    )
    expected_indices = list(range(LEGACY_COUNT, LEGACY_COUNT + len(expanded_mapping)))
    if [int(row["font_index"]) for row in expanded_mapping] != expected_indices:
        raise ValueError("canonical expanded font indices are not contiguous")
    all_expanded_characters = [row["character"] for row in expanded_mapping]
    iso_boot, boot_record = read_iso(args.iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    iso_eboot, eboot_record = read_iso(args.iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    boot = args.seed_boot.read_bytes() if getattr(args, "seed_boot", None) else iso_boot
    eboot = args.seed_eboot.read_bytes() if getattr(args, "seed_eboot", None) else iso_eboot
    expanded_boot, generated_rows, raw_atlas, boot_report = expand(boot, all_expanded_characters, args.font)
    expanded_eboot, generated_eboot_rows, _unused, eboot_report = expand(eboot, all_expanded_characters, args.font)
    if generated_rows != generated_eboot_rows:
        raise ValueError("BOOT/EBOOT expanded mapping mismatch")
    for index, old in enumerate(expanded_mapping):
        generated = generated_rows[index]
        for key in ("character", "game_code", "font_index"):
            if old[key] != generated[key]:
                raise ValueError(f"canonical expanded mapping mismatch at font index {old['font_index']}: {key}")
    alias_doc = json.loads(args.system_aliases.read_text(encoding="utf-8-sig"))
    aliases = alias_doc["aliases"]
    alias_characters = [row["character"] for row in aliases]
    if len(alias_characters) != len(set(alias_characters)):
        raise ValueError("duplicate system alias character")
    canonical_indices = {int(row["font_index"]) for row in canonical_mapping}
    if canonical_indices.intersection(int(row["font_index"]) for row in aliases):
        raise ValueError("system alias overwrites a canonical mapped font index")
    expanded_boot, boot_alias_rows = apply_system_aliases(
        expanded_boot, boot_report, aliases, args.font
    )
    expanded_eboot, eboot_alias_rows = apply_system_aliases(
        expanded_eboot, eboot_report, aliases, args.font
    )
    comparable = lambda rows: [
        {key: value for key, value in row.items() if key != "record_offset"} for row in rows
    ]
    if comparable(boot_alias_rows) != comparable(eboot_alias_rows):
        raise ValueError("BOOT/EBOOT system glyph alias mismatch")
    system_mapping = [*canonical_mapping, *aliases]
    system_workspace = json.loads(args.system_messages.read_text(encoding="utf-8-sig"))
    expanded_boot, system_boot_rows = patch_system_messages(
        expanded_boot, system_workspace, system_mapping
    )
    expanded_eboot, system_eboot_rows = patch_system_messages(
        expanded_eboot, system_workspace, system_mapping
    )
    if system_boot_rows != system_eboot_rows:
        raise ValueError("BOOT/EBOOT system-message patch mismatch")
    mapping_path = args.work / "hangul-mapping.json"
    mapping_path.write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.work / "BOOT.BIN").write_bytes(expanded_boot)
    (args.work / "EBOOT.BIN").write_bytes(expanded_eboot)
    save_new_atlas(raw_atlas, len(expanded_mapping) - 11, 11, args.work / "new-glyph-atlas.png")

    changes: dict[str, dict[int, bytes]] = defaultdict(dict)
    for (path, index), row in by_target.items():
        changes[path][index] = encode_translation(row["translation"], canonical_mapping)
    runtime_by_path = {row["iso_path"]: row for row in runtime_doc["resources"]}
    resource_reports = []
    overflow = []
    archive_cache: dict[str, tuple[bytes, list]] = {}
    archive_records = {}
    archive_outputs = {}
    standalone_outputs = {}
    standalone_records = {}
    runtime_copy_count = 0
    for path, replacements in sorted(changes.items()):
        original, record = read_iso(args.iso, path)
        output = rebuild_idm(parse_idm(original), replacements)
        standalone_outputs[path] = output
        standalone_records[path] = record
        allocated = math.ceil(len(original) / SECTOR_SIZE) * SECTOR_SIZE
        if len(output) > allocated:
            overflow.append({"kind": "standalone", "path": path, "size": len(output), "allocated": allocated})
        copies = runtime_by_path[path]["copies"]
        copy_free = []
        for copy in copies:
            archive_path = copy["archive_path"]
            if archive_path not in archive_cache:
                archive, archive_record = read_iso(args.iso, archive_path)
                archive_cache[archive_path] = archive, parse_archive(archive)
                archive_records[archive_path] = archive_record
                archive_outputs[archive_path] = archive
            archive, entries = archive_cache[archive_path]
            entry = next((item for item in entries if item.index == int(copy["entry_index"])
                          and item.name == copy["entry_name"]), None)
            if entry is None:
                raise ValueError(f"runtime IDM entry missing: {archive_path}#{copy['entry_index']}")
            current = archive[entry.offset:entry.offset + entry.size]
            if current != original:
                raise ValueError(f"runtime IDM differs from standalone: {archive_path}#{entry.index}")
            free = entry.allocated_size - len(output)
            copy_free.append(free)
            if free < 0:
                overflow.append({"kind": "archive", "path": archive_path, "entry_index": entry.index,
                                 "resource": path, "size": len(output), "allocated": entry.allocated_size})
            archive_outputs[archive_path] = replace_file(archive_outputs[archive_path], entry, output)
            runtime_copy_count += 1
        resource_reports.append(
            {
                "iso_path": path,
                "translation_count": len(replacements),
                "runtime_copy_count": len(copies),
                "original_size": len(original),
                "output_size": len(output),
                "standalone_allocated_size": allocated,
                "standalone_free_bytes": allocated - len(output),
                "minimum_runtime_free_bytes": min(copy_free) if copy_free else None,
                "output_sha256": sha256(output),
            }
        )
    tightest = sorted(resource_reports, key=lambda row: min(
        row["standalone_free_bytes"],
        row["minimum_runtime_free_bytes"] if row["minimum_runtime_free_bytes"] is not None else row["standalone_free_bytes"],
    ))[:10]
    s4010 = next(row for row in resource_reports if row["iso_path"].endswith("/s_4010/s_scene.idm"))
    cast_item_workspace = json.loads(args.cast_item_workspace.read_text(encoding="utf-8-sig"))
    cast_item = prepare_cast_items(args.iso, cast_item_workspace, canonical_mapping,
                                   args.work / "cast-item")
    report = {
        "valid": not overflow,
        "base_iso_sha256": file_sha(args.iso),
        "base_mapping_sha256": file_sha(args.mapping),
        "remaining_translation_sha256": file_sha(args.remaining),
        "mapping_revision": mapping_revision,
        "preserved_mapping_count": 964,
        "new_glyph_count": 11,
        "new_characters": "랴쉐겸듬똬롱링벅볍뿜클",
        "mapping_count": len(canonical_mapping),
        "mapping_code_duplicates": [],
        "new_code_collision_count": 0,
        "new_font_index_collision_count": 0,
        "font_table_count": LEGACY_COUNT + len(generated_rows),
        "base_translation_count": len(base_doc["records"]),
        "remaining_assignment_count": len(rows) - len(base_doc["records"]),
        "total_translation_count": len(by_target),
        "idm_resource_count": len(resource_reports),
        "runtime_copy_count": runtime_copy_count,
        "archive_count": len(archive_cache),
        "overflow_count": len(overflow),
        "overflows": overflow,
        "s4010": s4010,
        "tightest_resources": tightest,
        "boot": {key: boot_report[key] for key in ("expanded_count", "new_segment_file_offset", "new_segment_vaddr", "new_segment_size")},
        "eboot": {key: eboot_report[key] for key in ("expanded_count", "new_segment_file_offset", "new_segment_vaddr", "new_segment_size")},
        "resources": resource_reports,
        "cast_items": cast_item["report"],
        "system_messages": {
            "record_count": len(system_workspace["records"]),
            "override_count": len(system_boot_rows),
            "draft_count": sum(row["status"] == "draft" for row in system_workspace["records"]),
            "untranslated_count": sum(row["status"] == "untranslated" for row in system_workspace["records"]),
            "rows": system_boot_rows,
            "glyph_aliases": boot_alias_rows,
        },
    }
    if args.output and not overflow:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists() and not args.overwrite:
            raise FileExistsError(args.output)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        if temporary.exists():
            temporary.unlink()
        shutil.copyfile(args.iso, temporary)
        try:
            with temporary.open("r+b") as handle:
                for path in sorted(standalone_outputs):
                    write_fixed(handle, standalone_records[path], standalone_outputs[path])
                for path in sorted(archive_outputs):
                    write_fixed(handle, archive_records[path], archive_outputs[path])
                for key in ("cast", "items", "init"):
                    write_fixed(handle, cast_item["records"][key], cast_item["paths"][key].read_bytes())
                boot_extent = append_extent(handle, boot_record, expanded_boot)
                eboot_extent = append_extent(handle, eboot_record, expanded_eboot)
                volume_sectors = update_volume_space(handle)
            temporary.replace(args.output)
        except Exception:
            if temporary.exists():
                temporary.unlink()
            raise
        reread_boot, reread_boot_record = read_iso(args.output, "PSP_GAME/SYSDIR/BOOT.BIN")
        reread_eboot, reread_eboot_record = read_iso(args.output, "PSP_GAME/SYSDIR/EBOOT.BIN")
        if reread_boot != expanded_boot or reread_eboot != expanded_eboot:
            raise ValueError("expanded executable ISO re-extraction mismatch")
        for key in ("cast", "items", "init"):
            internal_path = {"cast": "PSP_GAME/USRDIR/data/misc/castinfo.dat.z",
                             "items": "PSP_GAME/USRDIR/data/misc/invinfo.dat.z",
                             "init": "PSP_GAME/USRDIR/data/arc/init.bin"}[key]
            actual, _record = read_iso(args.output, internal_path)
            if actual != cast_item["paths"][key].read_bytes():
                raise ValueError(f"cast/item ISO re-extraction mismatch: {internal_path}")
        verified_translations = 0
        verified_runtime_copies = 0
        for path, expected in standalone_outputs.items():
            actual, _record = read_iso(args.output, path)
            if actual != expected:
                raise ValueError(f"standalone IDM ISO re-extraction mismatch: {path}")
            parsed = parse_idm(actual)
            for index, encoded in changes[path].items():
                if parsed["strings"][index]["raw"] != encoded:
                    raise ValueError(f"translated IDM byte mismatch: {path}#{index}")
                verified_translations += 1
            for copy in runtime_by_path[path]["copies"]:
                archive_path = copy["archive_path"]
                archive, _archive_record = read_iso(args.output, archive_path)
                entry = next(item for item in parse_archive(archive)
                             if item.index == int(copy["entry_index"]) and item.name == copy["entry_name"])
                if archive[entry.offset:entry.offset + entry.size] != expected:
                    raise ValueError(f"runtime IDM ISO re-extraction mismatch: {archive_path}#{entry.index}")
                verified_runtime_copies += 1
        report.update(
            {
                "output_iso": str(args.output),
                "output_iso_size": args.output.stat().st_size,
                "output_iso_sha256": file_sha(args.output),
                "volume_space_sectors": volume_sectors,
                "verified_translation_count": verified_translations,
                "verified_runtime_copy_count": verified_runtime_copies,
                "boot_extent": {**boot_extent, "verified_lba": reread_boot_record.extent_lba},
                "eboot_extent": {**eboot_extent, "verified_lba": reread_eboot_record.extent_lba},
            }
        )
    (args.work / "preflight-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    printable = {key: value for key, value in report.items() if key not in ("resources", "overflows")}
    if "system_messages" in printable:
        printable["system_messages"] = {
            key: value for key, value in printable["system_messages"].items() if key != "rows"
        }
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    if overflow:
        raise ValueError(f"IDM allocation overflow count: {len(overflow)}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("base_translations", type=Path)
    parser.add_argument("remaining", type=Path)
    parser.add_argument("runtime_map", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--seed-boot", type=Path)
    parser.add_argument("--seed-eboot", type=Path)
    parser.add_argument("--cast-item-workspace", type=Path, required=True)
    parser.add_argument("--system-messages", type=Path, required=True)
    parser.add_argument("--system-aliases", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    preflight(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
