#!/usr/bin/env python3
"""Rearrange a one-row Ys VI glyph atlas into a fixed-column grid."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def build_grid(source: Image.Image, columns: int, cell_width: int, cell_height: int, gap: int) -> tuple[Image.Image, int]:
    if columns < 1 or cell_width < 1 or cell_height < 1 or gap < 0:
        raise ValueError("columns and cell dimensions must be positive; gap must be nonnegative")
    if source.height != cell_height or source.width % cell_width:
        raise ValueError(f"source dimensions do not match cells: {source.width}x{source.height}, cell={cell_width}x{cell_height}")
    count = source.width // cell_width
    rows = math.ceil(count / columns)
    width = columns * cell_width + (columns + 1) * gap
    height = rows * cell_height + (rows + 1) * gap
    output = Image.new("L", (width, height), 32)
    for index in range(count):
        x = gap + (index % columns) * (cell_width + gap)
        y = gap + (index // columns) * (cell_height + gap)
        glyph = source.crop((index * cell_width, 0, (index + 1) * cell_width, cell_height))
        output.paste(glyph, (x, y))
    if gap:
        draw = ImageDraw.Draw(output)
        for column in range(columns + 1):
            x = column * (cell_width + gap)
            draw.line((x, 0, x, height - 1), fill=96, width=gap)
        for row in range(rows + 1):
            y = row * (cell_height + gap)
            draw.line((0, y, width - 1, y), fill=96, width=gap)
    return output, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=24)
    parser.add_argument("--cell-width", type=int, default=128)
    parser.add_argument("--cell-height", type=int, default=96)
    parser.add_argument("--gap", type=int, default=1)
    args = parser.parse_args()
    with Image.open(args.source) as image:
        grid, count = build_grid(image.convert("L"), args.columns, args.cell_width, args.cell_height, args.gap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    grid.save(args.output)
    print(f"glyphs={count} columns={args.columns} rows={math.ceil(count / args.columns)} size={grid.width}x{grid.height}")
    print(args.output)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
