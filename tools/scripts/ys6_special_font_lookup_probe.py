#!/usr/bin/env python3
"""Find Ys VI font lookup candidates by comparing relocated MIPS instruction shapes."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

try:
    from tools.scripts.ys12_ys2_event_disasm import apply_psp_relocations, elf_layout
except ModuleNotFoundError:
    from ys12_ys2_event_disasm import apply_psp_relocations, elf_layout


def executable_words(path: Path) -> tuple[bytes, list[tuple[int, int]]]:
    raw = path.read_bytes()
    image, _counts = apply_psp_relocations(raw)
    segments, _sections = elf_layout(raw)
    ranges = [(row["offset"], row["offset"] + row["filesz"]) for row in segments if row["flags"] & 1]
    return bytes(image), ranges


def instruction_shape(word: int) -> tuple[int, int, int, int, int, int]:
    return word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31, (word >> 6) & 31, word & 63


def stride_sites(image: bytes, ranges: list[tuple[int, int]], stride: int) -> list[int]:
    result = []
    for start, end in ranges:
        for offset in range(start, end, 4):
            word = struct.unpack_from("<I", image, offset)[0]
            op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
            if op == 9 and rs == rt and word & 0xFFFF == stride:
                result.append(offset)
    return result


def window_shapes(image: bytes, center: int, radius: int) -> list[tuple[int, int, int, int, int, int]]:
    return [instruction_shape(struct.unpack_from("<I", image, center + delta)[0])
            for delta in range(-radius * 4, (radius + 1) * 4, 4)]


def similarity(left: list[tuple[int, ...]], right: list[tuple[int, ...]]) -> int:
    return sum(a == b for a, b in zip(left, right))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("standard", type=Path)
    parser.add_argument("special", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--radius", type=int, default=12)
    args = parser.parse_args()
    standard, standard_ranges = executable_words(args.standard)
    special, special_ranges = executable_words(args.special)
    standard_sites = stride_sites(standard, standard_ranges, 26)
    special_sites = stride_sites(special, special_ranges, 30)
    rows = []
    for special_offset in special_sites:
        target = window_shapes(special, special_offset, args.radius)
        ranked = sorted(((similarity(target, window_shapes(standard, offset, args.radius)), offset)
                         for offset in standard_sites), reverse=True)
        rows.append({
            "special_offset": f"0x{special_offset:X}",
            "matches": [{"score": score, "standard_offset": f"0x{offset:X}"}
                        for score, offset in ranked[:5]],
        })
    report = {
        "radius": args.radius,
        "window_instruction_count": args.radius * 2 + 1,
        "standard_stride": 26,
        "special_stride": 30,
        "standard_site_count": len(standard_sites),
        "special_site_count": len(special_sites),
        "candidates": sorted(rows, key=lambda row: row["matches"][0]["score"], reverse=True),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
