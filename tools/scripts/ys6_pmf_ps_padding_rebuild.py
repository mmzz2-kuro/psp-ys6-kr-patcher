#!/usr/bin/env python3
"""Rebuild Ys VI PMF video payloads using MPEG-PS padding, not H.264 zero padding."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.scripts.ys6_pmf_rebuild import SECTOR, START_CODE, extract_video, nal_types, split_access_units, video_payload_spans
except ModuleNotFoundError:
    from ys6_pmf_rebuild import SECTOR, START_CODE, extract_video, nal_types, split_access_units, video_payload_spans


@dataclass(frozen=True)
class ScheduledBytes:
    start: int
    end: int
    data: bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def schedule_units(original_units: list[bytes], final_units: list[bytes],
                   replace_start: int, replace_end: int) -> list[ScheduledBytes]:
    boundaries = [0]
    for unit in original_units:
        boundaries.append(boundaries[-1] + len(unit))
    starts = boundaries[:-1].copy()
    next_start = boundaries[replace_end]
    for index in range(replace_end - 1, replace_start - 1, -1):
        end = min(boundaries[index + 1], next_start)
        start = end - len(final_units[index])
        if start < boundaries[replace_start]:
            raise ValueError(
                f"replacement segment overflow before frame {index}: "
                f"{start} < {boundaries[replace_start]}"
            )
        starts[index] = start
        next_start = start
    rows: list[ScheduledBytes] = []
    for index, final in enumerate(final_units):
        start = starts[index]
        rows.append(ScheduledBytes(start, start + len(final), final))
    return rows


def bytes_for_range(schedule: list[ScheduledBytes], start: int, end: int, hint: int) -> tuple[bytes, int]:
    while hint < len(schedule) and schedule[hint].end <= start:
        hint += 1
    pieces: list[bytes] = []
    index = hint
    while index < len(schedule) and schedule[index].start < end:
        row = schedule[index]
        left = max(start, row.start)
        right = min(end, row.end)
        if left < right:
            pieces.append(row.data[left - row.start:right - row.start])
        index += 1
    return b"".join(pieces), hint


def make_padding(length: int) -> bytes:
    if length == 0:
        return b""
    if length < 6:
        return bytes(length)
    payload = length - 6
    if payload > 0xFFFF:
        raise ValueError("padding packet too large")
    return START_CODE + b"\xBE" + payload.to_bytes(2, "big") + bytes([0xFF]) * payload


def rebuild(original_path: Path, encoded_path: Path, output_path: Path,
            replace_start: int, replace_end: int) -> dict:
    original = original_path.read_bytes()
    spans = video_payload_spans(original)
    original_stream = extract_video(original, spans)
    original_units = split_access_units(original_stream)
    encoded_units = split_access_units(encoded_path.read_bytes())
    if len(encoded_units) != len(original_units):
        raise ValueError(f"frame count mismatch: {len(encoded_units)} != {len(original_units)}")
    original_idrs = [i for i, unit in enumerate(original_units) if 5 in nal_types(unit)]
    encoded_idrs = [i for i, unit in enumerate(encoded_units) if 5 in nal_types(unit)]
    if encoded_idrs != original_idrs:
        raise ValueError("encoded IDR positions do not match the original")
    final_units = [encoded_units[i] if replace_start <= i < replace_end else original_units[i]
                   for i in range(len(original_units))]
    schedule = schedule_units(original_units, final_units, replace_start, replace_end)

    span_ranges: dict[tuple[int, int], tuple[int, int]] = {}
    stream_cursor = 0
    for span in spans:
        length = span.end - span.start
        span_ranges[(span.start, span.end)] = (stream_cursor, stream_cursor + length)
        stream_cursor += length

    rebuilt = bytearray(original[:SECTOR])
    hint = 0
    total_ps_padding = 0
    short_zero_padding = 0
    video_payload_output = 0
    for block_offset in range(SECTOR, len(original), SECTOR):
        block = original[block_offset:block_offset + SECTOR]
        if block[:4] != bytes.fromhex("000001ba"):
            raise ValueError(f"missing pack header at 0x{block_offset:X}")
        header_end = 14 + (block[13] & 7)
        output_block = bytearray(block[:header_end])
        pos = header_end
        while pos + 6 <= len(block) and block[pos:pos + 3] == START_CODE:
            stream_id = block[pos + 3]
            packet_length = int.from_bytes(block[pos + 4:pos + 6], "big")
            packet_end = pos + 6 + packet_length
            if packet_end > len(block):
                raise ValueError(f"PES packet crosses pack boundary at 0x{block_offset + pos:X}")
            packet = block[pos:packet_end]
            if stream_id != 0xE0:
                output_block.extend(packet)
            else:
                header_length = block[pos + 8]
                payload_start = pos + 9 + header_length
                absolute_span = (block_offset + payload_start, block_offset + packet_end)
                range_start, range_end = span_ranges[absolute_span]
                payload, hint = bytes_for_range(schedule, range_start, range_end, hint)
                if not payload:
                    freed = packet_end - pos
                    output_block.extend(make_padding(freed))
                    total_ps_padding += freed
                else:
                    pes_header = bytearray(block[pos:payload_start])
                    freed = packet_end - payload_start - len(payload)
                    if 0 < freed < 6:
                        payload += bytes(freed)
                        short_zero_padding += freed
                        freed = 0
                    new_packet_length = len(pes_header) - 6 + len(payload)
                    pes_header[4:6] = new_packet_length.to_bytes(2, "big")
                    output_block.extend(pes_header)
                    output_block.extend(payload)
                    video_payload_output += len(payload)
                    output_block.extend(make_padding(freed))
                    if freed >= 6:
                        total_ps_padding += freed
            pos = packet_end
        output_block.extend(block[pos:])
        if len(output_block) != SECTOR:
            raise AssertionError(f"pack size changed at 0x{block_offset:X}: {len(output_block)}")
        rebuilt.extend(output_block)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rebuilt)
    reread = output_path.read_bytes()
    parsed_spans = video_payload_spans(reread)
    extracted = extract_video(reread, parsed_spans)
    expected_stream = b"".join(final_units)
    if extracted.rstrip(b"\x00") != expected_stream.rstrip(b"\x00"):
        raise AssertionError("rebuilt video stream does not match scheduled access units")
    return {
        "original": str(original_path),
        "encoded": str(encoded_path),
        "output": str(output_path),
        "original_sha256": sha256(original),
        "output_sha256": sha256(reread),
        "size": len(reread),
        "frame_count": len(final_units),
        "replace_start_frame": replace_start,
        "replace_end_frame_exclusive": replace_end,
        "video_payload_original": len(original_stream),
        "video_payload_output": video_payload_output,
        "mpeg_ps_padding_bytes": total_ps_padding,
        "short_zero_padding_bytes": short_zero_padding,
        "maximum_au_early_shift_bytes": max(
            (sum(len(unit) for unit in original_units[:index]) - schedule[index].start
             for index in range(replace_start, replace_end)),
            default=0,
        ),
        "replacement_last_byte_position": schedule[replace_end - 1].end,
        "replacement_original_end_position": sum(len(unit) for unit in original_units[:replace_end]),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("encoded", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--replace-start", type=int, required=True)
    parser.add_argument("--replace-end", type=int, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = rebuild(args.original, args.encoded, args.output, args.replace_start, args.replace_end)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
