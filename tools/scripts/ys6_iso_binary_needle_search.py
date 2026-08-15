#!/usr/bin/env python3
"""Search raw ISO files and decompressed Z payloads for a binary slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_iso_z_search import iter_files
    from ys6_z import verify_container_bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def execute(iso: Path, reference: Path, offset: int, length: int, extract_dir: Path | None = None) -> dict:
    source = reference.read_bytes()
    needle = source[offset:offset + length]
    if len(needle) != length or not needle:
        raise ValueError("reference slice is outside the file")
    raw_hits = []; decompressed_hits = []; checked = z_checked = 0
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE); pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            checked += 1
            handle.seek(record.extent_lba * SECTOR_SIZE); data = handle.read(record.data_length)
            position = data.find(needle)
            if position >= 0:
                raw_hits.append({"iso_path": path, "file_offset": position, "file_size": len(data), "file_sha256": sha256(data)})
            if path.casefold().endswith(".z"):
                z_checked += 1
                valid, payload, _error = verify_container_bytes(data)
                if valid and payload is not None:
                    position = payload.find(needle)
                    if position >= 0:
                        row = {"iso_path": path, "payload_offset": position, "payload_size": len(payload), "payload_sha256": sha256(payload)}
                        if extract_dir is not None:
                            extract_dir.mkdir(parents=True, exist_ok=True)
                            stem = Path(path).name.removesuffix(".z")
                            container_path = extract_dir / f"{stem}.z"
                            payload_path = extract_dir / stem
                            container_path.write_bytes(data); payload_path.write_bytes(payload)
                            row.update({"extracted_container": str(container_path), "extracted_payload": str(payload_path)})
                        decompressed_hits.append(row)
    return {
        "schema_version": 1, "iso": str(iso), "reference": str(reference),
        "slice_offset": offset, "slice_length": length, "slice_sha256": sha256(needle),
        "files_checked": checked, "z_checked": z_checked,
        "raw_hits": raw_hits, "decompressed_hits": decompressed_hits,
    }


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path); parser.add_argument("reference", type=Path)
    parser.add_argument("--offset", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--length", type=lambda value: int(value, 0), default=64)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--extract-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        report = execute(args.iso, args.reference, args.offset, args.length, args.extract_dir)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end=""); return 0
    except (OSError, ValueError) as exc:
        print(f"ISO 바이너리 조각 검색 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
