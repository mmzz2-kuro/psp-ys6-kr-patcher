#!/usr/bin/env python3
"""Compose Ys VI p2xx split MIG pictures into 480x272 research previews."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

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


STEMS = ["p200", "p201", "p210", "p211", "p212", "p220", "p221", "p222", "p230", "p231", "p232", "p240", "p241", "p242"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def rotate_blocks(image: Image.Image, offset: int) -> Image.Image:
    blocks = [image.crop((x, y, x + 4, y + 4)) for y in range(0, image.height, 4) for x in range(0, image.width, 4)]
    offset %= len(blocks)
    blocks = blocks[offset:] + blocks[:offset]
    output = Image.new("RGBA", image.size)
    columns = image.width // 4
    for index, block in enumerate(blocks):
        output.paste(block, ((index % columns) * 4, (index // columns) * 4))
    return output


def compose(files: list[Path], block_offset: int = 0) -> Image.Image:
    if len(files) != 8:
        raise ValueError(f"expected 8 pictures, got {len(files)}")
    pictures = [rotate_blocks(Image.open(path).convert("RGBA"), block_offset) for path in files]
    output = Image.new("RGBA", (480, 272))
    x = 0
    for picture in pictures[:4]:
        output.paste(picture, (x, 0))
        x += picture.width
    x = 0
    for picture in pictures[4:]:
        output.paste(picture, (x, 256))
        x += picture.width
    return output


def compose_images(pictures: list[Image.Image]) -> Image.Image:
    output = Image.new("RGBA", (480, 272))
    x = 0
    for picture in pictures[:4]:
        output.paste(picture, (x, 0))
        x += picture.width
    x = 0
    for picture in pictures[4:]:
        output.paste(picture, (x, 256))
        x += picture.width
    return output


def render_collection_without_prefix_blocks(payload: bytes) -> Image.Image:
    pictures = []
    for _index, _offset, _picture, palette, image in iter_pictures(payload):
        corrected = {**image, "payload": {**image["payload"], "data_offset": image["payload"]["data_offset"] + 16}}
        pictures.append(render_picture(payload, palette, corrected))
    if len(pictures) != 8:
        raise ValueError(f"expected 8 collection pictures, got {len(pictures)}")
    return compose_images(pictures)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("tools/patchdata/work/current/image-discovery/ui-inventory/images"))
    parser.add_argument("--output", type=Path, default=Path("tools/patchdata/work/current/image-discovery/tabulas"))
    parser.add_argument("--iso", type=Path, default=Path("roms/Ys VI - Napishtim no Hako (Japan).iso"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = []
    for stem in STEMS:
        files = sorted(args.inventory.glob(f"*_{stem}.dds.z__*.png"))
        image = compose(files, block_offset=2)
        output = args.output / f"{stem}.png"
        image.save(output)
        report.append({"id": stem, "source_count": len(files), "size": list(image.size), "output": output.as_posix()})
    (args.output / "compose-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sources = {}
    with args.iso.open("rb") as handle:
        for stem in STEMS:
            path = f"PSP_GAME/USRDIR/data/image/{stem}.dds.z"
            record = find_record(args.iso, path)
            handle.seek(record.extent_lba * SECTOR_SIZE)
            container = handle.read(record.data_length)
            valid, payload, error = verify_container_bytes(container)
            if not valid or payload is None:
                raise ValueError(f"invalid source {path}: {error}")
            sources[f"{stem}.dds.z"] = {
                "iso_path": path, "container": container, "payload": payload,
                "container_size": len(container),
                "allocated_size": ((len(container) + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE,
                "container_sha256": sha256(container), "payload_sha256": sha256(payload),
            }
            corrected = render_collection_without_prefix_blocks(payload)
            corrected.save(args.output / f"{stem}.png")

        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        root = parse_record(handle.read(SECTOR_SIZE), 156, PVD_SECTOR * SECTOR_SIZE)
        copies = {stem: [] for stem in STEMS}
        archive_count = 0
        for raw_path, record in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            if not path.startswith("PSP_GAME/USRDIR/data/arc/") or not path.lower().endswith(".bin"):
                continue
            archive_count += 1
            handle.seek(record.extent_lba * SECTOR_SIZE)
            archive = handle.read(record.data_length)
            for entry in parse_archive(archive):
                source = sources.get(entry.name.casefold())
                if source is None or entry.flags not in DATA_FLAGS or not entry.size:
                    continue
                data = archive[entry.offset:entry.offset + entry.size]
                valid, payload, _error = verify_container_bytes(data)
                stem = entry.name[:-6]
                copies[stem].append({
                    "archive_path": path, "entry_index": entry.index, "entry_name": entry.name,
                    "flags_hex": f"0x{entry.flags:08X}", "container_size": entry.size,
                    "allocated_size": entry.allocated_size,
                    "container_sha256": sha256(data),
                    "payload_sha256": sha256(payload) if valid and payload is not None else None,
                    "exact_container_match": data == source["container"],
                    "exact_payload_match": bool(valid and payload == source["payload"]),
                })
    runtime = {
        "archive_count": archive_count,
        "sources": {stem: {k: v for k, v in source.items() if k not in {"container", "payload"}} for stem, source in sources.items()},
        "copies": copies,
    }
    (args.output / "runtime-copy-report.json").write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pages": len(report), "archive_count": archive_count, "runtime_copy_counts": {k: len(v) for k, v in copies.items()}}, indent=2))


if __name__ == "__main__":
    main()
