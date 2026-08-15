#!/usr/bin/env python3
"""Patch selected optionselect DXT3 blocks inside Ys VI _static_tex MIG."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from tools.scripts.ys6_z import build_container, verify_container_bytes
except ModuleNotFoundError:
    from ys6_z import build_container, verify_container_bytes


OPTION_DXT_OFFSET = 0x70
OPTION_DXT_SIZE = 0x10000
STATIC_DXT_OFFSET = 0x106120


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def execute(static_payload_path: Path, original_option_path: Path, modified_option_path: Path,
            marker_report_path: Path, output_payload: Path, output_container: Path,
            allocation: int) -> dict:
    static_original = static_payload_path.read_bytes()
    option_original = original_option_path.read_bytes()
    option_modified = modified_option_path.read_bytes()
    marker = json.loads(marker_report_path.read_text(encoding="utf-8-sig"))
    original_dxt = option_original[OPTION_DXT_OFFSET:OPTION_DXT_OFFSET + OPTION_DXT_SIZE]
    modified_dxt = option_modified[OPTION_DXT_OFFSET:OPTION_DXT_OFFSET + OPTION_DXT_SIZE]
    static_dxt = static_original[STATIC_DXT_OFFSET:STATIC_DXT_OFFSET + OPTION_DXT_SIZE]
    if len(original_dxt) != OPTION_DXT_SIZE or len(modified_dxt) != OPTION_DXT_SIZE:
        raise ValueError("optionselect DXT3 payload size mismatch")
    if static_dxt != original_dxt:
        raise ValueError("_static_tex embedded DXT3 does not match original optionselect")
    block_indices = sorted({int(item["stored_block_index"]) for item in marker["block_map"]})
    patched = bytearray(static_original)
    changed_ranges = []
    for block_index in block_indices:
        option_offset = OPTION_DXT_OFFSET + block_index * 16
        static_offset = STATIC_DXT_OFFSET + block_index * 16
        replacement = option_modified[option_offset:option_offset + 16]
        if len(replacement) != 16:
            raise ValueError(f"invalid DXT3 block index: {block_index}")
        patched[static_offset:static_offset + 16] = replacement
        changed_ranges.append({
            "stored_block_index": block_index, "static_payload_offset": static_offset,
            "original_block_sha256": sha256(static_original[static_offset:static_offset + 16]),
            "replacement_block_sha256": sha256(replacement),
        })
    changed_positions = [index for index, (left, right) in enumerate(zip(static_original, patched)) if left != right]
    allowed = set()
    for block_index in block_indices:
        start = STATIC_DXT_OFFSET + block_index * 16; allowed.update(range(start, start + 16))
    outside = [index for index in changed_positions if index not in allowed]
    if outside:
        raise ValueError(f"changes outside selected DXT3 blocks: first=0x{outside[0]:X}")
    patched_bytes = bytes(patched)
    container = build_container(patched_bytes, 9)
    valid, verified_payload, error = verify_container_bytes(container)
    if not valid or verified_payload != patched_bytes:
        raise ValueError(f"rebuilt static texture container failed verification: {error}")
    if len(container) > allocation:
        raise ValueError(f"rebuilt container exceeds allocation: {len(container)} > {allocation}")
    output_payload.parent.mkdir(parents=True, exist_ok=True); output_payload.write_bytes(patched_bytes)
    output_container.parent.mkdir(parents=True, exist_ok=True); output_container.write_bytes(container)
    report = {
        "schema_version": 1, "static_payload": str(static_payload_path),
        "original_option": str(original_option_path), "modified_option": str(modified_option_path),
        "marker_report": str(marker_report_path), "output_payload": str(output_payload),
        "output_container": str(output_container), "static_dxt_offset": STATIC_DXT_OFFSET,
        "static_dxt_size": OPTION_DXT_SIZE, "embedded_original_identical": True,
        "selected_block_count": len(block_indices), "changed_byte_count": len(changed_positions),
        "outside_selected_blocks": [], "changed_ranges": changed_ranges,
        "original_payload_sha256": sha256(static_original), "output_payload_sha256": sha256(patched_bytes),
        "output_container_sha256": sha256(container), "output_container_size": len(container),
        "allocation_size": allocation, "remaining_slack": allocation - len(container), "valid": True,
    }
    report_path = output_container.with_suffix(output_container.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(report_path)
    return report


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("static_payload", type=Path); parser.add_argument("original_option", type=Path)
    parser.add_argument("modified_option", type=Path); parser.add_argument("marker_report", type=Path)
    parser.add_argument("output_payload", type=Path); parser.add_argument("output_container", type=Path)
    parser.add_argument("--allocation", type=lambda value: int(value, 0), required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args.static_payload, args.original_option, args.modified_option, args.marker_report,
                         args.output_payload, args.output_container, args.allocation)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"통합 텍스처 내장 패치 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
