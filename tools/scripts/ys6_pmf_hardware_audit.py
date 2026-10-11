#!/usr/bin/env python3
"""Compare original and rebuilt Ys VI PMFs for PSP hardware-sensitive differences."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from tools.scripts.ys6_pmf_rebuild import extract_video, nal_types, split_access_units, video_payload_spans
except ModuleNotFoundError:
    from ys6_pmf_rebuild import extract_video, nal_types, split_access_units, video_payload_spans


START3 = b"\x00\x00\x01"
START4 = b"\x00\x00\x00\x01"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def split_nals(access_unit: bytes) -> list[bytes]:
    starts: list[tuple[int, int]] = []
    cursor = 0
    while cursor + 3 < len(access_unit):
        if access_unit[cursor:cursor + 4] == START4:
            starts.append((cursor, 4))
            cursor += 4
        elif access_unit[cursor:cursor + 3] == START3:
            starts.append((cursor, 3))
            cursor += 3
        else:
            cursor += 1
    result: list[bytes] = []
    for index, (start, prefix) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(access_unit)
        result.append(access_unit[start + prefix:end].rstrip(b"\x00"))
    return [nal for nal in result if nal]


def parameter_sets(unit: bytes) -> list[dict]:
    rows = []
    for nal in split_nals(unit):
        kind = nal[0] & 0x1F
        if kind in (7, 8):
            rows.append({"nal_type": kind, "size": len(nal), "sha256": sha256(nal), "hex": nal.hex()})
    return rows


def audit(original_path: Path, rebuilt_path: Path, replace_start: int, dialogue_start: int) -> dict:
    original = original_path.read_bytes()
    rebuilt = rebuilt_path.read_bytes()
    original_spans = video_payload_spans(original)
    rebuilt_spans = video_payload_spans(rebuilt)
    original_units = split_access_units(extract_video(original, original_spans))
    rebuilt_units = split_access_units(extract_video(rebuilt, rebuilt_spans))
    if len(original_units) != len(rebuilt_units):
        raise ValueError("frame count mismatch")
    rows = []
    for index, (left, right) in enumerate(zip(original_units, rebuilt_units)):
        if left == right:
            continue
        trailing_zero_count = len(right) - len(right.rstrip(b"\x00"))
        rows.append({
            "frame": index,
            "original_size": len(left),
            "rebuilt_size": len(right),
            "rebuilt_nonzero_extent": len(right) - trailing_zero_count,
            "rebuilt_trailing_zero_count": trailing_zero_count,
            "original_nal_types": nal_types(left),
            "rebuilt_nal_types": nal_types(right),
        })
    padding = [row["rebuilt_trailing_zero_count"] for row in rows]
    window = [row for row in rows if replace_start <= row["frame"] <= dialogue_start + 10]
    return {
        "original": {"path": str(original_path), "size": len(original), "sha256": sha256(original)},
        "rebuilt": {"path": str(rebuilt_path), "size": len(rebuilt), "sha256": sha256(rebuilt)},
        "frame_count": len(original_units),
        "video_pes_count": len(original_spans),
        "replace_start_frame": replace_start,
        "dialogue_start_frame": dialogue_start,
        "first_changed_frame": rows[0]["frame"] if rows else None,
        "changed_frame_count": len(rows),
        "total_trailing_zero_padding": sum(padding),
        "maximum_trailing_zero_padding": max(padding, default=0),
        "first_replacement_parameter_sets": {
            "original": parameter_sets(original_units[replace_start]),
            "rebuilt": parameter_sets(rebuilt_units[replace_start]),
        },
        "replacement_to_first_dialogue_window": window,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("rebuilt", type=Path)
    parser.add_argument("--replace-start", type=int, required=True)
    parser.add_argument("--dialogue-start", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.original, args.rebuilt, args.replace_start, args.dialogue_start)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
