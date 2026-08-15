#!/usr/bin/env python3
"""Search Ys VI runtime archives for a standalone menu MIG counterpart."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record, parse_record, read_directory
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_arc import DATA_FLAGS, parse_archive
    from tools.scripts.ys6_mig_texture import MAGIC as MIG_MAGIC, inspect as inspect_mig
    from tools.scripts.ys6_z import verify_container_bytes
    from tools.scripts.ys6_menu_image_roundtrip import render_any_mig
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record, parse_record, read_directory
    from ys6_iso_z_search import iter_files
    from ys6_arc import DATA_FLAGS, parse_archive
    from ys6_mig_texture import MAGIC as MIG_MAGIC, inspect as inspect_mig
    from ys6_z import verify_container_bytes
    from ys6_menu_image_roundtrip import render_any_mig


ARC_ROOT = "PSP_GAME/USRDIR/data/arc"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def mig_blocks(data: bytes) -> tuple[dict, bytes] | None:
    if not data.startswith(MIG_MAGIC):
        return None
    _root, palette, image = inspect_mig(data)
    info = image["payload"]
    if palette is not None or info["pixel_format"] != 9:
        return None
    start = image["offset"] + 16 + info["data_offset"]
    size = info["width"] * info["height"]
    blocks = data[start:start + size]
    if len(blocks) != size:
        return None
    return info, blocks


def similarity(left: bytes, right: bytes) -> tuple[int, int, float]:
    total = min(len(left), len(right)) // 16
    equal = sum(
        left[offset:offset + 16] == right[offset:offset + 16]
        for offset in range(0, total * 16, 16)
    )
    return equal, total, equal / total if total else 0.0


def visual_similarity(image: Image.Image, reference: Image.Image) -> float:
    if image.size != reference.size:
        return 0.0
    def composite(value: Image.Image) -> Image.Image:
        rgba = value.convert("RGBA"); bg = Image.new("RGBA", rgba.size, (32, 32, 32, 255)); bg.alpha_composite(rgba); return bg.convert("RGB")
    stat = ImageStat.Stat(ImageChops.difference(composite(image), composite(reference)))
    return max(0.0, 1.0 - sum(stat.mean) / (3.0 * 255.0))


def search(iso: Path, reference_path: Path, reference_png: Path | None = None) -> dict:
    reference = reference_path.read_bytes()
    reference_mig = mig_blocks(reference)
    if reference_mig is None:
        raise ValueError("reference is not an unpaletted PSP DXT3 MIG")
    reference_info, reference_blocks = reference_mig
    visual_reference = None
    if reference_png is not None:
        with Image.open(reference_png) as opened:
            visual_reference = opened.convert("RGBA")
    directory = find_record(iso, ARC_ROOT)
    candidates = []
    standalone_checked = 0
    archives_checked = entries_checked = 0
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, entry in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            if not path.casefold().endswith(".z"):
                continue
            standalone_checked += 1
            handle.seek(entry.extent_lba * SECTOR_SIZE)
            stored = handle.read(entry.data_length)
            valid, payload, _error = verify_container_bytes(stored)
            if not valid or payload is None:
                continue
            parsed = mig_blocks(payload)
            if parsed is None:
                continue
            info, blocks = parsed
            if info["width"] != reference_info["width"] or info["height"] != reference_info["height"]:
                continue
            equal, total, ratio = similarity(reference_blocks, blocks)
            visual_ratio = visual_similarity(render_any_mig(payload, block_offset=1), visual_reference) if visual_reference is not None else 0.0
            if payload == reference or ratio >= 0.05 or visual_ratio >= 0.85:
                candidates.append({
                    "source_kind": "standalone_z",
                    "iso_path": path,
                    "extent_lba": entry.extent_lba,
                    "stored_size": entry.data_length,
                    "stored_sha256": sha256(stored),
                    "payload_sha256": sha256(payload),
                    "exact_payload": payload == reference,
                    "dimensions_match": True,
                    "equal_dxt3_blocks": equal,
                    "total_dxt3_blocks": total,
                    "block_similarity": round(ratio, 6),
                    "visual_similarity": round(visual_ratio, 6),
                })
        for record in sorted(read_directory(handle, directory), key=lambda item: item.name.casefold()):
            if record.is_directory:
                continue
            archives_checked += 1
            archive_path = f"{ARC_ROOT}/{record.name.split(';', 1)[0]}"
            handle.seek(record.extent_lba * SECTOR_SIZE)
            archive = handle.read(record.data_length)
            for entry in parse_archive(archive):
                if entry.flags not in DATA_FLAGS or entry.size <= 0:
                    continue
                entries_checked += 1
                stored = archive[entry.offset:entry.offset + entry.size]
                valid, payload, _error = verify_container_bytes(stored)
                content = payload if valid and payload is not None else stored
                name_hit = "option" in entry.name.casefold() or "select" in entry.name.casefold()
                exact = content == reference
                parsed = mig_blocks(content)
                equal = total = 0
                ratio = 0.0
                dimensions_match = False
                if parsed is not None:
                    info, blocks = parsed
                    dimensions_match = (
                        info["width"] == reference_info["width"]
                        and info["height"] == reference_info["height"]
                    )
                    if dimensions_match:
                        equal, total, ratio = similarity(reference_blocks, blocks)
                visual_ratio = visual_similarity(render_any_mig(content, block_offset=1), visual_reference) if dimensions_match and visual_reference is not None else 0.0
                if exact or name_hit or ratio >= 0.05 or visual_ratio >= 0.85:
                    candidates.append({
                        "source_kind": "runtime_archive",
                        "archive_iso_path": archive_path,
                        "archive_extent_lba": record.extent_lba,
                        "entry_index": entry.index,
                        "entry_name": entry.name,
                        "entry_offset": entry.offset,
                        "stored_size": entry.size,
                        "allocated_size": entry.allocated_size,
                        "stored_sha256": sha256(stored),
                        "payload_sha256": sha256(content),
                        "exact_payload": exact,
                        "name_hit": name_hit,
                        "dimensions_match": dimensions_match,
                        "equal_dxt3_blocks": equal,
                        "total_dxt3_blocks": total,
                        "block_similarity": round(ratio, 6),
                        "visual_similarity": round(visual_ratio, 6),
                    })
    candidates.sort(key=lambda item: (-item["block_similarity"], not item["exact_payload"], item.get("iso_path", item.get("archive_iso_path", "")), item.get("entry_index", -1)))
    return {
        "schema_version": 1,
        "iso": str(iso),
        "reference": str(reference_path),
        "reference_png": str(reference_png) if reference_png else None,
        "reference_sha256": sha256(reference),
        "standalone_z_checked": standalone_checked,
        "archives_checked": archives_checked,
        "entries_checked": entries_checked,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--reference-png", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = search(args.iso, args.reference, args.reference_png)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (OSError, ValueError) as exc:
        print(f"런타임 메뉴 이미지 검색 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
