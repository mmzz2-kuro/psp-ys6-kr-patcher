#!/usr/bin/env python3
"""Inspect and render the indexed 8-bit MIG textures used by Ys VI PSP."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from PIL import Image


MAGIC = b"MIG.00.1PSP\0"


def section(data: bytes, offset: int) -> dict:
    kind, unknown, size, data_size, child_offset = struct.unpack_from("<HHIII", data, offset)
    return {"offset": offset, "kind": kind, "unknown": unknown, "size": size,
            "data_size": data_size, "child_offset": child_offset}


def payload_header(data: bytes, offset: int) -> dict:
    base = offset + 16
    header_size, pixel_format, pixel_order = struct.unpack_from("<IHH", data, base)
    width, height, bits_per_pixel = struct.unpack_from("<HHH", data, base + 8)
    data_offset, _ = struct.unpack_from("<II", data, base + 24)
    return {"header_size": header_size, "pixel_format": pixel_format,
            "pixel_order": pixel_order, "width": width, "height": height,
            "bits_per_pixel": bits_per_pixel, "data_offset": data_offset}


def unswizzle_8bpp(source: bytes, width: int, height: int) -> bytes:
    if width % 16 or height % 8:
        raise ValueError("8-bit PSP swizzle requires width/height multiples of 16/8")
    output = bytearray(width * height)
    cursor = 0
    for block_y in range(0, height, 8):
        for block_x in range(0, width, 16):
            for row in range(8):
                target = (block_y + row) * width + block_x
                output[target:target + 16] = source[cursor:cursor + 16]
                cursor += 16
    return bytes(output)


def inspect(data: bytes) -> tuple[dict, dict | None, dict]:
    if not data.startswith(MAGIC):
        raise ValueError("not a MIG.00.1PSP texture")
    root = section(data, 16)
    picture = section(data, 32)
    cursor = 48
    palette = None
    image = None
    while cursor < 32 + picture["size"]:
        child = section(data, cursor)
        child["payload"] = payload_header(data, cursor)
        if child["kind"] == 5:
            palette = child
        elif child["kind"] == 4:
            image = child
        if child["size"] <= 0:
            break
        cursor += child["size"]
    if image is None:
        raise ValueError("MIG has no image section")
    return root, palette, image


def render(data: bytes) -> tuple[Image.Image, dict]:
    root, palette, image = inspect(data)
    info = image["payload"]
    if info["pixel_format"] != 5 or info["bits_per_pixel"] != 8 or palette is None:
        raise ValueError("renderer currently supports indexed 8-bit MIG textures only")
    palette_info = palette["payload"]
    if palette_info["pixel_format"] != 3:
        raise ValueError("renderer currently supports RGBA8888 palettes only")

    # data_offset is relative to the section payload (after its 16-byte header).
    palette_start = palette["offset"] + 16 + palette_info["data_offset"]
    color_count = palette_info["width"] * palette_info["height"]
    colors = data[palette_start:palette_start + color_count * 4]
    image_start = image["offset"] + 16 + info["data_offset"]
    pixel_count = info["width"] * info["height"]
    indices = data[image_start:image_start + pixel_count]
    if len(indices) != pixel_count:
        raise ValueError("truncated image data")
    if info["pixel_order"] == 1:
        indices = unswizzle_8bpp(indices, info["width"], info["height"])
    elif info["pixel_order"] != 0:
        raise ValueError(f"unsupported pixel order: {info['pixel_order']}")

    rgba = bytearray(pixel_count * 4)
    for index, palette_index in enumerate(indices):
        # PSP 8-bit CLUT storage swaps index bits 3 and 4 in each 32-color group.
        palette_index = ((palette_index & 0xE7) | ((palette_index & 0x08) << 1)
                         | ((palette_index & 0x10) >> 1))
        rgba[index * 4:index * 4 + 4] = colors[palette_index * 4:palette_index * 4 + 4]
    output = Image.frombytes("RGBA", (info["width"], info["height"]), bytes(rgba))
    metadata = {"root": root, "palette": palette, "image": image}
    return output, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    image, metadata = render(args.input.read_bytes())
    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.png)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"size": image.size, "mode": image.mode, "png": str(args.png) if args.png else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
