#!/usr/bin/env python3
"""Build a read-only mapping between Ys VI standalone and runtime archive XSO files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record, read_directory
    from tools.scripts.ys6_arc import AUXILIARY_FILE_FLAG, DATA_FLAGS, FILE_FLAG, ArcError, parse_archive
    from tools.scripts.ys6_xso import XsoError, parse_xso
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record, read_directory
    from ys6_arc import AUXILIARY_FILE_FLAG, DATA_FLAGS, FILE_FLAG, ArcError, parse_archive
    from ys6_xso import XsoError, parse_xso
    from ys6_z import verify_container_bytes


SCHEMA_VERSION = 2
EXPECTED_ISO_SHA256 = "0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B"
ARC_ROOT = "PSP_GAME/USRDIR/data/arc"
S0551_XSO_SHA256 = "1BA1D501FEF350045691CA15F3A4F99205623C829F3B916FEA566E3978175614"


class RuntimeMapError(Exception):
    pass


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def classify_hash_group(standalone_count: int, runtime_count: int) -> str:
    if standalone_count == 1 and runtime_count == 1:
        return "exact_one_to_one"
    if standalone_count == 1 and runtime_count > 1:
        return "runtime_duplicate"
    if standalone_count > 1 and runtime_count == 1:
        return "standalone_duplicate"
    if standalone_count > 1 and runtime_count > 1:
        return "many_to_many"
    if standalone_count and not runtime_count:
        return "standalone_only"
    if runtime_count and not standalone_count:
        return "runtime_only"
    raise RuntimeMapError("empty hash group")


def build_mappings(standalone: list[dict], runtime: list[dict]) -> list[dict]:
    standalone_by_hash: dict[str, list[dict]] = defaultdict(list)
    runtime_by_hash: dict[str, list[dict]] = defaultdict(list)
    for item in standalone:
        standalone_by_hash[item["xso_sha256"]].append(item)
    for item in runtime:
        if item["parse_status"] == "valid":
            runtime_by_hash[item["xso_sha256"]].append(item)
    mappings = []
    for digest in sorted(set(standalone_by_hash) | set(runtime_by_hash)):
        left = sorted(standalone_by_hash[digest], key=lambda item: item["iso_path"])
        right = sorted(runtime_by_hash[digest], key=lambda item: item["runtime_key"])
        mappings.append({
            "xso_sha256": digest,
            "status": classify_hash_group(len(left), len(right)),
            "standalone_count": len(left),
            "runtime_count": len(right),
            "standalone_paths": [item["iso_path"] for item in left],
            "runtime_keys": [item["runtime_key"] for item in right],
        })
    return mappings


def catalog_standalone(catalog: dict) -> list[dict]:
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("files"), list):
        raise RuntimeMapError("unsupported dialogue catalog schema")
    records = []
    seen_paths = set()
    for item in catalog["files"]:
        iso_path = item.get("iso_path")
        digest = item.get("xso_sha256")
        if not iso_path or not digest:
            raise RuntimeMapError("catalog XSO record is missing iso_path or xso_sha256")
        if iso_path in seen_paths:
            raise RuntimeMapError(f"duplicate catalog ISO path: {iso_path}")
        seen_paths.add(iso_path)
        records.append({
            "iso_path": iso_path,
            "map_group": item.get("map_group", ""),
            "map_id": item.get("map_id", ""),
            "xso_name": item.get("xso_name", ""),
            "compressed_size": item.get("compressed_size"),
            "xso_size": item.get("decompressed_size"),
            "xso_sha256": digest.upper(),
            "string_count": item.get("string_count"),
        })
    return sorted(records, key=lambda item: item["iso_path"])


def parse_xso_payload(payload: bytes, temporary_root: Path, sequence: int) -> tuple[int, str]:
    path = temporary_root / f"runtime-{sequence:04d}.xso"
    path.write_bytes(payload)
    try:
        parsed = parse_xso(path)
        return parsed.info.string_count, parsed.info.sha256
    finally:
        path.unlink(missing_ok=True)


def inspect_iso(iso: Path, temporary_root: Path) -> tuple[list[dict], list[dict], list[dict]]:
    directory = find_record(iso, ARC_ROOT)
    archives: list[dict] = []
    runtime_xso: list[dict] = []
    errors: list[dict] = []
    sequence = 0
    with iso.open("rb") as handle:
        records = sorted(read_directory(handle, directory), key=lambda item: item.name.casefold())
        for record in records:
            if record.is_directory:
                continue
            archive_path = f"{ARC_ROOT}/{record.name.split(';', 1)[0]}"
            handle.seek(record.extent_lba * SECTOR_SIZE)
            data = handle.read(record.data_length)
            archive_row = {
                "iso_path": archive_path,
                "filename": record.name.split(";", 1)[0],
                "extent_lba": record.extent_lba,
                "file_size": record.data_length,
                "sha256": sha256_bytes(data),
                "parse_status": "valid",
                "record_count": 0,
                "file_count": 0,
                "xso_count": 0,
                "total_xso_slack": 0,
            }
            try:
                entries = parse_archive(data)
            except ArcError as exc:
                archive_row["parse_status"] = "invalid"
                errors.append({"stage": "archive", "path": archive_path, "error": str(exc)})
                archives.append(archive_row)
                continue
            files = [entry for entry in entries if entry.flags in DATA_FLAGS and entry.size > 0]
            archive_row["record_count"] = len(entries)
            archive_row["file_count"] = len(files)
            for entry in files:
                if not entry.name.lower().endswith(".xso.z"):
                    continue
                sequence += 1
                container = data[entry.offset : entry.offset + entry.size]
                valid, payload, error = verify_container_bytes(container)
                row = {
                    "runtime_key": f"{archive_path}#{entry.index}:{entry.name}",
                    "archive_iso_path": archive_path,
                    "archive_sha256": archive_row["sha256"],
                    "entry_index": entry.index,
                    "entry_name": entry.name,
                    "flags_hex": f"0x{entry.flags:08X}",
                    "entry_kind": "regular" if entry.flags == FILE_FLAG else "auxiliary",
                    "record_offset": entry.record_offset,
                    "data_offset": entry.offset,
                    "compressed_size": entry.size,
                    "allocated_size": entry.allocated_size,
                    "slack_size": entry.allocated_size - entry.size,
                    "allocation_ratio": round(entry.size / entry.allocated_size, 6),
                    "container_sha256": sha256_bytes(container),
                    "parse_status": "invalid",
                    "xso_size": None,
                    "xso_sha256": None,
                    "string_count": None,
                    "error": error,
                }
                if valid and payload is not None:
                    try:
                        string_count, parsed_hash = parse_xso_payload(payload, temporary_root, sequence)
                        payload_hash = sha256_bytes(payload)
                        if parsed_hash != payload_hash:
                            raise RuntimeMapError("XSO parser SHA-256 mismatch")
                        row.update({
                            "parse_status": "valid", "xso_size": len(payload),
                            "xso_sha256": payload_hash, "string_count": string_count, "error": None,
                        })
                    except (OSError, XsoError, RuntimeMapError) as exc:
                        row["error"] = str(exc)
                if row["parse_status"] != "valid":
                    errors.append({"stage": "runtime_xso", "path": row["runtime_key"], "error": row["error"]})
                runtime_xso.append(row)
                archive_row["xso_count"] += 1
                archive_row["total_xso_slack"] += row["slack_size"]
            archives.append(archive_row)
    return archives, runtime_xso, errors


def mapping_status_indexes(mappings: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    standalone_status = {}
    runtime_status = {}
    for item in mappings:
        for path in item["standalone_paths"]:
            standalone_status[path] = item["status"]
        for key in item["runtime_keys"]:
            runtime_status[key] = item["status"]
    return standalone_status, runtime_status


def build_document(iso: Path, catalog_path: Path, temporary_root: Path) -> dict:
    iso_hash = sha256_file(iso)
    if iso_hash != EXPECTED_ISO_SHA256:
        raise RuntimeMapError(f"original ISO SHA-256 mismatch: expected={EXPECTED_ISO_SHA256}, actual={iso_hash}")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    standalone = catalog_standalone(catalog)
    archives, runtime, errors = inspect_iso(iso, temporary_root)
    mappings = build_mappings(standalone, runtime)
    standalone_status, runtime_status = mapping_status_indexes(mappings)
    for item in standalone:
        item["mapping_status"] = standalone_status[item["iso_path"]]
    for item in runtime:
        item["mapping_status"] = runtime_status.get(item["runtime_key"], "invalid")
    status_counts = Counter(item["status"] for item in mappings)
    standalone_status_counts = Counter(item["mapping_status"] for item in standalone)
    runtime_status_counts = Counter(item["mapping_status"] for item in runtime)
    valid_runtime = [item for item in runtime if item["parse_status"] == "valid"]
    high_risk = [item for item in valid_runtime if item["allocation_ratio"] >= 0.9]
    s0551 = [item for item in mappings if item["xso_sha256"] == S0551_XSO_SHA256]
    summary = {
        "archive_count": len(archives),
        "valid_archive_count": sum(item["parse_status"] == "valid" for item in archives),
        "archive_record_count": sum(item["record_count"] for item in archives),
        "archive_file_count": sum(item["file_count"] for item in archives),
        "standalone_xso_count": len(standalone),
        "runtime_xso_count": len(runtime),
        "valid_runtime_xso_count": len(valid_runtime),
        "invalid_runtime_xso_count": len(runtime) - len(valid_runtime),
        "mapping_group_count": len(mappings),
        "mapping_group_status_counts": dict(sorted(status_counts.items())),
        "standalone_status_counts": dict(sorted(standalone_status_counts.items())),
        "runtime_status_counts": dict(sorted(runtime_status_counts.items())),
        "zero_slack_count": sum(item["slack_size"] == 0 for item in valid_runtime),
        "high_risk_90_percent_count": len(high_risk),
        "error_count": len(errors),
        "s0551_regression_valid": len(s0551) == 1 and bool(s0551[0]["runtime_keys"]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"iso_path": str(iso), "iso_size": iso.stat().st_size, "iso_sha256": iso_hash, "catalog_path": str(catalog_path)},
        "summary": summary,
        "archives": archives,
        "runtime_entries": runtime,
        "standalone_xso": standalone,
        "mappings": mappings,
        "unmatched": {
            "standalone_only": [item["iso_path"] for item in standalone if item["mapping_status"] == "standalone_only"],
            "runtime_only": [item["runtime_key"] for item in runtime if item["mapping_status"] == "runtime_only"],
            "invalid_runtime": [item["runtime_key"] for item in runtime if item["parse_status"] != "valid"],
        },
        "errors": errors,
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(document: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "runtime_archive_xso_map.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    write_csv(output / "archive_inventory.csv", document["archives"], [
        "iso_path", "filename", "extent_lba", "file_size", "sha256", "parse_status",
        "record_count", "file_count", "xso_count", "total_xso_slack",
    ])
    mapping_rows = []
    for item in document["mappings"]:
        mapping_rows.append({**item, "standalone_paths": " | ".join(item["standalone_paths"]), "runtime_keys": " | ".join(item["runtime_keys"])})
    write_csv(output / "xso_runtime_mapping.csv", mapping_rows, [
        "xso_sha256", "status", "standalone_count", "runtime_count", "standalone_paths", "runtime_keys",
    ])
    write_csv(output / "xso_allocation_report.csv", document["runtime_entries"], [
        "runtime_key", "archive_iso_path", "entry_index", "entry_name", "flags_hex", "entry_kind", "compressed_size",
        "allocated_size", "slack_size", "allocation_ratio", "container_sha256", "xso_size",
        "xso_sha256", "string_count", "parse_status", "mapping_status", "error",
    ])
    summary = document["summary"]
    lines = ["# Ys VI 런타임 아카이브/XSO 분석 요약", ""]
    labels = {
        "archive_count": "전체 아카이브", "valid_archive_count": "정상 아카이브",
        "archive_file_count": "내부 파일 엔트리", "standalone_xso_count": "standalone XSO",
        "runtime_xso_count": "런타임 XSO", "valid_runtime_xso_count": "정상 런타임 XSO",
        "zero_slack_count": "여유 0바이트", "high_risk_90_percent_count": "할당 사용률 90% 이상",
        "error_count": "오류", "s0551_regression_valid": "s_0551 회귀 검증",
    }
    for key, label in labels.items():
        lines.append(f"- {label}: {summary[key]}")
    lines += ["", "## standalone 상태", ""]
    lines += [f"- {key}: {value}" for key, value in summary["standalone_status_counts"].items()]
    lines += ["", "## 런타임 상태", ""]
    lines += [f"- {key}: {value}" for key, value in summary["runtime_status_counts"].items()]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def validate_document(document: dict) -> list[str]:
    errors = []
    summary = document["summary"]
    if summary["standalone_xso_count"] != sum(summary["standalone_status_counts"].values()):
        errors.append("standalone status total mismatch")
    if summary["runtime_xso_count"] != sum(summary["runtime_status_counts"].values()):
        errors.append("runtime status total mismatch")
    archive_paths = {item["iso_path"] for item in document["archives"]}
    if len(archive_paths) != len(document["archives"]):
        errors.append("duplicate archive path")
    runtime_keys = {item["runtime_key"] for item in document["runtime_entries"]}
    if len(runtime_keys) != len(document["runtime_entries"]):
        errors.append("duplicate runtime key")
    if not summary["s0551_regression_valid"]:
        errors.append("s_0551 regression mapping missing")
    return errors


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    json_output = args.output / "runtime_archive_xso_map.json"
    if json_output.exists() and not args.overwrite:
        print(f"출력 파일이 이미 존재합니다: {json_output}", file=sys.stderr)
        return 2
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output) as temporary:
            document = build_document(args.iso, args.catalog, Path(temporary))
        validation_errors = validate_document(document)
        if validation_errors:
            raise RuntimeMapError("; ".join(validation_errors))
        write_outputs(document, args.output)
        print(json.dumps(document["summary"], ensure_ascii=False, indent=2))
        return 1 if document["errors"] else 0
    except (OSError, json.JSONDecodeError, RuntimeMapError) as exc:
        print(f"런타임 대응 분석 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
