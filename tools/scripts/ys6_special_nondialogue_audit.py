#!/usr/bin/env python3
"""Read-only ULJM-05009 -> ULJM-05155 non-dialogue text compatibility audit."""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive, replace_file
    from tools.scripts.ys6_castinfo import parse_records as parse_cast
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_system_message_workspace import encode_system_translation, encoded_length, extract as extract_system
    from tools.scripts.ys6_z import build_container, verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record
    from ys6_arc import DATA_FLAGS, parse_archive, replace_file
    from ys6_castinfo import parse_records as parse_cast
    from ys6_hangul_codec import encode_translation
    from ys6_system_message_workspace import encode_system_translation, encoded_length, extract as extract_system
    from ys6_z import build_container, verify_container_bytes


NAME_SIZE = 32
METADATA_SIZE = 44
DESCRIPTION_SIZE = 108
FORMAT_TOKEN = re.compile(r"%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[hlLzjt]*[diuoxXfFeEgGaAcspn%]")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_iso(iso: Path, internal_path: str) -> bytes:
    record = find_record(iso, internal_path)
    with iso.open("rb") as stream:
        stream.seek(record.extent_lba * SECTOR_SIZE)
        return stream.read(record.data_length)


def archive_payload(archive: bytes, name: str) -> tuple[bytes, dict]:
    entries = parse_archive(archive)
    entry = next(row for row in entries if row.flags in DATA_FLAGS and row.name.casefold() == name.casefold())
    stored = archive[entry.offset:entry.offset + entry.size]
    if name.lower().endswith(".z"):
        valid, payload, error = verify_container_bytes(stored)
        if not valid or payload is None:
            raise ValueError(f"invalid container {name}: {error}")
    else:
        payload = stored
    unchanged = replace_file(archive, entry, stored) == archive
    roundtrip = True
    if name.lower().endswith(".z"):
        valid, rebuilt, _error = verify_container_bytes(build_container(payload))
        roundtrip = bool(valid and rebuilt == payload)
    return payload, {
        "entry_index": entry.index,
        "entry_name": entry.name,
        "stored_size": len(stored),
        "payload_size": len(payload),
        "payload_sha256": sha(payload),
        "same_entry_archive_roundtrip": unchanged,
        "container_payload_roundtrip": roundtrip,
    }


def container_payload(data: bytes) -> bytes:
    valid, payload, error = verify_container_bytes(data)
    if not valid or payload is None:
        raise ValueError(f"invalid standalone container: {error}")
    return payload


def decode(raw: bytes) -> str:
    try:
        return raw.decode("cp932")
    except UnicodeDecodeError:
        return ""


def parse_items(data: bytes) -> list[dict]:
    if len(data) < 16:
        raise ValueError("invinfo header truncated")
    record_size, count = struct.unpack_from("<II", data, 8)
    if record_size != 184 or len(data) != 16 + record_size * count:
        raise ValueError(f"invinfo layout mismatch: size={len(data)}, record={record_size}, count={count}")
    rows = []
    for index in range(count):
        offset = 16 + index * record_size
        record = data[offset:offset + record_size]
        name_raw = record[:NAME_SIZE].split(b"\0", 1)[0]
        metadata = record[NAME_SIZE:NAME_SIZE + METADATA_SIZE]
        description_raw = record[NAME_SIZE + METADATA_SIZE:].split(b"\0", 1)[0]
        resource_id = metadata[20:30].split(b"\0", 1)[0].decode("ascii", errors="replace")
        rows.append({
            "index": index,
            "resource_id": resource_id,
            "name": decode(name_raw),
            "description": decode(description_raw).replace("\r\n", "\n"),
            "metadata_sha256": sha(metadata),
            "record_sha256": sha(record),
        })
    return rows


def find_all(data: bytes, needle: bytes) -> list[int]:
    positions, start = [], 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            return positions
        if offset + len(needle) < len(data) and data[offset + len(needle)] == 0:
            positions.append(offset)
        start = offset + 1


