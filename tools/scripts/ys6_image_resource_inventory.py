#!/usr/bin/env python3
"""Build a PNG/contact-sheet inventory of Ys VI PSP UI image resources."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_mig_collection_extract import iter_pictures, render_picture
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_iso_z_search import iter_files
    from ys6_mig_collection_extract import iter_pictures, render_picture
    from ys6_z import verify_container_bytes


DEFAULT_PREFIXES = (
    "PSP_GAME/USRDIR/data/menu/",
    "PSP_GAME/USRDIR/data/image/",
    "PSP_GAME/USRDIR/data/title/",
)


def safe_name(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path).strip("_")


def inventory(iso: Path, output: Path, prefixes: tuple[str, ...]) -> dict:
    images_dir = output / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    records = []
    previews = []
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        root = parse_record(handle.read(SECTOR_SIZE), 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            if not path.lower().endswith(".dds.z") or not any(path.startswith(prefix) for prefix in prefixes):
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            container = handle.read(record.data_length)
            valid, payload, error = verify_container_bytes(container)
            base = {
                "iso_path": path,
                "extent_lba": record.extent_lba,
                "container_size": record.data_length,
                "allocated_size": math.ceil(record.data_length / SECTOR_SIZE) * SECTOR_SIZE,
            }
            if not valid or payload is None:
                records.append({**base, "valid": False, "error": error})
                continue
            try:
                pictures = list(iter_pictures(payload))
            except Exception as exc:
                records.append({**base, "valid": True, "rendered": False, "error": str(exc)})
                continue
            for picture_index, _picture_offset, _picture, palette, image_section in pictures:
                info = image_section["payload"]
                row = {
                    **base,
                    "valid": True,
                    "picture_index": picture_index,
                    "width": info["width"],
                    "height": info["height"],
                    "pixel_format": info["pixel_format"],
                }
                try:
                    image = render_picture(payload, palette, image_section)
                    name = f"{safe_name(path)}__{picture_index:03d}.png"
                    image.save(images_dir / name)
                    row["rendered"] = True
                    row["png"] = str(images_dir / name)
                    if image.width >= 64 and image.height >= 16:
                        previews.append((path, picture_index, image))
                except Exception as exc:
                    row["rendered"] = False
                    row["error"] = str(exc)
                records.append(row)

    cell_width, cell_height, columns, per_page = 320, 304, 4, 24
    for page_index in range(math.ceil(len(previews) / per_page)):
        page_rows = previews[page_index * per_page:(page_index + 1) * per_page]
        rows = math.ceil(len(page_rows) / columns)
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for position, (path, picture_index, image) in enumerate(page_rows):
            left = position % columns * cell_width
            top = position // columns * cell_height
            preview = image.copy()
            preview.thumbnail((288, 256), Image.Resampling.NEAREST)
            dark = Image.new("RGBA", preview.size, (32, 32, 32, 255))
            dark.alpha_composite(preview.convert("RGBA"))
            sheet.paste(dark.convert("RGB"), (left + 16, top + 40))
            label = f"{Path(path).name} [{picture_index}] {image.width}x{image.height}"
            draw.text((left + 16, top + 12), label, fill="white")
        sheet.save(output / f"contact-sheet-{page_index + 1:02d}.png")

    report = {
        "iso": str(iso),
        "prefixes": list(prefixes),
        "record_count": len(records),
        "rendered_count": sum(bool(row.get("rendered")) for row in records),
        "preview_count": len(previews),
        "contact_sheet_count": math.ceil(len(previews) / per_page),
        "resources": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix", action="append")
    args = parser.parse_args()
    prefixes = tuple(args.prefix) if args.prefix else DEFAULT_PREFIXES
    report = inventory(args.iso, args.output, prefixes)
    print(json.dumps({key: report[key] for key in (
        "record_count", "rendered_count", "preview_count", "contact_sheet_count"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
