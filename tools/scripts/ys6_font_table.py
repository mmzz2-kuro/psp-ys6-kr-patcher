#!/usr/bin/env python3
"""Inspect and render the Ys VI embedded 16x12 bitmap font table."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


DEFAULT_OFFSET = 0x13E88C
DEFAULT_COUNT = 0x1200
RECORD_SIZE = 0x1A
GLYPH_WIDTH = 16
GLYPH_HEIGHT = 12
GLYPH_SIZE = GLYPH_WIDTH * GLYPH_HEIGHT // 8


@dataclass(frozen=True)
class Glyph:
    index: int
    code: int
    bitmap: bytes

    @property
    def text(self) -> str:
        try:
            return self.code.to_bytes(2, "big").decode("cp932")
        except UnicodeDecodeError:
            return ""


def parse_table(data: bytes, offset: int, count: int) -> list[Glyph]:
    end = offset + count * RECORD_SIZE
    if offset < 0 or end > len(data):
        raise ValueError(
            f"font table 0x{offset:X}..0x{end:X} exceeds file size 0x{len(data):X}"
        )

    glyphs = []
    for index in range(count):
        start = offset + index * RECORD_SIZE
        code = int.from_bytes(data[start : start + 2], "little")
        bitmap = data[start + 2 : start + RECORD_SIZE]
        glyphs.append(Glyph(index, code, bitmap))
    return glyphs


def render_glyph(glyph: Glyph) -> Image.Image:
    pixels = bytearray(GLYPH_WIDTH * GLYPH_HEIGHT)
    for y in range(GLYPH_HEIGHT):
        row = int.from_bytes(glyph.bitmap[y * 2 : y * 2 + 2], "big")
        for x in range(GLYPH_WIDTH):
            pixels[y * GLYPH_WIDTH + x] = 255 if row & (1 << (15 - x)) else 0
    return Image.frombytes("L", (GLYPH_WIDTH, GLYPH_HEIGHT), bytes(pixels))


def write_atlas(glyphs: list[Glyph], output: Path, columns: int = 16) -> None:
    rows = (len(glyphs) + columns - 1) // columns
    atlas = Image.new("L", (columns * GLYPH_WIDTH, rows * GLYPH_HEIGHT))
    for glyph in glyphs:
        x = glyph.index % columns * GLYPH_WIDTH
        y = glyph.index // columns * GLYPH_HEIGHT
        atlas.paste(render_glyph(glyph), (x, y))
    atlas.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("boot_bin", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--offset", type=lambda value: int(value, 0), default=DEFAULT_OFFSET)
    parser.add_argument("--count", type=lambda value: int(value, 0), default=DEFAULT_COUNT)
    args = parser.parse_args()

    glyphs = parse_table(args.boot_bin.read_bytes(), args.offset, args.count)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    atlas_path = args.output_dir / "ys6-font-atlas.png"
    csv_path = args.output_dir / "ys6-font-map.csv"
    write_atlas(glyphs, atlas_path)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(("index", "code_hex", "text"))
        for glyph in glyphs:
            writer.writerow((glyph.index, f"{glyph.code:04X}", glyph.text))

    print(f"offset=0x{args.offset:X}")
    print(f"count={len(glyphs)}")
    print(f"record_size={RECORD_SIZE}")
    print(atlas_path)
    print(csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
