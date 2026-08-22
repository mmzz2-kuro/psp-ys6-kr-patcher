#!/usr/bin/env python3
"""Inventory unique Ys VI runtime DDS images absent from standalone resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_mig_collection_extract import iter_pictures, render_picture
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_arc import DATA_FLAGS, parse_archive
    from ys6_iso_z_search import iter_files
    from ys6_mig_collection_extract import iter_pictures, render_picture
    from ys6_z import verify_container_bytes


ARC_PREFIX = "PSP_GAME/USRDIR/data/arc/"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def build_audit(iso: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    images_dir = output / "runtime-only-images"
    images_dir.mkdir(parents=True, exist_ok=True)

    standalone_by_hash: dict[str, list[str]] = defaultdict(list)
    archive_rows: list[dict] = []
    unique_payloads: dict[str, dict] = {}
    errors: list[dict] = []

    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        root = parse_record(handle.read(SECTOR_SIZE), 156, PVD_SECTOR * SECTOR_SIZE)
        files = [(raw.split(";", 1)[0], record) for raw, record in iter_files(handle, root)]

        for path, record in files:
            if path.startswith(ARC_PREFIX) or not path.lower().endswith(".dds.z"):
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            valid, payload, _error = verify_container_bytes(handle.read(record.data_length))
            if valid and payload is not None:
                standalone_by_hash[digest(payload)].append(path)

        for archive_path, record in files:
            if not archive_path.startswith(ARC_PREFIX) or not archive_path.lower().endswith(".bin"):
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            archive_data = handle.read(record.data_length)
            try:
                entries = parse_archive(archive_data)
            except Exception as exc:
                errors.append({"archive": archive_path, "error": str(exc)})
                continue
            for entry in entries:
                if entry.flags not in DATA_FLAGS or entry.size <= 0 or not entry.name.lower().endswith(".dds.z"):
                    continue
                container = archive_data[entry.offset:entry.offset + entry.size]
                valid, payload, error = verify_container_bytes(container)
                if not valid or payload is None:
                    errors.append({"archive": archive_path, "entry_index": entry.index,
                                   "entry_name": entry.name, "error": error})
                    continue
                payload_hash = digest(payload)
                runtime_key = f"{archive_path}#{entry.index}:{entry.name}"
                row = {"runtime_key": runtime_key, "archive": archive_path,
                       "entry_index": entry.index, "entry_name": entry.name,
                       "payload_sha256": payload_hash, "payload_size": len(payload),
                       "matches_standalone": payload_hash in standalone_by_hash,
                       "standalone_paths": standalone_by_hash.get(payload_hash, [])}
                archive_rows.append(row)
                if payload_hash not in standalone_by_hash:
                    unique_payloads.setdefault(payload_hash, {"payload": payload, "runtime_keys": []})["runtime_keys"].append(runtime_key)

    picture_rows: list[dict] = []
    previews: list[tuple[str, int, Image.Image]] = []
    for sequence, (payload_hash, item) in enumerate(sorted(unique_payloads.items()), 1):
        payload = item.pop("payload")
        try:
            pictures = list(iter_pictures(payload))
        except Exception as exc:
            item["render_error"] = str(exc)
            continue
        for picture_index, _picture_offset, _picture, palette, image_section in pictures:
            info = image_section["payload"]
            row = {"payload_sha256": payload_hash, "runtime_keys": item["runtime_keys"],
                   "picture_index": picture_index, "width": info["width"],
                   "height": info["height"], "pixel_format": info["pixel_format"]}
            try:
                image = render_picture(payload, palette, image_section)
                filename = f"{sequence:04d}-{safe_name(Path(item['runtime_keys'][0]).name)}-{picture_index:03d}.png"
                image.save(images_dir / filename)
                row.update({"rendered": True, "png": str(images_dir / filename)})
                if image.width >= 64 and image.height >= 16:
                    previews.append((item["runtime_keys"][0], picture_index, image))
            except Exception as exc:
                row.update({"rendered": False, "error": str(exc)})
            picture_rows.append(row)

    cell_width, cell_height, columns, per_page = 320, 304, 4, 24
    page_count = math.ceil(len(previews) / per_page)
    for page_index in range(page_count):
        page = previews[page_index * per_page:(page_index + 1) * per_page]
        sheet = Image.new("RGB", (cell_width * columns, cell_height * math.ceil(len(page) / columns)), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for position, (runtime_key, picture_index, source) in enumerate(page):
            left = position % columns * cell_width
            top = position // columns * cell_height
            preview = source.copy()
            preview.thumbnail((288, 256), Image.Resampling.NEAREST)
            dark = Image.new("RGBA", preview.size, (32, 32, 32, 255))
            dark.alpha_composite(preview.convert("RGBA"))
            sheet.paste(dark.convert("RGB"), (left + 16, top + 40))
            draw.text((left + 16, top + 12), f"{Path(runtime_key).name} [{picture_index}] {source.width}x{source.height}", fill="white")
        sheet.save(output / f"runtime-only-contact-sheet-{page_index + 1:02d}.png")

    report = {
        "iso": str(iso), "standalone_payload_hash_count": len(standalone_by_hash),
        "runtime_dds_entry_count": len(archive_rows),
        "runtime_dds_matching_standalone_count": sum(row["matches_standalone"] for row in archive_rows),
        "runtime_only_unique_payload_count": len(unique_payloads),
        "runtime_only_picture_count": len(picture_rows), "preview_count": len(previews),
        "contact_sheet_count": page_count, "runtime_entries": archive_rows,
        "runtime_only_payloads": unique_payloads, "pictures": picture_rows, "errors": errors,
    }
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_audit(args.iso, args.output)
    print(json.dumps({key: report[key] for key in (
        "standalone_payload_hash_count", "runtime_dds_entry_count",
        "runtime_dds_matching_standalone_count", "runtime_only_unique_payload_count",
        "runtime_only_picture_count", "preview_count", "contact_sheet_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
