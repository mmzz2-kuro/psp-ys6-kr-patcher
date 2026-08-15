#!/usr/bin/env python3
"""Map stored PSP DXT3 blocks to PPSSPP's rendered 4x4 block coordinates."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.ys6_menu_image_roundtrip import psp_dxt3_to_pc
except ModuleNotFoundError:
    from ys6_menu_image_roundtrip import psp_dxt3_to_pc


def block_bytes(image: Image.Image, block_index: int, blocks_per_row: int) -> bytes:
    x = (block_index % blocks_per_row) * 4
    y = (block_index // blocks_per_row) * 4
    return image.crop((x, y, x + 4, y + 4)).tobytes()


def decode_ppsspp_dxt3_block(block: bytes) -> bytes:
    if len(block) != 16:
        raise ValueError("DXT3 block must be 16 bytes")
    color1 = int.from_bytes(block[4:6], "little")
    color2 = int.from_bytes(block[6:8], "little")

    def rgb565(value: int) -> tuple[int, int, int]:
        return ((value >> 8) & 0xF8, (value >> 3) & 0xFC, (value << 3) & 0xF8)

    first = rgb565(color1); second = rgb565(color2)
    if color1 > color2:
        third = tuple((a + a + b) // 3 for a, b in zip(first, second))
        fourth = tuple((b + b + a) // 3 for a, b in zip(first, second))
    else:
        third = tuple((a + b) // 2 for a, b in zip(first, second))
        fourth = (0, 0, 0)
    colors = (first, second, third, fourth)
    output = bytearray()
    for y in range(4):
        color_row = block[y]
        alpha_row = int.from_bytes(block[8 + y * 2:10 + y * 2], "little")
        for _x in range(4):
            red, green, blue = colors[color_row & 3]
            alpha = (alpha_row & 0xF) * 17
            output.extend((red, green, blue, alpha))
            color_row >>= 2
            alpha_row >>= 4
    return bytes(output)


def normalize_dump_block(block: bytes) -> bytes:
    output = bytearray(block)
    for index in range(0, len(output), 4):
        output[index] &= 0xF8
        output[index + 1] &= 0xFC
        output[index + 2] &= 0xF8
        output[index + 3] = 0
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("dump_png", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--offset", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    args = parser.parse_args()

    size = args.width * args.height
    stored = args.payload.read_bytes()[args.offset:args.offset + size]
    if len(stored) != size:
        raise ValueError("DXT3 atlas is truncated")
    decoded = Image.frombytes("RGBA", (args.width, args.height), psp_dxt3_to_pc(stored), "bcn", (2,))
    with Image.open(args.dump_png) as opened:
        rendered = opened.convert("RGBA")
    if rendered.size != decoded.size:
        raise ValueError(f"image size mismatch: {rendered.size} != {decoded.size}")

    blocks_per_row = args.width // 4
    block_count = blocks_per_row * (args.height // 4)
    rendered_by_hash: dict[bytes, list[int]] = defaultdict(list)
    for index in range(block_count):
        rendered_by_hash[hashlib.sha256(block_bytes(rendered, index, blocks_per_row)).digest()].append(index)

    mappings = []
    decoded_blocks = [decode_ppsspp_dxt3_block(stored[index * 16:(index + 1) * 16])
                      for index in range(block_count)]
    rendered_exact: dict[bytes, list[int]] = defaultdict(list)
    for index in range(block_count):
        rendered_exact[normalize_dump_block(block_bytes(rendered, index, blocks_per_row))].append(index)
    unique = ambiguous = missing = 0
    for stored_index in range(block_count):
        digest = hashlib.sha256(block_bytes(decoded, stored_index, blocks_per_row)).digest()
        candidates = rendered_by_hash.get(digest, [])
        if len(candidates) == 1:
            unique += 1
        elif candidates:
            ambiguous += 1
        else:
            missing += 1
        mappings.append({
            "stored_index": stored_index,
            "stored_x": stored_index % blocks_per_row,
            "stored_y": stored_index // blocks_per_row,
            "rendered_indices": candidates,
            "rendered_coords": [[item % blocks_per_row, item // blocks_per_row] for item in candidates],
        })

    result = {
        "schema_version": 1,
        "payload": str(args.payload),
        "dump_png": str(args.dump_png),
        "offset": args.offset,
        "width": args.width,
        "height": args.height,
        "block_count": block_count,
        "unique_match_count": unique,
        "ambiguous_match_count": ambiguous,
        "missing_match_count": missing,
        "mappings": mappings,
    }
    exact_rows = []
    for stored_index, source_block in enumerate(decoded_blocks):
        candidates = rendered_exact.get(normalize_dump_block(source_block), [])
        exact_rows.append({
            "stored_index": stored_index,
            "rendered_indices": candidates,
            "rendered_coords": [[item % blocks_per_row, item // blocks_per_row] for item in candidates],
        })
    result["ppsspp_exact_mappings"] = exact_rows
    target_rows = []
    for target_y in range(7, 11):
        for target_x in range(10, 14):
            rendered_index = target_y * blocks_per_row + target_x
            target = normalize_dump_block(block_bytes(rendered, rendered_index, blocks_per_row))
            ranked = []
            for stored_index, candidate_raw in enumerate(decoded_blocks):
                candidate = normalize_dump_block(candidate_raw)
                error = sum((left - right) * (left - right) for left, right in zip(target, candidate))
                ranked.append((error, stored_index))
            ranked.sort()
            target_rows.append({
                "rendered_index": rendered_index,
                "rendered_coord": [target_x, target_y],
                "nearest": [{"error": error, "stored_index": stored_index,
                             "stored_coord": [stored_index % blocks_per_row, stored_index // blocks_per_row]}
                            for error, stored_index in ranked[:8]],
            })
    result["effect_row_nearest"] = target_rows
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "block_count", "unique_match_count", "ambiguous_match_count", "missing_match_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
