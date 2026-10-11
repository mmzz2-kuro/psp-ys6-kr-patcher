#!/usr/bin/env python3
"""Build and apply validated SPECIAL VERSION cast/item translation assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive, replace_file
    from tools.scripts.ys6_castinfo import NAME_SIZE, parse_records as parse_cast
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_special_font_expand_proof_iso import read_iso
    from tools.scripts.ys6_special_nondialogue_audit import parse_items
    from tools.scripts.ys6_z import build_container, verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE
    from ys6_arc import DATA_FLAGS, parse_archive, replace_file
    from ys6_castinfo import NAME_SIZE, parse_records as parse_cast
    from ys6_hangul_codec import encode_translation
    from ys6_special_font_expand_proof_iso import read_iso
    from ys6_special_nondialogue_audit import parse_items
    from ys6_z import build_container, verify_container_bytes


CAST_PATH = "PSP_GAME/USRDIR/data/misc/castinfo.dat.z"
ITEM_PATH = "PSP_GAME/USRDIR/data/misc/invinfo.dat.z"
INIT_PATH = "PSP_GAME/USRDIR/data/arc/init.bin"
CAST_ENTRY = (7, "castinfo.dat.z")
ITEM_ENTRY = (9, "invinfo.dat.z")
ITEM_NAME_SIZE = 32
ITEM_METADATA_SIZE = 44
ITEM_DESCRIPTION_SIZE = 108


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def unpack(data: bytes, label: str) -> bytes:
    valid, payload, error = verify_container_bytes(data)
    if not valid or payload is None:
        raise ValueError(f"invalid {label} container: {error}")
    return payload


def fixed(value: bytes, size: int, label: str) -> bytes:
    if b"\0" in value or len(value) + 1 > size:
        raise ValueError(f"{label} field overflow or NUL: {len(value) + 1}/{size}")
    return value + bytes(size - len(value))


def build_workspace(cast_workspace: dict, item_workspace: dict, cast_payload: bytes,
                    item_payload: bytes) -> dict:
    special_cast = {row.identifier: row for row in parse_cast(cast_payload)}
    cast_by_source = {}
    for row in cast_workspace["records"]:
        if row.get("status") not in {"reviewed", "override"} or not row.get("translation"):
            continue
        cast_by_source.setdefault(row["source"], []).append(row)
    cast_rows = []
    for target in special_cast.values():
        candidates = cast_by_source.get(target.name_cp932, [])
        translations = {row["translation"] for row in candidates}
        if len(translations) > 1:
            raise ValueError(f"cast source translation conflict: {target.name_cp932}: {translations}")
        if not candidates:
            continue
        source = candidates[0]
        cast_rows.append({
            "identifier": target.identifier,
            "source": target.name_cp932,
            "source_name_field_hex": target.name_raw_hex,
            "source_name_field_sha256": sha(bytes.fromhex(target.name_raw_hex)),
            "translation": source["translation"],
            "source_identifier": source["identifier"],
            "match_method": "identifier_and_source" if source["identifier"] == target.identifier else "source_name_remap",
            "status": "apply",
        })
    if len(cast_rows) != 70:
        raise ValueError(f"SPECIAL cast apply count mismatch: {len(cast_rows)}")

    special_items = {row["resource_id"]: row for row in parse_items(item_payload)}
    item_rows, excluded = [], []
    for source in item_workspace["records"]:
        target = special_items.get(source["resource_id"])
        if target is None:
            continue
        exact = target["name"] == source["source_name"] and target["description"] == source["source_description"]
        if source["resource_id"] == "ky_09" or not exact:
            excluded.append({"resource_id": source["resource_id"], "source_name": target["name"],
                             "reason": "special_description_review_required", "status": "excluded"})
            continue
        item_rows.append({
            "index": target["index"], "resource_id": target["resource_id"],
            "source_name": target["name"], "source_description": target["description"],
            "source_record_sha256": target["record_sha256"],
            "translation_name": source["translation_name"],
            "translation_description": source["translation_description"],
            "match_method": "resource_id_and_source", "status": "apply",
        })
    for resource_id in ("ky_20", "ky_21", "ky_22", "ky_23"):
        target = special_items[resource_id]
        excluded.append({"resource_id": resource_id, "source_name": target["name"],
                         "reason": "special_only_translation_required", "status": "excluded"})
    if len(item_rows) != 72 or len(excluded) != 5:
        raise ValueError(f"SPECIAL item apply/excluded count mismatch: {len(item_rows)}/{len(excluded)}")
    return {
        "schema_version": 1, "profile": "ULJM-05155",
        "source": {"cast_payload_sha256": sha(cast_payload), "item_payload_sha256": sha(item_payload)},
        "summary": {"cast_apply_count": len(cast_rows), "item_apply_count": len(item_rows),
                    "item_excluded_count": len(excluded)},
        "cast": cast_rows, "items": item_rows, "excluded_items": excluded,
    }


def patch_cast(payload: bytes, rows: list[dict], mapping: list[dict]) -> tuple[bytes, list[dict]]:
    records = {row.identifier: row for row in parse_cast(payload)}
    output = bytearray(payload); report = []
    for row in rows:
        target = records[row["identifier"]]
        if target.name_cp932 != row["source"] or sha(bytes.fromhex(target.name_raw_hex)) != row["source_name_field_sha256"]:
            raise ValueError(f"cast source mismatch: {row['identifier']}")
        encoded = encode_translation(row["translation"], mapping)
        output[target.name_offset:target.name_offset + NAME_SIZE] = fixed(encoded, NAME_SIZE, row["identifier"])
        report.append({"identifier": row["identifier"], "source": row["source"],
                       "translation": row["translation"], "encoded_hex": encoded.hex().upper(),
                       "match_method": row["match_method"]})
    result = bytes(output)
    allowed = {index for row in rows for index in range(records[row["identifier"]].name_offset,
                                                         records[row["identifier"]].name_offset + NAME_SIZE)}
    if any(index not in allowed for index, (left, right) in enumerate(zip(payload, result)) if left != right):
        raise ValueError("cast change outside selected name fields")
    return result, report


def patch_items(payload: bytes, rows: list[dict], mapping: list[dict]) -> tuple[bytes, list[dict]]:
    records = {row["resource_id"]: row for row in parse_items(payload)}
    output = bytearray(payload); report = []
    for row in rows:
        target = records[row["resource_id"]]
        if (target["index"] != row["index"] or target["name"] != row["source_name"] or
                target["description"] != row["source_description"] or
                target["record_sha256"] != row["source_record_sha256"]):
            raise ValueError(f"item source mismatch: {row['resource_id']}")
        name = encode_translation(row["translation_name"], mapping)
        description = encode_translation(row["translation_description"].replace("\n", "\r\n"), mapping)
        offset = 16 + target["index"] * 184
        output[offset:offset + ITEM_NAME_SIZE] = fixed(name, ITEM_NAME_SIZE, row["resource_id"] + " name")
        description_offset = offset + ITEM_NAME_SIZE + ITEM_METADATA_SIZE
        output[description_offset:description_offset + ITEM_DESCRIPTION_SIZE] = fixed(
            description, ITEM_DESCRIPTION_SIZE, row["resource_id"] + " description")
        report.append({"index": target["index"], "resource_id": row["resource_id"],
                       "translation_name": row["translation_name"], "name_hex": name.hex().upper(),
                       "description_hex": description.hex().upper()})
    result = bytes(output)
    before, after = {row["resource_id"]: row for row in parse_items(payload)}, {row["resource_id"]: row for row in parse_items(result)}
    selected = {row["resource_id"] for row in rows}
    for resource_id in before:
        if before[resource_id]["metadata_sha256"] != after[resource_id]["metadata_sha256"]:
            raise ValueError(f"item metadata changed: {resource_id}")
        if resource_id not in selected and before[resource_id]["record_sha256"] != after[resource_id]["record_sha256"]:
            raise ValueError(f"excluded item changed: {resource_id}")
    return result, report


def prepare(iso: Path, workspace: dict, mapping: list[dict], work: Path) -> dict:
    cast_container, cast_iso_record = read_iso(iso, CAST_PATH)
    item_container, item_iso_record = read_iso(iso, ITEM_PATH)
    init, init_iso_record = read_iso(iso, INIT_PATH)
    entries = parse_archive(init)
    cast_entry = next(row for row in entries if (row.index, row.name) == CAST_ENTRY)
    item_entry = next(row for row in entries if (row.index, row.name) == ITEM_ENTRY)
    cast_payload = unpack(cast_container, "standalone cast")
    item_payload = unpack(item_container, "standalone item")
    if unpack(init[cast_entry.offset:cast_entry.offset + cast_entry.size], "runtime cast") != cast_payload:
        raise ValueError("cast standalone/runtime payload mismatch")
    if unpack(init[item_entry.offset:item_entry.offset + item_entry.size], "runtime item") != item_payload:
        raise ValueError("item standalone/runtime payload mismatch")
    if sha(cast_payload) != workspace["source"]["cast_payload_sha256"] or sha(item_payload) != workspace["source"]["item_payload_sha256"]:
        raise ValueError("cast/item workspace source hash mismatch")
    patched_cast, cast_report = patch_cast(cast_payload, workspace["cast"], mapping)
    patched_items, item_report = patch_items(item_payload, workspace["items"], mapping)
    cast_output, item_output = build_container(patched_cast), build_container(patched_items)
    limits = {
        "cast_standalone": math.ceil(len(cast_container) / SECTOR_SIZE) * SECTOR_SIZE,
        "item_standalone": math.ceil(len(item_container) / SECTOR_SIZE) * SECTOR_SIZE,
        "cast_runtime": cast_entry.allocated_size,
        "item_runtime": item_entry.allocated_size,
    }
    sizes = {"cast_standalone": len(cast_output), "item_standalone": len(item_output),
             "cast_runtime": len(cast_output), "item_runtime": len(item_output)}
    overflow = [{"target": key, "size": sizes[key], "allocated": value}
                for key, value in limits.items() if sizes[key] > value]
    if overflow:
        raise ValueError(f"cast/item allocation overflow: {overflow}")
    patched_init = replace_file(replace_file(init, cast_entry, cast_output), item_entry, item_output)
    work.mkdir(parents=True, exist_ok=True)
    paths = {"cast": work / "castinfo.dat.z", "items": work / "invinfo.dat.z", "init": work / "init.bin"}
    paths["cast"].write_bytes(cast_output); paths["items"].write_bytes(item_output); paths["init"].write_bytes(patched_init)
    report = {"cast_apply_count": len(cast_report), "item_apply_count": len(item_report),
              "item_excluded_count": len(workspace["excluded_items"]), "sizes": sizes, "allocated": limits,
              "overflow_count": 0, "cast_payload_sha256": sha(patched_cast),
              "item_payload_sha256": sha(patched_items), "cast": cast_report, "items": item_report}
    return {"paths": paths, "records": {"cast": cast_iso_record, "items": item_iso_record, "init": init_iso_record},
            "originals": {"cast": cast_container, "items": item_container, "init": init}, "report": report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path); parser.add_argument("cast_workspace", type=Path)
    parser.add_argument("item_workspace", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    init = read_iso(args.iso, INIT_PATH)[0]
    cast_payload = unpack(read_iso(args.iso, CAST_PATH)[0], "cast")
    item_payload = unpack(read_iso(args.iso, ITEM_PATH)[0], "item")
    workspace = build_workspace(json.loads(args.cast_workspace.read_text(encoding="utf-8-sig")),
                                json.loads(args.item_workspace.read_text(encoding="utf-8-sig")),
                                cast_payload, item_payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(workspace["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