def audited_encode(text: str, mapping: list[dict], missing: set[str]) -> bytes | None:
    codes = {row["character"]: int(row["game_code"], 0) for row in mapping}
    output = bytearray()
    try:
        for character in text:
            if character in codes:
                output.extend(codes[character].to_bytes(2, "big"))
            elif "가" <= character <= "힣":
                missing.add(character)
                output.extend(b"\xF9\xFC")
            else:
                output.extend(character.encode("cp932"))
        return bytes(output)
    except (UnicodeEncodeError, ValueError):
        return None


def classify_cast(payload: bytes, workspace: dict, mapping: list[dict]) -> dict:
    special = {row.identifier: row for row in parse_cast(payload)}
    counts, candidates, missing = Counter(), [], set()
    approved = 0
    for row in workspace["records"]:
        target = special.get(row["identifier"])
        if target is None:
            status = "unmatched"
        elif target.name_cp932 == row["source"]:
            status = "exact"
        else:
            status = "context_match"
        counts[status] += 1
        translation = row.get("translation", "")
        is_approved = row.get("status") in {"reviewed", "override"} and bool(translation)
        if is_approved:
            approved += 1
            encoded = audited_encode(translation, mapping, missing)
            if encoded is None:
                counts["approved_unencodable"] += 1
            elif len(encoded) + 1 > NAME_SIZE:
                counts["approved_overflow"] += 1
            if status == "exact":
                counts["approved_exact"] += 1
            candidates.append({"identifier": row["identifier"], "status": status,
                               "source": row["source"], "special_source": target.name_cp932 if target else None,
                               "translation": translation,
                               "encoded_size_with_nul": len(encoded) + 1 if encoded is not None else None})
    return {"standard_count": len(workspace["records"]), "special_count": len(special),
            "approved_count": approved, "counts": dict(counts), "missing_glyphs": "".join(sorted(missing)),
            "candidates": candidates,
            "special_only_identifiers": sorted(set(special) - {row["identifier"] for row in workspace["records"]})}


def classify_items(payload: bytes, workspace: dict, mapping: list[dict]) -> dict:
    special_rows = parse_items(payload)
    special = {row["resource_id"]: row for row in special_rows}
    counts, candidates, missing = Counter(), [], set()
    approved = 0
    mapped_characters = {row["character"] for row in mapping}
    for row in workspace["records"]:
        target = special.get(row["resource_id"])
        if target is None:
            status = "unmatched"
        elif target["name"] == row["source_name"] and target["description"] == row["source_description"]:
            status = "exact"
        elif target["name"] == row["source_name"]:
            status = "context_match"
        else:
            status = "conflict"
        counts[status] += 1
        is_approved = row.get("status") == "override" and bool(row.get("translation_name"))
        if not is_approved:
            continue
        approved += 1
        name = audited_encode(row["translation_name"], mapping, missing)
        description_text = row.get("translation_description", "").replace("\n", "\r\n")
        description = audited_encode(description_text, mapping, missing)
        if name is None or description is None:
            counts["approved_unencodable"] += 1
        elif len(name) + 1 > NAME_SIZE or len(description) + 1 > DESCRIPTION_SIZE:
            counts["approved_overflow"] += 1
        if status == "exact":
            counts["approved_exact"] += 1
        candidates.append({"index": row["index"], "resource_id": row["resource_id"], "status": status,
                           "source_name": row["source_name"], "special_name": target["name"] if target else None,
                           "translation_name": row["translation_name"],
                           "name_size_with_nul": len(name) + 1 if name is not None else None,
                           "description_size_with_nul": len(description) + 1 if description is not None else None})
    return {"standard_count": len(workspace["records"]), "special_count": len(special_rows),
            "special_layout": {"header_size": 16, "record_size": 184, "record_count": len(special_rows),
                               "name_size": NAME_SIZE, "metadata_size": METADATA_SIZE,
                               "description_size": DESCRIPTION_SIZE},
            "approved_count": approved, "counts": dict(counts), "missing_glyphs": "".join(sorted(missing)),
            "candidates": candidates,
            "special_only_items": [row for row in special_rows if row["resource_id"] not in
                                   {item["resource_id"] for item in workspace["records"]}]}


