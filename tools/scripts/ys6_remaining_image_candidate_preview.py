#!/usr/bin/env python3
"""Compose the five remaining Ys VI untranslated image candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_mig_collection_extract import iter_pictures, render_picture
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record
    from ys6_mig_collection_extract import iter_pictures, render_picture
    from ys6_z import verify_container_bytes


TARGETS = {
    "p901": {"rows": [[0, 1, 2, 3], [4, 5, 6, 7]], "size": [480, 272]},
    "p902": {"rows": [[0, 1, 2, 3], [4, 5, 6, 7]], "size": [480, 272]},
    "v130": {"rows": [[0, 1, 2, 3]], "size": [480, 64]},
    "v131": {"rows": [[0, 1, 2, 3]], "size": [480, 64]},
    "v132": {"rows": [[0, 1, 2, 3]], "size": [480, 64]},
}


def read_iso_file(iso: Path, path: str) -> bytes:
    record = find_record(iso, path)
    with iso.open("rb") as handle:
        handle.seek(record.extent_lba * SECTOR_SIZE)
        return handle.read(record.data_length)


def compose(payload: bytes, rows: list[list[int]], expected_size: list[int]) -> tuple[Image.Image, list[dict]]:
    pictures = {}
    picture_rows = []
    for index, _offset, _picture, palette, image_section in iter_pictures(payload):
        corrected = {**image_section, "payload": {**image_section["payload"],
                     "data_offset": image_section["payload"]["data_offset"] + 16}}
        image = render_picture(payload, palette, corrected)
        pictures[index] = image
        picture_rows.append({"picture_index": index, "width": image.width, "height": image.height})

    output = Image.new("RGBA", tuple(expected_size), (0, 0, 0, 0))
    y = 0
    placements = []
    for row in rows:
        x = 0
        row_height = pictures[row[0]].height
        for index in row:
            picture = pictures[index]
            if picture.height != row_height:
                raise ValueError(f"row height mismatch at picture {index}")
            output.alpha_composite(picture, (x, y))
            placements.append({"picture_index": index, "data_offset_adjustment": 16,
                               "x": x, "y": y,
                               "width": picture.width, "height": picture.height})
            x += picture.width
        if x != expected_size[0]:
            raise ValueError(f"row width mismatch: {x} != {expected_size[0]}")
        y += row_height
    if y != expected_size[1]:
        raise ValueError(f"total height mismatch: {y} != {expected_size[1]}")
    return output, placements


def create_contact_sheet(images: list[tuple[str, Image.Image]], output: Path) -> None:
    scale = 2
    margin = 24
    label_height = 30
    width = max(image.width * scale for _name, image in images) + margin * 2
    height = sum(image.height * scale + label_height + margin for _name, image in images) + margin
    sheet = Image.new("RGB", (width, height), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    y = margin
    for name, image in images:
        draw.text((margin, y), f"{name}.png  {image.width}x{image.height}  (2x)", fill="white")
        y += label_height
        preview = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        backdrop = Image.new("RGBA", preview.size, (48, 48, 48, 255))
        backdrop.alpha_composite(preview)
        sheet.paste(backdrop.convert("RGB"), (margin, y))
        y += preview.height + margin
    sheet.save(output)


def build(iso: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    records = []
    composed = []
    for stem, spec in TARGETS.items():
        iso_path = f"PSP_GAME/USRDIR/data/image/{stem}.dds.z"
        container = read_iso_file(iso, iso_path)
        valid, payload, error = verify_container_bytes(container)
        if not valid or payload is None:
            raise ValueError(f"{iso_path}: {error}")
        image, placements = compose(payload, spec["rows"], spec["size"])
        destination = output / f"{stem}.png"
        image.save(destination)
        composed.append((stem, image))
        records.append({"id": stem, "iso_path": iso_path, "output": str(destination),
                        "size": list(image.size), "placements": placements})
    contact_sheet = output / "candidate-contact-sheet-2x.png"
    create_contact_sheet(composed, contact_sheet)
    report = {"iso": str(iso), "candidate_count": len(records),
              "contact_sheet": str(contact_sheet), "candidates": records}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build(args.iso, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
