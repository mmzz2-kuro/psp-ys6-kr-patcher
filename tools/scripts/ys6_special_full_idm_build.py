#!/usr/bin/env python3
"""Build the full resolved IDM dialogue port for Ys VI SPECIAL VERSION."""
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
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_arc import parse_archive, replace_file
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_idm import parse_idm, rebuild_idm, sha256
    from tools.scripts.ys6_special_font_expand import expand
    from tools.scripts.ys6_special_font_expand_proof_iso import (
        BASE_ISO_SHA256, append_extent, read_iso, update_volume_space, write_fixed,
    )
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record
    from ys6_arc import parse_archive, replace_file
    from ys6_hangul_codec import encode_translation
    from ys6_idm import parse_idm, rebuild_idm, sha256
    from ys6_special_font_expand import expand
    from ys6_special_font_expand_proof_iso import (
        BASE_ISO_SHA256, append_extent, read_iso, update_volume_space, write_fixed,
    )


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def current_resolved_rows(resolution: dict, workspace: dict) -> tuple[list[dict], list[dict]]:
    current = {(row["iso_path"], int(row["string_index"])): row for row in workspace["records"]}
    result = []; changed = []
    for old in resolution["all_resolved"]:
        key = old["source_iso_path"], int(old["source_string_index"])
        row = current.get(key)
        if row is None:
            raise ValueError(f"current translation row missing: {key}")
        if row["source_raw_hex"].upper() != old["source_raw_hex"].upper():
            raise ValueError(f"current translation source mismatch: {key}")
        if row["status"] != "override":
            raise ValueError(f"resolved translation is no longer override: {key}: {row['status']}")
        updated = dict(old); updated["translation"] = row["translation"]
        result.append(updated)
        if updated["translation"] != old["translation"]:
            changed.append({"source_iso_path": key[0], "source_string_index": key[1],
                            "target_iso_path": old["target_iso_path"],
                            "target_flat_index": int(old["target_flat_index"]),
                            "before": old["translation"], "after": updated["translation"]})
    return result, changed