def classify_system(executable: bytes, workspace: dict, mapping: list[dict]) -> dict:
    counts, candidates, missing, incompatible = Counter(), [], set(), set()
    mapped_characters = {row["character"] for row in mapping}
    extracted = extract_system(executable)["records"]
    workspace_raw = {row["source_raw_hex"] for row in workspace["records"]}
    special_only = [row for row in extracted if row["source_raw_hex"] not in workspace_raw]
    approved = 0
    for row in workspace["records"]:
        raw = bytes.fromhex(row["source_raw_hex"])
        hits = find_all(executable, raw)
        status = "unmatched" if not hits else "exact" if len(hits) == 1 else "ambiguous"
        counts[status] += 1
        translation = row.get("translation", "")
        is_approved = row.get("status") == "override" and bool(translation)
        if not is_approved:
            continue
        approved += 1
        missing.update(character for character in translation
                       if "가" <= character <= "힣" and character not in mapped_characters)
        for character in set(translation):
            if "가" <= character <= "힣" and character in mapped_characters:
                try:
                    encode_system_translation(character, mapping)
                except ValueError:
                    incompatible.add(character)
        try:
            encoded = encode_system_translation(translation, mapping)
            encoding_error = None
        except ValueError as exc:
            encoded = None
            encoding_error = str(exc)
            match = re.search(r"'(.)'", encoding_error)
            if match:
                incompatible.add(match.group(1))
        source_tokens = FORMAT_TOKEN.findall(row.get("source", ""))
        translation_tokens = FORMAT_TOKEN.findall(translation)
        token_valid = source_tokens == translation_tokens
        estimated_size = encoded_length(translation) + 1
        fit = bool(hits) and estimated_size <= len(raw) + 1
        if status == "exact": counts["approved_exact"] += 1
        if not fit: counts["approved_overflow_or_unmatched"] += 1
        if encoding_error: counts["approved_euc_encoding_blocked"] += 1
        if not token_valid: counts["approved_token_mismatch"] += 1
        fuzzy = []
        if status == "unmatched":
            ranked = sorted(
                ((difflib.SequenceMatcher(None, row["source"], candidate["source"]).ratio(), candidate)
                 for candidate in extracted), reverse=True, key=lambda item: item[0]
            )[:3]
            fuzzy = [{"ratio": round(ratio, 4), "identifier": candidate["identifier"],
                      "offset": f"0x{candidate['offset']:X}", "source": candidate["source"]}
                     for ratio, candidate in ranked]
        candidates.append({"identifier": row["identifier"], "status": status,
                           "special_offsets": [f"0x{offset:X}" for offset in hits],
                           "source": row["source"], "translation": translation,
                           "source_size_with_nul": len(raw) + 1,
                           "translation_size_with_nul": estimated_size,
                           "fits_source_storage": fit, "format_tokens_valid": token_valid,
                           "euc_encoding_valid": encoding_error is None,
                           "euc_encoding_error": encoding_error, "fuzzy_candidates": fuzzy})
    return {"standard_count": len(workspace["records"]), "special_extracted_count": len(extracted),
            "special_only_candidate_count": len(special_only), "approved_count": approved,
            "counts": dict(counts), "missing_glyphs": "".join(sorted(missing)),
            "euc_incompatible_characters": "".join(sorted(incompatible)), "candidates": candidates,
            "special_only_candidates": special_only}


