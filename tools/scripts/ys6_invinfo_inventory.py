#!/usr/bin/env python3
"""Compare PSP and Windows Ys VI invinfo.dat item text records."""

from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from pathlib import Path

try:
    from tools.scripts.ys6_windows_korean_codec import decode_custom, load_code_map
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.scripts.ys6_windows_korean_codec import decode_custom, load_code_map


HEADER_SIZE = 16
NAME_SIZE = 52
METADATA_SIZE = 24


def first_string(field: bytes) -> bytes:
    """Return the displayed string and ignore stale bytes after its first NUL."""
    return field.split(b"\0", 1)[0]


def parse_header(data: bytes) -> tuple[int, int]:
    if len(data) < HEADER_SIZE:
        raise ValueError("invinfo.dat is shorter than its header")
    record_size, count = struct.unpack_from("<II", data, 8)
    if record_size < NAME_SIZE + METADATA_SIZE:
        raise ValueError(f"invalid record size: {record_size}")
    expected = HEADER_SIZE + record_size * count
    if len(data) != expected:
        raise ValueError(f"file size mismatch: expected {expected}, got {len(data)}")
    return record_size, count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psp", type=Path, required=True)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--code-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    psp = args.psp.read_bytes()
    windows = args.windows.read_bytes()
    psp_record_size, psp_count = parse_header(psp)
    win_record_size, win_count = parse_header(windows)
    if (psp_record_size, psp_count) != (win_record_size, win_count):
        raise ValueError("PSP and Windows record layouts differ")

    mapping = load_code_map(args.code_map)
    rows = []
    metadata_mismatch = []
    for index in range(psp_count):
        start = HEADER_SIZE + index * psp_record_size
        p_record = psp[start:start + psp_record_size]
        w_record = windows[start:start + psp_record_size]
        metadata_start = NAME_SIZE
        description_start = NAME_SIZE + METADATA_SIZE
        if p_record[metadata_start:description_start] != w_record[metadata_start:description_start]:
            metadata_mismatch.append(index)

        p_name_raw = first_string(p_record[:NAME_SIZE])
        p_desc_raw = first_string(p_record[description_start:])
        w_name_raw = first_string(w_record[:NAME_SIZE])
        w_desc_raw = first_string(w_record[description_start:])
        ko_name, name_unresolved = decode_custom(w_name_raw, mapping)
        ko_desc, desc_unresolved = decode_custom(w_desc_raw, mapping)
        rows.append({
            "index": index,
            "resource_id": first_string(p_record[NAME_SIZE:NAME_SIZE + 10]).decode("ascii", "replace"),
            "japanese_name": p_name_raw.decode("cp932", "replace"),
            "korean_name": ko_name,
            "japanese_description": p_desc_raw.decode("cp932", "replace"),
            "korean_description": ko_desc,
            "name_unresolved_codes": name_unresolved,
            "description_unresolved_codes": desc_unresolved,
        })

    args.output.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": 1,
        "record_size": psp_record_size,
        "record_count": psp_count,
        "layout": {
            "name": [0, NAME_SIZE],
            "metadata": [NAME_SIZE, NAME_SIZE + METADATA_SIZE],
            "description": [NAME_SIZE + METADATA_SIZE, psp_record_size],
        },
        "metadata_mismatch_indices": metadata_mismatch,
        "items": rows,
    }
    (args.output / "items.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "items.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "index", "resource_id", "japanese_name", "korean_name",
            "japanese_description", "korean_description",
            "name_unresolved_codes", "description_unresolved_codes",
        ])
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["name_unresolved_codes"] = " ".join(row["name_unresolved_codes"])
            csv_row["description_unresolved_codes"] = " ".join(row["description_unresolved_codes"])
            writer.writerow(csv_row)

    print(json.dumps({
        "record_count": psp_count,
        "metadata_mismatch_count": len(metadata_mismatch),
        "unresolved_item_count": sum(
            bool(row["name_unresolved_codes"] or row["description_unresolved_codes"]) for row in rows
        ),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
