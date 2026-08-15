#!/usr/bin/env python3
"""Inventory PPSSPP texture dumps and create similarity-ranked contact sheets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def similarity(left: Image.Image, right: Image.Image) -> float:
    if left.size != right.size:
        return 0.0
    left_rgb = left.convert("RGB")
    right_rgb = right.convert("RGB")
    stat = ImageStat.Stat(ImageChops.difference(left_rgb, right_rgb))
    mean_error = sum(stat.mean) / 3.0
    return max(0.0, 1.0 - mean_error / 255.0)


def execute(dump_dir: Path, reference_path: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(reference_path) as opened:
        reference = opened.convert("RGBA")
    rows = []
    for path in dump_dir.rglob("*.png"):
        try:
            with Image.open(path) as opened:
                opened.load()
                image = opened.convert("RGBA")
        except OSError:
            continue
        rows.append({
            "path": str(path), "filename": path.name, "width": image.width,
            "height": image.height, "mode": image.mode, "sha256": sha256(path),
            "reference_similarity": round(similarity(image, reference), 6),
            "mtime": path.stat().st_mtime,
        })
    rows.sort(key=lambda item: (-item["reference_similarity"], -item["mtime"], item["filename"]))
    candidates = [item for item in rows if item["width"] == reference.width and item["height"] == reference.height]
    thumb_w, thumb_h, label_h, columns = 256, 256, 48, 4
    pages = []
    for page_index in range(math.ceil(len(candidates) / 20)):
        page_rows = candidates[page_index * 20:(page_index + 1) * 20]
        sheet_rows = math.ceil(len(page_rows) / columns)
        sheet = Image.new("RGB", (columns * thumb_w, sheet_rows * (thumb_h + label_h)), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for index, item in enumerate(page_rows):
            x = (index % columns) * thumb_w; y = (index // columns) * (thumb_h + label_h)
            with Image.open(item["path"]) as opened:
                rgba = opened.convert("RGBA")
            backdrop = Image.new("RGBA", rgba.size, (32, 32, 32, 255)); backdrop.alpha_composite(rgba)
            sheet.paste(backdrop.convert("RGB"), (x, y))
            draw.text((x + 4, y + thumb_h + 4), item["filename"], fill=(255, 255, 255))
            draw.text((x + 4, y + thumb_h + 22), f"similarity={item['reference_similarity']:.6f}", fill=(180, 220, 255))
        page_path = output / f"contact-sheet-{page_index + 1:02d}.png"
        sheet.save(page_path)
        pages.append(str(page_path))
    report = {
        "schema_version": 1, "dump_dir": str(dump_dir), "reference": str(reference_path),
        "texture_count": len(rows), "same_size_candidate_count": len(candidates),
        "contact_sheets": pages, "textures": rows,
    }
    (output / "texture-inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump_dir", type=Path); parser.add_argument("reference", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = execute(args.dump_dir, args.reference, args.output)
        print(json.dumps({key: report[key] for key in ("texture_count", "same_size_candidate_count", "contact_sheets")}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"텍스처 덤프 인벤토리 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
