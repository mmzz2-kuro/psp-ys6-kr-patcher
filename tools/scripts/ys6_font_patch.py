#!/usr/bin/env python3
"""Replace one Ys VI embedded font glyph with a rendered TrueType/TTC glyph."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from tools.scripts.ys6_font_table import (
        DEFAULT_COUNT, DEFAULT_OFFSET, GLYPH_HEIGHT, GLYPH_SIZE,
        GLYPH_WIDTH, RECORD_SIZE, parse_table, render_glyph,
    )
except ModuleNotFoundError:
    try:
        from .ys6_font_table import (
            DEFAULT_COUNT, DEFAULT_OFFSET, GLYPH_HEIGHT, GLYPH_SIZE,
            GLYPH_WIDTH, RECORD_SIZE, parse_table, render_glyph,
        )
    except ImportError:
        from ys6_font_table import (
            DEFAULT_COUNT, DEFAULT_OFFSET, GLYPH_HEIGHT, GLYPH_SIZE,
            GLYPH_WIDTH, RECORD_SIZE, parse_table, render_glyph,
        )


def render_text_bitmap(
    text: str,
    font_path: Path,
    font_index: int,
    font_size: int,
    threshold: int,
) -> tuple[bytes, Image.Image]:
    font = ImageFont.truetype(str(font_path), font_size, index=font_index)
    bbox = font.getbbox(text)
    glyph_width = bbox[2] - bbox[0]
    glyph_height = bbox[3] - bbox[1]
    if glyph_width > GLYPH_WIDTH or glyph_height > GLYPH_HEIGHT:
        raise ValueError(
            f"rendered glyph {glyph_width}x{glyph_height} exceeds "
            f"{GLYPH_WIDTH}x{GLYPH_HEIGHT}"
        )

    x = (GLYPH_WIDTH - glyph_width) // 2 - bbox[0]
    y = (GLYPH_HEIGHT - glyph_height) // 2 - bbox[1]
    grayscale = Image.new("L", (GLYPH_WIDTH, GLYPH_HEIGHT), 0)
    ImageDraw.Draw(grayscale).text((x, y), text, font=font, fill=255)
    mono = grayscale.point(lambda value: 255 if value >= threshold else 0, mode="1")

    bitmap = bytearray()
    for row in range(GLYPH_HEIGHT):
        value = 0
        for column in range(GLYPH_WIDTH):
            if mono.getpixel((column, row)):
                value |= 1 << (15 - column)
        bitmap.extend(value.to_bytes(2, "big"))
    return bytes(bitmap), mono.convert("L")


def render_pattern_bitmap(pattern_path: Path) -> tuple[bytes, Image.Image]:
    rows = pattern_path.read_text(encoding="utf-8").splitlines()
    if len(rows) != GLYPH_HEIGHT:
        raise ValueError(f"pattern must contain exactly {GLYPH_HEIGHT} rows")
    if any(len(row) != GLYPH_WIDTH for row in rows):
        raise ValueError(f"every pattern row must contain exactly {GLYPH_WIDTH} characters")
    if any(character not in {".", "#"} for row in rows for character in row):
        raise ValueError("pattern may contain only '.' and '#'")

    bitmap = bytearray()
    pixels = bytearray(GLYPH_WIDTH * GLYPH_HEIGHT)
    for y, row in enumerate(rows):
        value = 0
        for x, character in enumerate(row):
            if character == "#":
                value |= 1 << (15 - x)
                pixels[y * GLYPH_WIDTH + x] = 255
        bitmap.extend(value.to_bytes(2, "big"))
    return bytes(bitmap), Image.frombytes("L", (GLYPH_WIDTH, GLYPH_HEIGHT), bytes(pixels))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_boot", type=Path)
    parser.add_argument("output_boot", type=Path)
    parser.add_argument("--code", type=lambda value: int(value, 0), required=True)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--text")
    source_group.add_argument("--pattern", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-index", type=int, default=0)
    parser.add_argument("--font-size", type=int, default=12)
    parser.add_argument("--threshold", type=int, default=96)
    parser.add_argument("--offset", type=lambda value: int(value, 0), default=DEFAULT_OFFSET)
    parser.add_argument("--count", type=lambda value: int(value, 0), default=DEFAULT_COUNT)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.text is not None and len(args.text) != 1:
        raise ValueError("--text must contain exactly one Unicode character")
    if args.text is not None and args.font is None:
        raise ValueError("--font is required with --text")
    if args.output_boot.exists() and not args.overwrite:
        raise FileExistsError(f"output already exists: {args.output_boot}")

    source = args.input_boot.read_bytes()
    glyphs = parse_table(source, args.offset, args.count)
    matches = [glyph for glyph in glyphs if glyph.code == args.code]
    if len(matches) != 1:
        raise ValueError(f"expected one code 0x{args.code:04X}, found {len(matches)}")

    glyph = matches[0]
    if args.pattern is not None:
        bitmap, preview = render_pattern_bitmap(args.pattern)
    else:
        bitmap, preview = render_text_bitmap(
            args.text,
            args.font,
            args.font_index,
            args.font_size,
            args.threshold,
        )
    if len(bitmap) != GLYPH_SIZE:
        raise AssertionError("unexpected glyph bitmap size")

    record_offset = args.offset + glyph.index * RECORD_SIZE
    bitmap_offset = record_offset + 2
    patched = bytearray(source)
    patched[bitmap_offset : bitmap_offset + GLYPH_SIZE] = bitmap
    args.output_boot.parent.mkdir(parents=True, exist_ok=True)
    args.output_boot.write_bytes(patched)

    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        comparison = Image.new("L", (GLYPH_WIDTH * 2 + 2, GLYPH_HEIGHT), 0)
        comparison.paste(render_glyph(glyph), (0, 0))
        comparison.paste(preview, (GLYPH_WIDTH + 2, 0))
        comparison.resize(
            (comparison.width * 8, comparison.height * 8), Image.Resampling.NEAREST
        ).save(args.preview)

    changed = [i for i, (old, new) in enumerate(zip(source, patched)) if old != new]
    print(f"code=0x{glyph.code:04X}")
    print(f"index={glyph.index}")
    print(f"record_offset=0x{record_offset:X}")
    print(f"bitmap_offset=0x{bitmap_offset:X}")
    print(f"changed_bytes={len(changed)}")
    print(f"input_sha256={hashlib.sha256(source).hexdigest().upper()}")
    print(f"output_sha256={hashlib.sha256(patched).hexdigest().upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
