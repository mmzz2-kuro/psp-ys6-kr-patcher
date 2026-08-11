#!/usr/bin/env python3
"""Search every Ys VI .z payload in an ISO without extracting the ISO."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

from iso9660_info import DirectoryRecord, PVD_SECTOR, SECTOR_SIZE, parse_record


def read_directory_relaxed(handle, record):
    handle.seek(record.extent_lba * SECTOR_SIZE)
    data = handle.read(record.data_length)
    offset = 0
    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset = ((offset // SECTOR_SIZE) + 1) * SECTOR_SIZE
            continue
        raw_name = data[offset + 33 : offset + 33 + data[offset + 32]]
        if raw_name not in (b"\x00", b"\x01"):
            yield DirectoryRecord(
                raw_name.decode("cp932"),
                struct.unpack_from("<I", data, offset + 2)[0],
                struct.unpack_from("<I", data, offset + 10)[0],
                bool(data[offset + 25] & 0x02),
                record.extent_lba * SECTOR_SIZE + offset,
            )
        offset += length


def iter_files(handle, root):
    stack = [("", root)]
    while stack:
        base, directory = stack.pop()
        for entry in read_directory_relaxed(handle, directory):
            path = f"{base}/{entry.name}".lstrip("/")
            if entry.is_directory:
                stack.append((path, entry))
            else:
                yield path, entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("needle", type=Path, help="decompressed byte sequence to find")
    args = parser.parse_args()
    needle = args.needle.read_bytes()
    hits = []
    errors = []
    checked = 0
    with args.iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for path, entry in iter_files(handle, root):
            if not entry.name.split(";", 1)[0].lower().endswith(".z"):
                continue
            checked += 1
            handle.seek(entry.extent_lba * SECTOR_SIZE)
            container = handle.read(entry.data_length)
            try:
                payload = zlib.decompress(container[8:])
            except (zlib.error, ValueError) as exc:
                errors.append({"path": path, "error": str(exc)})
                continue
            offset = payload.find(needle)
            if offset >= 0:
                hits.append(
                    {
                        "path": path,
                        "payload_offset": offset,
                        "payload_size": len(payload),
                        "payload_sha256": hashlib.sha256(payload).hexdigest().upper(),
                    }
                )
    print(
        json.dumps(
            {
                "iso": str(args.iso),
                "needle": str(args.needle),
                "needle_size": len(needle),
                "z_checked": checked,
                "hits": hits,
                "error_count": len(errors),
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if hits else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
