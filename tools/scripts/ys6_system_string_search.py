#!/usr/bin/env python3
"""Search Ys VI PSP/Windows resources for exact system-message variants."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_windows_archive import read_entry, read_index
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_arc import DATA_FLAGS, parse_archive
    from ys6_iso_z_search import iter_files
    from ys6_windows_archive import read_entry, read_index


DEFAULT_TEXTS = (
    "データをセーブします", "データをセーブします。", "データをセーブしますか",
    "データをセーブしますか？", "セーブします", "セーブしますか", "セーブ",
)


def patterns(texts: list[str]) -> list[dict]:
    rows = []
    for text in dict.fromkeys(texts):
        for encoding in ("cp932", "utf-16le", "utf-16be"):
            rows.append({"text": text, "encoding": encoding, "bytes": text.encode(encoding)})
    return rows


def find_all(data: bytes, variants: list[dict], location: dict) -> list[dict]:
    hits = []
    for variant in variants:
        start = 0
        while True:
            offset = data.find(variant["bytes"], start)
            if offset < 0: break
            before, after = max(0, offset - 32), min(len(data), offset + len(variant["bytes"]) + 32)
            hits.append({**location, "offset": offset, "text": variant["text"],
                         "encoding": variant["encoding"], "match_hex": variant["bytes"].hex().upper(),
                         "context_hex": data[before:after].hex().upper()})
            start = offset + 1
    return hits


def unwrap_z(data: bytes) -> tuple[bytes, bool]:
    if len(data) >= 8:
        try: return zlib.decompress(data[8:]), True
        except zlib.error: pass
    return data, False


def search_psp(iso: Path, variants: list[dict]) -> tuple[list[dict], dict]:
    hits, errors = [], []
    files = decompressed = archives = entries = 0
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            iso_path = raw_path.split(";", 1)[0]
            handle.seek(record.extent_lba * SECTOR_SIZE)
            stored = handle.read(record.data_length); files += 1
            hits += find_all(stored, variants, {"source": "psp", "iso_path": iso_path, "layer": "stored"})
            payload, was_z = unwrap_z(stored)
            if was_z:
                decompressed += 1
                hits += find_all(payload, variants, {"source": "psp", "iso_path": iso_path, "layer": "z_payload"})
            if iso_path.lower().startswith("psp_game/usrdir/data/arc/") and iso_path.lower().endswith(".bin"):
                try:
                    archive_entries = parse_archive(payload); archives += 1
                except Exception as exc:
                    errors.append({"iso_path": iso_path, "error": str(exc)}); continue
                for entry in archive_entries:
                    if entry.flags not in DATA_FLAGS or entry.size <= 0: continue
                    entries += 1
                    child = payload[entry.offset:entry.offset + entry.size]
                    hits += find_all(child, variants, {"source": "psp", "iso_path": iso_path,
                        "layer": "archive_entry", "entry_index": entry.index, "entry_name": entry.name,
                        "entry_flags": f"0x{entry.flags:08X}"})
                    child_payload, child_z = unwrap_z(child)
                    if child_z:
                        hits += find_all(child_payload, variants, {"source": "psp", "iso_path": iso_path,
                            "layer": "archive_entry_z_payload", "entry_index": entry.index,
                            "entry_name": entry.name, "entry_flags": f"0x{entry.flags:08X}"})
    return hits, {"files": files, "z_payloads": decompressed, "archives": archives,
                  "archive_entries": entries, "errors": errors}


def search_windows(ni: Path, na: Path, variants: list[dict]) -> tuple[list[dict], dict]:
    hits, errors, checked = [], [], 0
    for entry in read_index(ni):
        if (entry.offset, entry.packed_size) == (0, 0): continue
        try: data = read_entry(na, entry).data
        except Exception as exc:
            errors.append({"entry_index": entry.index, "entry_name": entry.name, "error": str(exc)}); continue
        checked += 1
        hits += find_all(data, variants, {"source": "windows", "entry_index": entry.index,
                                         "entry_name": entry.name, "layer": "archive_payload"})
    return hits, {"entries": checked, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--windows-ni", type=Path)
    parser.add_argument("--windows-na", type=Path)
    parser.add_argument("--text", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    texts = list(DEFAULT_TEXTS) + args.text
    variants = patterns(texts)
    psp_hits, psp_stats = search_psp(args.iso, variants)
    windows_hits, windows_stats = [], None
    if args.windows_ni:
        na = args.windows_na or args.windows_ni.with_suffix(".na")
        windows_hits, windows_stats = search_windows(args.windows_ni, na, variants)
    result = {"schema_version": 1, "texts": texts, "pattern_count": len(variants),
              "psp": psp_stats, "windows": windows_stats, "hit_count": len(psp_hits) + len(windows_hits),
              "hits": psp_hits + windows_hits}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pattern_count": len(variants), "psp": psp_stats, "windows": windows_stats,
                      "hit_count": result["hit_count"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
