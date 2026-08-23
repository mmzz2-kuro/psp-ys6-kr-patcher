#!/usr/bin/env python3
"""List and losslessly extract movie files from a Ys VI PSP ISO."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_iso_z_search import iter_files
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_iso_z_search import iter_files


MOVIE_EXTENSIONS = (".pmf", ".mps", ".pss", ".mpg", ".mpeg", ".avi")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def extract_movies(iso: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        root = parse_record(handle.read(SECTOR_SIZE), 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            if not path.lower().endswith(MOVIE_EXTENSIONS):
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            data = handle.read(record.data_length)
            destination = output / Path(path).name
            destination.write_bytes(data)
            rows.append({
                "iso_path": path,
                "extent_lba": record.extent_lba,
                "size": len(data),
                "sha256": sha256(data),
                "magic_hex": data[:16].hex().upper(),
                "output": destination.as_posix(),
            })
    report = {"iso": str(iso), "movie_count": len(rows), "movies": rows}
    (output / "extract-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract_movies(args.iso, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
