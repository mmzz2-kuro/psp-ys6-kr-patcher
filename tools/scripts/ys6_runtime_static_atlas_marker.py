#!/usr/bin/env python3
"""Insert DXT1 diagnostic markers into the runtime option atlas in static_tex.dds.z."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.ys6_z import build_container, verify_container_bytes
except ModuleNotFoundError:
    from ys6_z import build_container, verify_container_bytes


ATLAS_OFFSET = 0x106130
STORAGE_WIDTH = 256
STORAGE_HEIGHT = 256
ATLAS_SIZE = STORAGE_WIDTH * STORAGE_HEIGHT // 2
BLOCK_SIZE = 8
BLOCKS_PER_ROW = STORAGE_WIDTH // 4
MARKER_BOXES = ((40, 28, 55, 43),)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def magenta_psp_dxt1_block() -> bytes:
    # PSP order: four color-index rows, then two RGB565 endpoints.
    return bytes.fromhex("000000001FF81FF8")


def indexed_psp_dxt1_block(block_index: int) -> bytes:
    color = block_index & 0xFFFF
    endpoint = color.to_bytes(2, "little")
    return bytes(4) + endpoint + endpoint


def selected_blocks() -> list[int]:
    result: set[int] = set()
    for left, top, right, bottom in MARKER_BOXES:
        for block_y in range(top // 4, bottom // 4 + 1):
            for block_x in range(left // 4, right // 4 + 1):
                result.add(block_y * BLOCKS_PER_ROW + block_x)
    return sorted(result)


def psp_dxt1_to_pc(stored: bytes) -> bytes:
    output = bytearray()
    for offset in range(0, len(stored), BLOCK_SIZE):
        block = stored[offset:offset + BLOCK_SIZE]
        output.extend(block[4:8] + block[0:4])
    return bytes(output)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_payload", type=Path)
    parser.add_argument("output_payload", type=Path)
    parser.add_argument("output_container", type=Path)
    parser.add_argument("--allocation", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--block-map", action="store_true",
                        help="replace every DXT block with its RGB565 block index")
    args = parser.parse_args(argv)

    original = args.source_payload.read_bytes()
    if len(original) < ATLAS_OFFSET + ATLAS_SIZE:
        raise ValueError("static_tex payload is too short for the runtime atlas")
    patched = bytearray(original)
    marker = magenta_psp_dxt1_block()
    blocks = list(range(ATLAS_SIZE // BLOCK_SIZE)) if args.block_map else selected_blocks()
    ranges = []
    for block_index in blocks:
        offset = ATLAS_OFFSET + block_index * BLOCK_SIZE
        before = bytes(patched[offset:offset + BLOCK_SIZE])
        replacement = indexed_psp_dxt1_block(block_index) if args.block_map else marker
        patched[offset:offset + BLOCK_SIZE] = replacement
        ranges.append({"block_index": block_index, "payload_offset": offset,
                       "original_sha256": sha256(before), "replacement_sha256": sha256(replacement)})

    patched_bytes = bytes(patched)
    changed = [i for i, pair in enumerate(zip(original, patched_bytes)) if pair[0] != pair[1]]
    allowed = set()
    for block_index in blocks:
        start = ATLAS_OFFSET + block_index * BLOCK_SIZE
        allowed.update(range(start, start + BLOCK_SIZE))
    outside = [position for position in changed if position not in allowed]
    if outside:
        raise ValueError(f"change outside selected blocks: 0x{outside[0]:X}")

    container = build_container(patched_bytes, 9)
    valid, verified, error = verify_container_bytes(container)
    if not valid or verified != patched_bytes:
        raise ValueError(f"container verification failed: {error}")
    if len(container) > args.allocation:
        raise ValueError(f"container exceeds allocation: {len(container)} > {args.allocation}")

    args.output_payload.parent.mkdir(parents=True, exist_ok=True)
    args.output_payload.write_bytes(patched_bytes)
    args.output_container.parent.mkdir(parents=True, exist_ok=True)
    args.output_container.write_bytes(container)
    atlas = patched_bytes[ATLAS_OFFSET:ATLAS_OFFSET + ATLAS_SIZE]
    preview = Image.frombytes("RGBA", (STORAGE_WIDTH, STORAGE_HEIGHT),
                              psp_dxt1_to_pc(atlas), "bcn", (1,))
    preview_path = args.output_payload.with_suffix(".marker.png")
    preview.save(preview_path)

    report = {
        "schema_version": 1,
        "source_payload": str(args.source_payload),
        "output_payload": str(args.output_payload),
        "output_container": str(args.output_container),
        "preview": str(preview_path),
        "atlas_offset": ATLAS_OFFSET,
        "atlas_size": ATLAS_SIZE,
        "storage_width": STORAGE_WIDTH,
        "storage_height": STORAGE_HEIGHT,
        "marker_boxes": MARKER_BOXES,
        "block_map": args.block_map,
        "selected_block_count": len(blocks),
        "changed_byte_count": len(changed),
        "outside_selected_blocks": [],
        "changed_ranges": ranges,
        "source_payload_sha256": sha256(original),
        "output_payload_sha256": sha256(patched_bytes),
        "output_container_sha256": sha256(container),
        "output_container_size": len(container),
        "allocation_size": args.allocation,
        "remaining_slack": args.allocation - len(container),
        "valid": True,
    }
    report_path = args.output_container.with_suffix(args.output_container.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
