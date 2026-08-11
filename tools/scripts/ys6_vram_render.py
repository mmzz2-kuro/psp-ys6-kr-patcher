#!/usr/bin/env python3
"""Render a raw PSP VRAM dump in common pixel formats for visual inspection."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def expand(value: int, bits: int) -> int:
    maximum = (1 << bits) - 1
    return (value * 255 + maximum // 2) // maximum


def render_16(data: bytes, width: int, mode: str) -> Image.Image:
    pixel_count = len(data) // 2
    height = (pixel_count + width - 1) // width
    rgba = bytearray(width * height * 4)

    for index in range(pixel_count):
        value = data[index * 2] | data[index * 2 + 1] << 8
        if mode == "565":
            r = expand(value & 0x1F, 5)
            g = expand((value >> 5) & 0x3F, 6)
            b = expand((value >> 11) & 0x1F, 5)
            a = 255
        elif mode == "5551":
            r = expand(value & 0x1F, 5)
            g = expand((value >> 5) & 0x1F, 5)
            b = expand((value >> 10) & 0x1F, 5)
            a = 255 if value & 0x8000 else 0
        elif mode == "4444":
            r = expand(value & 0x0F, 4)
            g = expand((value >> 4) & 0x0F, 4)
            b = expand((value >> 8) & 0x0F, 4)
            a = expand((value >> 12) & 0x0F, 4)
        else:
            raise ValueError(f"unsupported mode: {mode}")
        start = index * 4
        rgba[start : start + 4] = bytes((r, g, b, a))

    return Image.frombytes("RGBA", (width, height), bytes(rgba))


def render_8(data: bytes, width: int) -> Image.Image:
    height = (len(data) + width - 1) // width
    padded = data + bytes(width * height - len(data))
    return Image.frombytes("L", (width, height), padded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--width", type=int, default=512)
    args = parser.parse_args()

    data = args.input.read_bytes()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for mode in ("565", "5551", "4444"):
        output = args.output_dir / f"vram-{mode}-w{args.width}.png"
        render_16(data, args.width, mode).save(output)
        outputs.append(output)

    output_8 = args.output_dir / f"vram-l8-w{args.width}.png"
    render_8(data, args.width).save(output_8)
    outputs.append(output_8)

    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
