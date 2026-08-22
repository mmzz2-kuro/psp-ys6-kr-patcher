#!/usr/bin/env python3
"""Extract and locate the v100-v108 Zemes sanctuary statue messages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record, parse_record
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_mig_collection_extract import iter_pictures, render_picture
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record, parse_record
    from ys6_arc import DATA_FLAGS, parse_archive
    from ys6_iso_z_search import iter_files
    from ys6_mig_collection_extract import iter_pictures, render_picture
    from ys6_z import verify_container_bytes


STEMS = [f"v{index}" for index in range(100, 109)]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, default=Path("roms/Ys VI - Napishtim no Hako (Japan).iso"))
    parser.add_argument("--output", type=Path,
                        default=Path("tools/patchdata/work/current/image-discovery/zemes-statue-messages"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    sources: dict[str, dict] = {}
    previews: list[tuple[str, Image.Image]] = []
    with args.iso.open("rb") as handle:
        for stem in STEMS:
            iso_path = f"PSP_GAME/USRDIR/data/image/{stem}.dds.z"
            record = find_record(args.iso, iso_path)
            handle.seek(record.extent_lba * SECTOR_SIZE)
            container = handle.read(record.data_length)
            valid, payload, error = verify_container_bytes(container)
            if not valid or payload is None:
                raise ValueError(f"{stem}: invalid container: {error}")
            pictures = list(iter_pictures(payload))
            if len(pictures) != 1:
                raise ValueError(f"{stem}: expected one picture, got {len(pictures)}")
            picture_index, _offset, _picture, palette, image_section = pictures[0]
            image = render_picture(payload, palette, image_section)
            image.save(args.output / f"{stem}.png")
            previews.append((stem, image))
            sources[f"{stem}.dds.z"] = {
                "iso_path": iso_path,
                "extent_lba": record.extent_lba,
                "container_size": record.data_length,
                "allocated_size": ((record.data_length + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE,
                "container_sha256": sha256(container),
                "payload_sha256": sha256(payload),
                "picture_index": picture_index,
                "width": image.width,
                "height": image.height,
                "pixel_format": image_section["payload"]["pixel_format"],
                "alpha_bbox": list(image.getbbox()) if image.getbbox() else None,
            }

        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        root = parse_record(handle.read(SECTOR_SIZE), 156, PVD_SECTOR * SECTOR_SIZE)
        copies = {stem: [] for stem in STEMS}
        archive_count = 0
        for raw_path, record in iter_files(handle, root):
            archive_path = raw_path.split(";", 1)[0]
            if not archive_path.startswith("PSP_GAME/USRDIR/data/arc/") or not archive_path.lower().endswith(".bin"):
                continue
            archive_count += 1
            handle.seek(record.extent_lba * SECTOR_SIZE)
            archive = handle.read(record.data_length)
            for entry in parse_archive(archive):
                source = sources.get(entry.name.casefold())
                if source is None or entry.flags not in DATA_FLAGS or entry.size <= 0:
                    continue
                data = archive[entry.offset:entry.offset + entry.size]
                valid, payload, _error = verify_container_bytes(data)
                stem = entry.name[:-6].casefold()
                copies[stem].append({
                    "archive_path": archive_path,
                    "entry_index": entry.index,
                    "flags_hex": f"0x{entry.flags:08X}",
                    "container_size": entry.size,
                    "allocated_size": entry.allocated_size,
                    "container_sha256": sha256(data),
                    "payload_sha256": sha256(payload) if valid and payload is not None else None,
                    "exact_container_match": sha256(data) == source["container_sha256"],
                    "exact_payload_match": bool(valid and payload is not None and sha256(payload) == source["payload_sha256"]),
                })

    sheet = Image.new("RGBA", (768, 288), (28, 28, 28, 255))
    draw = ImageDraw.Draw(sheet)
    for position, (stem, preview) in enumerate(previews):
        left = (position % 3) * 256
        top = (position // 3) * 96
        sheet.alpha_composite(preview, (left, top + 24))
        draw.text((left + 6, top + 5), f"{stem} 256x64", fill=(255, 255, 255, 255))
    sheet.save(args.output / "contact-sheet.png")

    report = {
        "source_iso": str(args.iso),
        "resource_count": len(sources),
        "archive_count": archive_count,
        "sources": sources,
        "runtime_copies": copies,
        "runtime_copy_counts": {stem: len(rows) for stem, rows in copies.items()},
    }
    (args.output / "discovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "resource_count": report["resource_count"],
        "runtime_copy_counts": report["runtime_copy_counts"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