def build(args: argparse.Namespace) -> dict:
    standard_init = read_iso(args.standard_iso, "PSP_GAME/USRDIR/data/arc/init.bin")
    special_init = read_iso(args.special_iso, "PSP_GAME/USRDIR/data/arc/init.bin")
    standard_cast, standard_cast_meta = archive_payload(standard_init, "castinfo.dat")
    special_cast, special_cast_meta = archive_payload(special_init, "castinfo.dat.z")
    standard_items, standard_item_meta = archive_payload(standard_init, "invinfo.dat")
    special_items, special_item_meta = archive_payload(special_init, "invinfo.dat.z")
    standard_cast_standalone = read_iso(args.standard_iso, "PSP_GAME/USRDIR/data/misc/castinfo.dat")
    standard_item_standalone = read_iso(args.standard_iso, "PSP_GAME/USRDIR/data/misc/invinfo.dat")
    special_cast_standalone_raw = read_iso(args.special_iso, "PSP_GAME/USRDIR/data/misc/castinfo.dat.z")
    special_item_standalone_raw = read_iso(args.special_iso, "PSP_GAME/USRDIR/data/misc/invinfo.dat.z")
    special_cast_standalone = container_payload(special_cast_standalone_raw)
    special_item_standalone = container_payload(special_item_standalone_raw)
    mapping = json.loads(args.mapping.read_text(encoding="utf-8-sig"))["mappings"]
    cast_workspace = json.loads(args.cast_workspace.read_text(encoding="utf-8-sig"))
    item_workspace = json.loads(args.item_workspace.read_text(encoding="utf-8-sig"))
    system_workspace = json.loads(args.system_workspace.read_text(encoding="utf-8-sig"))
    special_boot = read_iso(args.special_iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    report = {
        "schema_version": 1,
        "profiles": {"standard": "ULJM-05009", "special": "ULJM-05155"},
        "resources": {"standard_cast": standard_cast_meta, "special_cast": special_cast_meta,
                      "standard_items": standard_item_meta, "special_items": special_item_meta},
        "cast": classify_cast(special_cast, cast_workspace, mapping),
        "items": classify_items(special_items, item_workspace, mapping),
        "system_messages": classify_system(special_boot, system_workspace, mapping),
        "source_cross_checks": {
            "standard_cast_payload_matches_workspace_source": sha(standard_cast) == cast_workspace["source"]["castinfo_sha256"],
            "standard_item_payload_matches_workspace_source": sha(standard_items) == item_workspace["source_sha256"],
            "special_boot_sha256": sha(special_boot),
            "standard_cast_standalone_matches_archive": standard_cast_standalone == standard_cast,
            "standard_item_standalone_matches_archive": standard_item_standalone == standard_items,
            "special_cast_standalone_matches_archive": special_cast_standalone == special_cast,
            "special_item_standalone_matches_archive": special_item_standalone == special_items,
            "special_cast_standalone_container_roundtrip":
                verify_container_bytes(build_container(special_cast_standalone))[1] == special_cast_standalone,
            "special_item_standalone_container_roundtrip":
                verify_container_bytes(build_container(special_item_standalone))[1] == special_item_standalone,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, rows, fields in (
        ("cast-candidates.csv", report["cast"]["candidates"],
         ("identifier", "status", "source", "special_source", "translation", "encoded_size_with_nul")),
        ("item-candidates.csv", report["items"]["candidates"],
         ("index", "resource_id", "status", "source_name", "special_name", "translation_name",
          "name_size_with_nul", "description_size_with_nul")),
        ("system-message-candidates.csv", report["system_messages"]["candidates"],
         ("identifier", "status", "special_offsets", "source", "translation", "source_size_with_nul",
          "translation_size_with_nul", "fits_source_storage", "format_tokens_valid", "euc_encoding_valid",
          "euc_encoding_error", "fuzzy_candidates")),
    ):
        with (args.output.parent / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                                 for key, value in row.items()})
    summary = {
        "cast": {key: value for key, value in report["cast"].items() if key != "candidates"},
        "items": {key: value for key, value in report["items"].items() if key not in {"candidates", "special_only_items"}},
        "system_messages": {key: value for key, value in report["system_messages"].items()
                            if key not in {"candidates", "special_only_candidates"}},
        "source_cross_checks": report["source_cross_checks"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    import sys
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("standard_iso", type=Path)
    parser.add_argument("special_iso", type=Path)
    parser.add_argument("cast_workspace", type=Path)
    parser.add_argument("item_workspace", type=Path)
    parser.add_argument("system_workspace", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output", type=Path)
    build(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
