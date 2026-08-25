#!/usr/bin/env python3
"""Compare two ISO9660 images by logical file paths and payload hashes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
from ys6_iso_z_search import iter_files


def digest_stream(handle, size: int) -> str:
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = handle.read(min(1024 * 1024, remaining))
        if not chunk:
            raise OSError("ISO 파일 payload를 끝까지 읽지 못했습니다")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest().upper()


def file_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return digest_stream(handle, path.stat().st_size)


def clean(path: str) -> str:
    return "/".join(part.split(";", 1)[0] for part in path.replace("\\", "/").split("/"))


def inventory(iso: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            path = clean(raw_path)
            handle.seek(record.extent_lba * SECTOR_SIZE)
            rows[path.casefold()] = {
                "path": path,
                "lba": record.extent_lba,
                "size": record.data_length,
                "sha256": digest_stream(handle, record.data_length),
            }
    return rows


def compare(first: Path, second: Path, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    a, b = inventory(first), inventory(second)
    rows: list[dict[str, object]] = []
    counts = {"identical": 0, "same_payload_moved": 0, "different": 0, "first_only": 0, "second_only": 0}
    for key in sorted(set(a) | set(b)):
        left, right = a.get(key), b.get(key)
        if left is None:
            status = "second_only"
        elif right is None:
            status = "first_only"
        elif left["sha256"] != right["sha256"] or left["size"] != right["size"]:
            status = "different"
        elif left["lba"] != right["lba"]:
            status = "same_payload_moved"
        else:
            status = "identical"
        counts[status] += 1
        rows.append({
            "path": (left or right)["path"], "status": status,
            "first_lba": left["lba"] if left else "", "second_lba": right["lba"] if right else "",
            "first_size": left["size"] if left else "", "second_size": right["size"] if right else "",
            "first_sha256": left["sha256"] if left else "", "second_sha256": right["sha256"] if right else "",
        })
    with (output / "files.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    report = {
        "schema_version": 1,
        "first": {"path": str(first), "size": first.stat().st_size, "sha256": file_digest(first), "file_count": len(a)},
        "second": {"path": str(second), "size": second.stat().st_size, "sha256": file_digest(second), "file_count": len(b)},
        "counts": counts,
        "different_files": [row for row in rows if row["status"] in {"different", "first_only", "second_only"}],
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.first, args.second, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
