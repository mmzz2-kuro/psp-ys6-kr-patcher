#!/usr/bin/env python3
"""Estimate ULJM-05009 -> ULJM-05155 Ys VI patch-port feasibility."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

from iso9660_info import SECTOR_SIZE, find_record
from ys6_arc import DATA_FLAGS, find_file, parse_archive, replace_file
from ys6_z import build_container, verify_container_bytes


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_iso_file(iso: Path, internal_path: str) -> bytes:
    record = find_record(iso, internal_path)
    with iso.open("rb") as handle:
        handle.seek(record.extent_lba * SECTOR_SIZE)
        data = handle.read(record.data_length)
    if len(data) != record.data_length:
        raise OSError(f"ISO 파일을 끝까지 읽지 못했습니다: {internal_path}")
    return data


def read_inventory_file(iso: Path, row: dict[str, str], side: str) -> bytes:
    lba, size = int(row[f"{side}_lba"]), int(row[f"{side}_size"])
    with iso.open("rb") as handle:
        handle.seek(lba * SECTOR_SIZE); data = handle.read(size)
    if len(data) != size:
        raise OSError(f"ISO inventory 파일을 끝까지 읽지 못했습니다: {row['path']}")
    return data


def xso_signature(payload: bytes) -> dict[str, object] | None:
    if len(payload) < 0x24 or payload[:4] != b"XSR\0":
        return None
    words, strings = struct.unpack_from("<II", payload, 0x1C)
    code_end = 0x24 + words * 4
    table_end = code_end + strings * 4
    if code_end > len(payload) or table_end > len(payload):
        return None
    offsets = [struct.unpack_from("<I", payload, code_end + index * 4)[0] for index in range(strings)]
    pool = payload[table_end:]
    raw_strings = []
    for index, start in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < len(offsets) else len(pool)
        if start >= end or end > len(pool):
            return None
        stored = pool[start:end]; terminator = stored.find(b"\0")
        if terminator < 0:
            return None
        raw_strings.append(stored[:terminator].hex().upper())
    return {"payload_sha256": sha(payload), "code_sha256": sha(payload[0x24:code_end]),
            "code_word_count": words, "string_count": strings, "raw_strings": raw_strings}


def container_signature(data: bytes) -> dict[str, object] | None:
    valid, payload, _error = verify_container_bytes(data)
    return xso_signature(payload) if valid and payload is not None else None


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["path"].casefold(): row for row in csv.DictReader(handle)}


def collect_new_candidates(iso: Path, rows: dict[str, dict[str, str]]) -> tuple[list[dict], dict]:
    candidates: list[dict] = []
    archives = {"parsed": 0, "failed": 0, "xso_entries": 0}
    with iso.open("rb") as handle:
        for row in rows.values():
            path = row["path"]
            if row["second_size"] and path.lower().endswith(".xso.z"):
                handle.seek(int(row["second_lba"]) * SECTOR_SIZE); data = handle.read(int(row["second_size"]))
                signature = container_signature(data)
                if signature:
                    candidates.append({"location": path, "basename": Path(path).name.casefold(), **signature})
            if not row["second_size"] or not path.lower().startswith("psp_game/usrdir/data/arc/") or not path.lower().endswith(".bin"):
                continue
            handle.seek(int(row["second_lba"]) * SECTOR_SIZE); data = handle.read(int(row["second_size"]))
            try:
                entries = parse_archive(data); archives["parsed"] += 1
            except Exception:
                archives["failed"] += 1; continue
            for entry in entries:
                if entry.flags not in DATA_FLAGS or entry.size <= 0 or not entry.name.lower().endswith(".xso.z"):
                    continue
                signature = container_signature(data[entry.offset:entry.offset + entry.size])
                if signature:
                    archives["xso_entries"] += 1
                    candidates.append({"location": f"{path}#{entry.index}:{entry.name}",
                                       "basename": entry.name.casefold(), **signature})
    return candidates, archives


def archive_summary(data: bytes) -> dict[str, object]:
    try:
        entries = parse_archive(data)
    except Exception as exc:
        return {"valid": False, "error": str(exc), "size": len(data), "sha256": sha(data)}
    files = [entry for entry in entries if entry.flags in DATA_FLAGS and entry.size > 0]
    return {"valid": True, "size": len(data), "sha256": sha(data), "record_count": len(entries),
            "file_count": len(files), "names": [entry.name for entry in files]}


def build(first_iso: Path, second_iso: Path, comparison_csv: Path, catalog_path: Path,
          translations_path: Path, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    rows = load_rows(comparison_csv)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    translations = json.loads(translations_path.read_text(encoding="utf-8-sig"))
    candidates, archive_scan = collect_new_candidates(second_iso, rows)
    by_payload: dict[str, list[dict]] = defaultdict(list)
    by_code_name: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    by_basename: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        by_payload[candidate["payload_sha256"]].append(candidate)
        by_code_name[(candidate["basename"], candidate["code_sha256"], candidate["string_count"])].append(candidate)
        by_basename[candidate["basename"]].append(candidate)

    file_results = []
    for item in catalog["files"]:
        path = item["iso_path"]
        inventory_row = rows.get(path.casefold())
        if inventory_row is None or not inventory_row["first_size"]:
            file_results.append({"iso_path": path, "xso_sha256": item["xso_sha256"], "status": "old_inventory_missing",
                                 "match_count": 0, "matches": []})
            continue
        old_data = read_inventory_file(first_iso, inventory_row, "first")
        signature = container_signature(old_data)
        if signature is None:
            status, matches = "invalid_old_xso", []
        else:
            matches = by_payload.get(signature["payload_sha256"], [])
            if matches:
                status = "exact_payload"
            else:
                matches = by_code_name.get((Path(path).name.casefold(), signature["code_sha256"], signature["string_count"]), [])
                status = "same_code_and_string_count" if matches else "unmatched"
        file_results.append({"iso_path": path, "xso_sha256": item["xso_sha256"], "status": status,
                             "match_count": len(matches), "matches": [row["location"] for row in matches[:10]]})

    result_by_path = {row["iso_path"]: row for row in file_results}
    translation_counts = Counter()
    source_mapping_counts = Counter()
    for record in translations["records"]:
        match = result_by_path.get(record["iso_path"])
        translation_counts[match["status"] if match else "catalog_missing"] += 1
        pool = by_basename.get(Path(record["iso_path"]).name.casefold(), [])
        raw = record["source_raw_hex"].upper()
        hits = [(candidate["location"], index) for candidate in pool
                for index, value in enumerate(candidate["raw_strings"]) if value == raw]
        if not hits:
            source_mapping_counts["no_source_match"] += 1
        elif len(hits) == 1:
            source_mapping_counts["unique_source_match"] += 1
        elif len(set(index for _location, index in hits)) == 1:
            source_mapping_counts["duplicate_copies_same_index"] += 1
        else:
            source_mapping_counts["ambiguous_index"] += 1

    first_boot = read_iso_file(first_iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    second_boot = read_iso_file(second_iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    first_eboot = read_iso_file(first_iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    second_eboot = read_iso_file(second_iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    first_init = read_iso_file(first_iso, "PSP_GAME/USRDIR/data/arc/init.bin")
    second_init = read_iso_file(second_iso, "PSP_GAME/USRDIR/data/arc/init.bin")
    first_init_report, second_init_report = archive_summary(first_init), archive_summary(second_init)
    shared_init_names = sorted(set(first_init_report.get("names", [])) & set(second_init_report.get("names", [])))
    first_entries = {entry.name.casefold(): entry for entry in parse_archive(first_init)
                     if entry.flags in DATA_FLAGS and entry.size > 0}
    second_entries = {entry.name.casefold(): entry for entry in parse_archive(second_init)
                      if entry.flags in DATA_FLAGS and entry.size > 0}
    core_payloads = []
    for name in ("castinfo.dat", "enemyinfo.dat", "invinfo.dat", "gameinfo.dat", "eex.dat"):
        old_entry, new_entry = first_entries[name], second_entries[name + ".z"]
        old_payload = first_init[old_entry.offset:old_entry.offset + old_entry.size]
        new_container = second_init[new_entry.offset:new_entry.offset + new_entry.size]
        valid, new_payload, error = verify_container_bytes(new_container)
        core_payloads.append({"name": name, "new_name": new_entry.name, "new_container_valid": valid,
                              "error": error, "old_size": len(old_payload),
                              "new_payload_size": len(new_payload) if new_payload is not None else None,
                              "old_sha256": sha(old_payload),
                              "new_payload_sha256": sha(new_payload) if new_payload is not None else None,
                              "same_payload": new_payload == old_payload if new_payload is not None else False})

    tools_dir = translations_path.resolve().parents[1]
    additional_manifest = json.loads((tools_dir / "patchdata/ys6_additional_images/manifest.json").read_text(encoding="utf-8-sig"))
    additional_statuses = Counter()
    additional_payload_statuses = Counter()
    for resource in additional_manifest["resources"]:
        comparison = rows.get(resource["iso_path"].casefold())
        additional_statuses[comparison["status"] if comparison else "not_listed"] += 1
        if not comparison or not comparison["first_size"] or not comparison["second_size"]:
            additional_payload_statuses["missing_side"] += 1
            continue
        old_container = read_inventory_file(first_iso, comparison, "first")
        new_container = read_inventory_file(second_iso, comparison, "second")
        old_valid, old_payload, _ = verify_container_bytes(old_container)
        new_valid, new_payload, _ = verify_container_bytes(new_container)
        if not old_valid or not new_valid:
            additional_payload_statuses["invalid_container"] += 1
        elif old_payload == new_payload:
            additional_payload_statuses["same_decoded_payload"] += 1
        else:
            additional_payload_statuses["different_decoded_payload"] += 1
    option_comparison = rows.get("psp_game/usrdir/data/image/static_tex.dds.z")
    xso_sample_row = rows["psp_game/usrdir/data/map/s_02/s_0202/talkoruha3.xso.z"]
    xso_sample = read_inventory_file(second_iso, xso_sample_row, "second")
    xso_valid, xso_payload, xso_error = verify_container_bytes(xso_sample)
    rebuilt_xso = build_container(xso_payload) if xso_payload is not None else b""
    rebuilt_xso_valid, rebuilt_xso_payload, rebuilt_xso_error = verify_container_bytes(rebuilt_xso) if rebuilt_xso else (False, None, "not built")
    arc_sample_row = rows["psp_game/usrdir/data/arc/xso0202.bin"]
    arc_sample = read_inventory_file(second_iso, arc_sample_row, "second")
    arc_entry = find_file(parse_archive(arc_sample), "talkoruha3.xso.z")
    arc_roundtrip = replace_file(arc_sample, arc_entry, arc_sample[arc_entry.offset:arc_entry.offset + arc_entry.size])
    static_sample = read_inventory_file(second_iso, option_comparison, "second") if option_comparison else b""
    static_valid, static_payload, static_error = verify_container_bytes(static_sample) if static_sample else (False, None, "missing")
    rebuilt_static = build_container(static_payload) if static_payload is not None else b""
    rebuilt_static_valid, rebuilt_static_payload, rebuilt_static_error = verify_container_bytes(rebuilt_static) if rebuilt_static else (False, None, "not built")
    report = {
        "schema_version": 1,
        "executables": {
            "first_boot": {"size": len(first_boot), "sha256": sha(first_boot), "header_hex": first_boot[:16].hex().upper()},
            "second_boot": {"size": len(second_boot), "sha256": sha(second_boot), "header_hex": second_boot[:16].hex().upper()},
            "first_eboot": {"size": len(first_eboot), "sha256": sha(first_eboot), "header_hex": first_eboot[:16].hex().upper()},
            "second_eboot": {"size": len(second_eboot), "sha256": sha(second_eboot), "header_hex": second_eboot[:16].hex().upper()},
        },
        "init_archives": {"first": first_init_report, "second": second_init_report,
                          "shared_file_names": shared_init_names, "shared_file_name_count": len(shared_init_names),
                          "core_payloads": core_payloads},
        "new_xso_candidates": {"total": len(candidates), "archive_scan": archive_scan},
        "catalog_file_counts": dict(Counter(row["status"] for row in file_results)),
        "translation_record_counts": dict(translation_counts),
        "translation_source_mapping_counts": dict(source_mapping_counts),
        "image_assets": {"additional_resource_counts": dict(additional_statuses),
                         "additional_decoded_payload_counts": dict(additional_payload_statuses),
                         "option_static_tex_status": option_comparison["status"] if option_comparison else "not_listed"},
        "roundtrip_samples": {
            "standalone_xso": {"path": xso_sample_row["path"], "source_valid": xso_valid, "source_error": xso_error,
                               "rebuilt_valid": rebuilt_xso_valid, "rebuilt_error": rebuilt_xso_error,
                               "payload_equal": rebuilt_xso_payload == xso_payload,
                               "source_size": len(xso_sample), "rebuilt_size": len(rebuilt_xso)},
            "archive_same_entry": {"path": arc_sample_row["path"], "entry": arc_entry.name,
                                   "archive_byte_identical": arc_roundtrip == arc_sample},
            "static_tex": {"path": option_comparison["path"] if option_comparison else None,
                           "source_valid": static_valid, "source_error": static_error,
                           "rebuilt_valid": rebuilt_static_valid, "rebuilt_error": rebuilt_static_error,
                           "payload_equal": rebuilt_static_payload == static_payload,
                           "source_size": len(static_sample), "rebuilt_size": len(rebuilt_static)},
        },
        "catalog_file_count": len(file_results), "translation_record_count": len(translations["records"]),
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "xso-mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("iso_path", "xso_sha256", "status", "match_count", "matches"))
        writer.writeheader()
        for row in file_results:
            writer.writerow({**row, "matches": " | ".join(row["matches"])})
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_iso", type=Path); parser.add_argument("second_iso", type=Path)
    parser.add_argument("comparison_csv", type=Path); parser.add_argument("catalog", type=Path)
    parser.add_argument("translations", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.first_iso, args.second_iso, args.comparison_csv, args.catalog,
                           args.translations, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
