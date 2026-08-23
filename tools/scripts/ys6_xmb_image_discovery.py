#!/usr/bin/env python3
"""Extract and describe PSP XMB assets from a Ys VI ISO without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from iso9660_info import Iso9660Error, SECTOR_SIZE, find_record


CANDIDATES = (
    "PSP_GAME/ICON0.PNG",
    "PSP_GAME/PIC0.PNG",
    "PSP_GAME/PIC1.PNG",
    "PSP_GAME/SND0.AT3",
    "PSP_GAME/PARAM.SFO",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def png_info(data: bytes) -> dict[str, object]:
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("유효한 PNG IHDR이 아닙니다")
    color_types = {0: "grayscale", 2: "truecolor", 3: "indexed", 4: "grayscale-alpha", 6: "truecolor-alpha"}
    color_type = data[25]
    return {
        "width": int.from_bytes(data[16:20], "big"),
        "height": int.from_bytes(data[20:24], "big"),
        "bit_depth": data[24],
        "color_type": color_type,
        "color_mode": color_types.get(color_type, "unknown"),
        "has_alpha": color_type in (4, 6) or b"tRNS" in data,
    }


def extract(iso: Path, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    with iso.open("rb") as handle:
        for internal_path in CANDIDATES:
            try:
                record = find_record(iso, internal_path)
            except Iso9660Error as exc:
                rows.append({"iso_path": internal_path, "present": False, "error": str(exc)})
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            data = handle.read(record.data_length)
            if len(data) != record.data_length:
                raise OSError(f"파일을 끝까지 읽지 못했습니다: {internal_path}")
            target = output / Path(internal_path).name
            target.write_bytes(data)
            row: dict[str, object] = {
                "iso_path": internal_path,
                "present": True,
                "record": asdict(record),
                "byte_offset": record.extent_lba * SECTOR_SIZE,
                "sha256": sha256(data),
                "output": str(target),
            }
            if target.suffix.upper() == ".PNG":
                row["image"] = png_info(data)
            rows.append(row)
    report = {"schema_version": 1, "iso": str(iso), "assets": rows}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Ys VI PSP XMB 자산 읽기 전용 추출")
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.iso, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
