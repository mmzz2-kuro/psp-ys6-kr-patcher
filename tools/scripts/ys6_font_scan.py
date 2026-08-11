#!/usr/bin/env python3
"""Scan a Ys VI PSP ISO for embedded font and texture-atlas candidates."""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
from ys6_iso_z_search import iter_files


KNOWN_MAGICS = (b"PGF0", b"PGF", b"BWFO", b"BWFON", b"GIM.", b"MIG.")


def dds_info(data: bytes) -> dict | None:
    if len(data) < 128 or data[:4] != b"DDS ":
        return None
    height, width = struct.unpack_from("<II", data, 12)
    pixel_flags = struct.unpack_from("<I", data, 80)[0]
    fourcc = data[84:88].rstrip(b"\0").decode("ascii", "replace")
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    return {"width": width, "height": height, "pixel_flags": f"0x{pixel_flags:08X}", "fourcc": fourcc, "rgb_bits": rgb_bits}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    known_hits = []
    dds_files = []
    errors = []
    checked = 0
    with args.iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for path, entry in iter_files(handle, root):
            checked += 1
            handle.seek(entry.extent_lba * SECTOR_SIZE)
            stored = handle.read(entry.data_length)
            payload = stored
            if entry.name.split(";", 1)[0].lower().endswith(".z"):
                try:
                    payload = zlib.decompress(stored[8:])
                except zlib.error as exc:
                    errors.append({"path": path, "error": str(exc)})
                    continue
            for magic in KNOWN_MAGICS:
                offset = payload.find(magic)
                if offset >= 0:
                    known_hits.append({"path": path, "magic": magic.decode("ascii", "replace"), "offset": offset, "payload_size": len(payload)})
            info = dds_info(payload)
            if info:
                info.update({"path": path, "stored_size": entry.data_length, "payload_size": len(payload)})
                dds_files.append(info)
    dimensions = Counter((item["width"], item["height"]) for item in dds_files)
    likely_atlases = [
        item for item in dds_files
        if item["width"] >= 128 and item["height"] >= 128
        and (item["width"] % 16 == 0 and item["height"] % 16 == 0)
    ]
    likely_atlases.sort(key=lambda item: (-item["width"] * item["height"], item["path"].casefold()))
    result = {
        "iso": str(args.iso),
        "files_checked": checked,
        "known_magic_hits": known_hits,
        "dds_count": len(dds_files),
        "dds_dimensions": [
            {"width": width, "height": height, "count": count}
            for (width, height), count in dimensions.most_common()
        ],
        "likely_atlases": likely_atlases,
        "error_count": len(errors),
        "errors": errors,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
