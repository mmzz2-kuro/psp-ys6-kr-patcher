#!/usr/bin/env python3
"""Inventory Ys VI PSP non-dialogue strings and texture candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_iso_z_search import iter_files
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_iso_z_search import iter_files

JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
PRINTABLE = re.compile(r"^[\x20-\x7e\u3000-\u30ff\u3400-\u9fff\uff01-\uff5e]+$")
SYSTEM_WORDS = re.compile(r"(?i)(system|menu|item|shop|save|load|option|status|battle|magic|weapon|armor|access|help|title|caption|name|info|data|init|common)")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def decode_candidates(data: bytes, minimum: int = 2) -> list[dict]:
    rows = []
    start = 0
    for end in range(len(data) + 1):
        if end < len(data) and data[end] != 0:
            continue
        raw = data[start:end]
        start = end + 1
        if len(raw) < minimum:
            continue
        try:
            text = raw.decode("cp932")
        except UnicodeDecodeError:
            continue
        if len(text) < minimum or not JAPANESE.search(text) or not PRINTABLE.match(text):
            continue
        if text.encode("cp932") != raw:
            continue
        rows.append({"offset": end - len(raw), "byte_length": len(raw), "text": text})
    return rows


def mig_info(data: bytes) -> dict | None:
    if not data.startswith(b"MIG.00.1PSP"):
        return None
    words = [struct.unpack_from("<I", data, offset)[0] for offset in range(0, min(len(data), 128) - 3, 4)]
    return {
        "magic": data[:12].decode("ascii", "replace"),
        "payload_size": len(data),
        "header_hex": data[:128].hex().upper(),
        "header_u32_le": words,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files, strings, textures, errors = [], [], [], []
    with args.iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for iso_path, entry in iter_files(handle, root):
            handle.seek(entry.extent_lba * SECTOR_SIZE)
            stored = handle.read(entry.data_length)
            clean_path = iso_path.split(";", 1)[0]
            extension = Path(clean_path).suffix.lower()
            payload, compression = stored, "none"
            if clean_path.lower().endswith(".z"):
                try:
                    payload = zlib.decompress(stored[8:])
                    compression = "ys6_zlib"
                except zlib.error as exc:
                    errors.append({"iso_path": clean_path, "error": str(exc)})
            magic = payload[:16].rstrip(b"\0").decode("ascii", "replace")
            record = {
                "iso_path": clean_path, "stored_size": len(stored), "payload_size": len(payload),
                "extension": extension, "compression": compression, "stored_sha256": sha256(stored),
                "payload_sha256": sha256(payload), "magic_ascii": magic,
                "system_name_hint": bool(SYSTEM_WORDS.search(clean_path)),
            }
            files.append(record)
            if not clean_path.lower().endswith(".xso.z") and len(payload) <= 32 * 1024 * 1024:
                for candidate in decode_candidates(payload):
                    strings.append({"iso_path": clean_path, "payload_sha256": record["payload_sha256"], **candidate})
            info = mig_info(payload)
            if info:
                textures.append({"iso_path": clean_path, "stored_sha256": record["stored_sha256"], **info})

    extension_counts = Counter(row["extension"] for row in files)
    string_file_counts = Counter(row["iso_path"] for row in strings)
    summary = {
        "schema_version": 1, "iso": str(args.iso), "iso_sha256": file_sha256(args.iso),
        "file_count": len(files), "extension_counts": dict(extension_counts.most_common()),
        "japanese_candidate_count": len(strings), "japanese_candidate_file_count": len(string_file_counts),
        "top_japanese_candidate_files": [{"iso_path": path, "count": count} for path, count in string_file_counts.most_common(100)],
        "mig_texture_count": len(textures), "error_count": len(errors), "errors": errors,
    }
    (args.output_dir / "inventory.json").write_text(json.dumps({"summary": summary, "files": files, "textures": textures}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "japanese-strings.json").write_text(json.dumps({"schema_version": 1, "records": strings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "japanese-strings.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("iso_path", "offset", "byte_length", "text", "payload_sha256")); writer.writeheader(); writer.writerows(strings)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
