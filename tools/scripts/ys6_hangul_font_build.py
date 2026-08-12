#!/usr/bin/env python3
"""Build multiple safe-width Korean glyphs into a decrypted Ys VI EBOOT."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.ys6_font_patch import render_pattern_bitmap, render_text_bitmap
    from tools.scripts.ys6_font_table import DEFAULT_COUNT, DEFAULT_OFFSET, GLYPH_HEIGHT, GLYPH_SIZE, GLYPH_WIDTH, RECORD_SIZE, parse_table
except ModuleNotFoundError:
    from ys6_font_patch import render_pattern_bitmap, render_text_bitmap
    from ys6_font_table import DEFAULT_COUNT, DEFAULT_OFFSET, GLYPH_HEIGHT, GLYPH_SIZE, GLYPH_WIDTH, RECORD_SIZE, parse_table


def bitmap_to_image(bitmap: bytes) -> Image.Image:
    pixels = bytearray(GLYPH_WIDTH * GLYPH_HEIGHT)
    for y in range(GLYPH_HEIGHT):
        row = int.from_bytes(bitmap[y * 2 : y * 2 + 2], "big")
        for x in range(GLYPH_WIDTH):
            if row & (1 << (15 - x)):
                pixels[y * GLYPH_WIDTH + x] = 255
    return Image.frombytes("L", (GLYPH_WIDTH, GLYPH_HEIGHT), bytes(pixels))


def image_to_bitmap(image: Image.Image) -> bytes:
    output = bytearray()
    for y in range(GLYPH_HEIGHT):
        row = 0
        for x in range(GLYPH_WIDTH):
            if image.getpixel((x, y)):
                row |= 1 << (15 - x)
        output.extend(row.to_bytes(2, "big"))
    return bytes(output)


def fit_visible_width(bitmap: bytes, visible_width: int) -> tuple[bytes, int, tuple[int, int, int, int] | None]:
    image = bitmap_to_image(bitmap)
    bbox = image.getbbox()
    if bbox is None:
        return bitmap, 0, None
    shift = max(0, bbox[2] - visible_width)
    if shift:
        shifted = Image.new("L", image.size, 0)
        shifted.paste(image, (-shift, 0))
        image = shifted
    final_bbox = image.getbbox()
    if final_bbox is not None and final_bbox[2] > visible_width:
        raise ValueError("glyph still exceeds visible width")
    return image_to_bitmap(image), shift, final_bbox


def align_horizontal_center(bitmap: bytes, offset: int = -2) -> tuple[bytes, int, tuple[int, int, int, int] | None]:
    """Center a glyph in the 16px cell, apply an offset, and keep it in bounds."""
    image = bitmap_to_image(bitmap)
    bbox = image.getbbox()
    if bbox is None:
        return bitmap, 0, None
    width = bbox[2] - bbox[0]
    target_x = (GLYPH_WIDTH - width) // 2 + offset
    target_x = max(0, min(GLYPH_WIDTH - width, target_x))
    shift = target_x - bbox[0]
    aligned = Image.new("L", image.size, 0)
    aligned.paste(image.crop(bbox), (target_x, bbox[1]))
    return image_to_bitmap(aligned), shift, aligned.getbbox()


def align_horizontal_left(bitmap: bytes, inset: int = 1) -> tuple[bytes, int, tuple[int, int, int, int] | None]:
    """Align a glyph's ink bbox to a fixed left inset without scaling it."""
    image = bitmap_to_image(bitmap)
    bbox = image.getbbox()
    if bbox is None:
        return bitmap, 0, None
    width = bbox[2] - bbox[0]
    target_x = max(0, min(GLYPH_WIDTH - width, inset))
    shift = target_x - bbox[0]
    aligned = Image.new("L", image.size, 0)
    aligned.paste(image.crop(bbox), (target_x, bbox[1]))
    return image_to_bitmap(aligned), shift, aligned.getbbox()