def tile_atlas(source: Image.Image, count: int, columns: int = 32) -> Image.Image:
    rows = max(1, math.ceil(count / columns)); result = Image.new("L", (columns * 16, rows * 14), 0)
    for index in range(count):
        result.paste(source.crop((index * 16, 0, index * 16 + 16, 14)),
                     ((index % columns) * 16, (index // columns) * 14))
    return result


def build(args) -> dict:
    if file_sha(args.iso) != BASE_ISO_SHA256:
        raise ValueError("issue-109 base ISO SHA-256 mismatch")
    args.work.mkdir(parents=True, exist_ok=True)
    resolution = json.loads(args.resolution.read_text(encoding="utf-8-sig"))
    base_mapping_doc = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    runtime = json.loads(args.runtime_map.read_text(encoding="utf-8-sig"))
    workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    rows, translation_changes = current_resolved_rows(resolution, workspace)
    if len(rows) != 4127:
        raise ValueError(f"resolved translation count mismatch: {len(rows)}")
    base_mapping = base_mapping_doc["mappings"]
    if int(base_mapping_doc["mapping_revision"]) != 3 or len(base_mapping) != 434:
        raise ValueError("issue-109 mapping revision/count mismatch")
    mapped = {row["character"] for row in base_mapping}
    needed = sorted({character for row in rows for character in row["translation"]
                     if "가" <= character <= "힣" and character not in mapped}, key=ord)
    if len(needed) != 512:
        raise ValueError(f"remaining expanded glyph count mismatch: {len(needed)}")
    boot, original_boot_record = read_iso(args.iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    eboot, original_eboot_record = read_iso(args.iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    expanded_boot, new_rows, raw_atlas, boot_report = expand(boot, needed, args.font)
    expanded_eboot, eboot_rows, _unused_atlas, eboot_report = expand(eboot, needed, args.font)
    if new_rows != eboot_rows:
        raise ValueError("BOOT/EBOOT expanded mapping mismatch")
    mapping = [dict(row) for row in base_mapping] + new_rows
    mapping_doc = {"schema_version": 2, "profile": "ULJM-05155", "mapping_revision": 4,
                   "base_mapping_revision": 3, "mappings": mapping}
    mapping_path = args.work / "hangul-mapping.json"
    mapping_path.write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas = tile_atlas(raw_atlas, len(new_rows))
    atlas.resize((atlas.width * 3, atlas.height * 3), Image.Resampling.NEAREST).save(args.work / "expanded-glyph-atlas.png")
    (args.work / "BOOT.BIN").write_bytes(expanded_boot); (args.work / "EBOOT.BIN").write_bytes(expanded_eboot)
    target_changes: dict[str, dict[int, bytes]] = defaultdict(dict)
    target_text: dict[str, dict[int, str]] = defaultdict(dict)
    for row in rows:
        path = row["target_iso_path"]; index = int(row["target_flat_index"])
        encoded = encode_translation(row["translation"], mapping)
        if index in target_changes[path] and target_changes[path][index] != encoded:
            raise ValueError(f"shared target translation conflict: {path}#{index}")
        target_changes[path][index] = encoded; target_text[path][index] = row["translation"]
    runtime_by_path = {row["iso_path"]: row for row in runtime["resources"]}
    standalone_outputs = {}; standalone_records = {}; resource_reports = []
    archives = {}; archive_original = {}; archive_records = {}; archive_target_indices = defaultdict(list)
    for path, changes in sorted(target_changes.items()):
        original, record = read_iso(args.iso, path); parsed = parse_idm(original)
        output = rebuild_idm(parsed, changes); allocated = math.ceil(len(original) / SECTOR_SIZE) * SECTOR_SIZE
        if len(output) > allocated:
            raise ValueError(f"standalone IDM allocation overflow: {path}: {len(output)}>{allocated}")
        standalone_outputs[path] = output; standalone_records[path] = record
        copies = runtime_by_path[path]["copies"]
        for copy in copies:
            archive_path = copy["archive_path"]
            if archive_path not in archives:
                archive, archive_record = read_iso(args.iso, archive_path)
                archives[archive_path] = archive; archive_original[archive_path] = archive
                archive_records[archive_path] = archive_record
            archive = archives[archive_path]; entries = parse_archive(archive)
            entry = next((item for item in entries if item.index == int(copy["entry_index"])
                          and item.name == copy["entry_name"]), None)
            if entry is None:
                raise ValueError(f"runtime IDM entry missing: {archive_path}#{copy['entry_index']}")
            current = archive[entry.offset:entry.offset + entry.size]
            if current != original:
                raise ValueError(f"runtime IDM differs from standalone: {archive_path}#{entry.index}")
            if len(output) > entry.allocated_size:
                raise ValueError(f"archive IDM allocation overflow: {archive_path}#{entry.index}: {len(output)}>{entry.allocated_size}")
            archives[archive_path] = replace_file(archive, entry, output)
            archive_target_indices[archive_path].append(entry.index)
        resource_reports.append({"iso_path": path, "translation_count": len(changes),
                                 "runtime_copy_count": len(copies), "original_size": len(original),
                                 "output_size": len(output), "allocated_size": allocated,
                                 "free_bytes": allocated - len(output), "output_sha256": sha256(output)})
    s4010 = next(row for row in resource_reports if row["iso_path"].endswith("/s_4010/s_scene.idm"))
    if s4010["output_size"] != 4087 or s4010["allocated_size"] != 4096:
        raise ValueError(f"s_4010 current-size lock mismatch: {s4010}")
    for path, output in archives.items():
        if len(output) != len(archive_original[path]):
            raise ValueError(f"archive size changed unexpectedly: {path}")
        before_entries = parse_archive(archive_original[path]); after_entries = parse_archive(output)
        if [(x.index, x.name, x.offset, x.allocated_size) for x in before_entries] != [(x.index, x.name, x.offset, x.allocated_size) for x in after_entries]:
            raise ValueError(f"archive layout changed unexpectedly: {path}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(args.output)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    if temporary.exists(): temporary.unlink()
    shutil.copyfile(args.iso, temporary)
    try:
        with temporary.open("r+b") as handle:
            for path in sorted(standalone_outputs):
                write_fixed(handle, standalone_records[path], standalone_outputs[path])
            for path in sorted(archives):
                write_fixed(handle, archive_records[path], archives[path])
            boot_extent = append_extent(handle, original_boot_record, expanded_boot)
            eboot_extent = append_extent(handle, original_eboot_record, expanded_eboot)
            volume_sectors = update_volume_space(handle)
        temporary.replace(args.output)
    except Exception:
        if temporary.exists(): temporary.unlink()
        raise
    reread_boot, reread_boot_record = read_iso(args.output, "PSP_GAME/SYSDIR/BOOT.BIN")
    reread_eboot, reread_eboot_record = read_iso(args.output, "PSP_GAME/SYSDIR/EBOOT.BIN")
    if reread_boot != expanded_boot or reread_eboot != expanded_eboot:
        raise ValueError("expanded executable ISO re-extraction mismatch")
    verified_translations = 0; verified_copies = 0
    for path, expected in standalone_outputs.items():
        actual, _record = read_iso(args.output, path)
        if actual != expected:
            raise ValueError(f"standalone IDM ISO re-extraction mismatch: {path}")
        parsed = parse_idm(actual)
        for index, encoded in target_changes[path].items():
            if parsed["strings"][index]["raw"] != encoded:
                raise ValueError(f"translated IDM byte mismatch: {path}#{index}")
            verified_translations += 1
    for archive_path, expected in archives.items():
        actual, _record = read_iso(args.output, archive_path)
        if actual != expected:
            raise ValueError(f"archive ISO re-extraction mismatch: {archive_path}")
        entries = parse_archive(actual)
        for index in archive_target_indices[archive_path]:
            entry = next(item for item in entries if item.index == index)
            resource = next(row for row in runtime["resources"] for copy in row["copies"]
                            if copy["archive_path"] == archive_path and int(copy["entry_index"]) == index)
            expected_idm = standalone_outputs[resource["iso_path"]]
            if actual[entry.offset:entry.offset + entry.size] != expected_idm:
                raise ValueError(f"runtime IDM ISO re-extraction mismatch: {archive_path}#{index}")
            verified_copies += 1
    if verified_translations != 4127:
        raise ValueError(f"verified translation count mismatch: {verified_translations}")
    report = {"valid": True, "base_iso_sha256": BASE_ISO_SHA256,
              "workspace_sha256": file_sha(args.workspace), "resolution_sha256": file_sha(args.resolution),
              "base_mapping_sha256": file_sha(args.mapping), "mapping_revision": 4,
              "base_mapping_count": len(base_mapping), "expanded_glyph_count": len(new_rows),
              "mapping_count": len(mapping), "font_table_count": 1774 + len(new_rows),
              "resolved_translation_count": len(rows), "current_translation_change_count": len(translation_changes),
              "idm_resource_count": len(standalone_outputs), "runtime_copy_count": verified_copies,
              "archive_count": len(archives), "s4010": s4010,
              "boot": {**boot_extent, "verified_lba": reread_boot_record.extent_lba,
                       "font": {key: boot_report[key] for key in ("expanded_count", "new_segment_file_offset", "new_segment_vaddr", "new_segment_size")}},
              "eboot": {**eboot_extent, "verified_lba": reread_eboot_record.extent_lba,
                        "font": {key: eboot_report[key] for key in ("expanded_count", "new_segment_file_offset", "new_segment_vaddr", "new_segment_size")}},
              "output_iso": str(args.output), "output_iso_size": args.output.stat().st_size,
              "output_iso_sha256": file_sha(args.output), "volume_space_sectors": volume_sectors,
              "resources": resource_reports, "current_translation_changes": translation_changes}
    (args.work / "full-resolved-translations.json").write_text(
        json.dumps({"schema_version": 1, "profile": "ULJM-05155", "records": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (args.work / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("resources", "current_translation_changes")},
                     ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path); parser.add_argument("resolution", type=Path)
    parser.add_argument("runtime_map", type=Path); parser.add_argument("mapping", type=Path)
    parser.add_argument("workspace", type=Path); parser.add_argument("work", type=Path)
    parser.add_argument("output", type=Path); parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true"); args = parser.parse_args()
    build(args); return 0


if __name__ == "__main__":
    raise SystemExit(main())