def parse_overrides(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        character, separator, path = value.partition("=")
        if not separator or len(character) != 1:
            raise ValueError(f"invalid override: {value}")
        result[character] = Path(path)
    return result


def build(eboot: bytes, mapping: list[dict], font: Path, visible_width: int, overrides: dict[str, Path], horizontal_center_offset: int | None = None, horizontal_left_inset: int | None = None) -> tuple[bytes, list[dict], Image.Image]:
    if horizontal_center_offset is not None and horizontal_left_inset is not None:
        raise ValueError("horizontal center and left alignment cannot be used together")
    glyphs = parse_table(eboot, DEFAULT_OFFSET, DEFAULT_COUNT)
    patched = bytearray(eboot)
    previews = []
    report = []
    for row in mapping:
        character = row["character"]
        index = int(row["font_index"])
        code = int(row["game_code"], 0)
        glyph = glyphs[index]
        if glyph.code != code:
            raise ValueError(f"mapping mismatch at index {index}: 0x{glyph.code:04X} != 0x{code:04X}")
        if character in overrides:
            bitmap, preview = render_pattern_bitmap(overrides[character])
            shift = 0
            bbox = preview.getbbox()
            source = "override"
        else:
            bitmap, _ = render_text_bitmap(character, font, 0, 12, 96)
            bitmap, shift, bbox = fit_visible_width(bitmap, visible_width)
            preview = bitmap_to_image(bitmap)
            source = "gulim"
        alignment_shift = 0
        if horizontal_center_offset is not None:
            bitmap, alignment_shift, bbox = align_horizontal_center(bitmap, horizontal_center_offset)
            preview = bitmap_to_image(bitmap)
        elif horizontal_left_inset is not None:
            bitmap, alignment_shift, bbox = align_horizontal_left(bitmap, horizontal_left_inset)
            preview = bitmap_to_image(bitmap)
        if not any(bitmap):
            raise ValueError(f"blank glyph: {character}")
        bitmap_offset = DEFAULT_OFFSET + index * RECORD_SIZE + 2
        patched[bitmap_offset : bitmap_offset + GLYPH_SIZE] = bitmap
        previews.append((character, preview))
        report.append({**row, "source": source, "shift_left": shift, "alignment_shift": alignment_shift, "horizontal_center_offset": horizontal_center_offset, "horizontal_left_inset": horizontal_left_inset, "bbox": list(bbox) if bbox else None, "bitmap_offset": f"0x{bitmap_offset:X}", "bitmap_hex": bitmap.hex().upper()})
    atlas = Image.new("L", (GLYPH_WIDTH * len(previews), GLYPH_HEIGHT), 0)
    for column, (_, image) in enumerate(previews):
        atlas.paste(image, (column * GLYPH_WIDTH, 0))
    return bytes(patched), report, atlas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_eboot", type=Path)
    parser.add_argument("mapping_json", type=Path)
    parser.add_argument("output_eboot", type=Path)
    parser.add_argument("report_json", type=Path)
    parser.add_argument("atlas_png", type=Path)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--visible-width", type=int, default=12)
    parser.add_argument("--horizontal-center-offset", type=int)
    parser.add_argument("--horizontal-left-inset", type=int)
    parser.add_argument("--override", action="append", default=[])
    args = parser.parse_args()
    if not 1 <= args.visible_width <= GLYPH_WIDTH:
        raise ValueError("visible width must be in 1..16")
    source = args.input_eboot.read_bytes()
    mapping = json.loads(args.mapping_json.read_text(encoding="utf-8"))["mappings"]
    patched, report, atlas = build(source, mapping, args.font, args.visible_width, parse_overrides(args.override), args.horizontal_center_offset, args.horizontal_left_inset)
    args.output_eboot.parent.mkdir(parents=True, exist_ok=True)
    args.output_eboot.write_bytes(patched)
    args.report_json.write_text(json.dumps({"visible_width": args.visible_width, "glyphs": report}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    atlas.resize((atlas.width * 8, atlas.height * 8), Image.Resampling.NEAREST).save(args.atlas_png)
    changed = sum(left != right for left, right in zip(source, patched))
    print(json.dumps({"glyph_count": len(report), "changed_bytes": changed, "input_sha256": hashlib.sha256(source).hexdigest().upper(), "output_sha256": hashlib.sha256(patched).hexdigest().upper()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
