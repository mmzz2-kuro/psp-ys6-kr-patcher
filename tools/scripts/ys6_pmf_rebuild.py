#!/usr/bin/env python3
"""Inspect and rebuild Ys VI PSMF files while preserving non-video packets."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


SECTOR = 0x800
START_CODE = bytes.fromhex("000001")
AUD = bytes.fromhex("0000000109")


@dataclass(frozen=True)
class PayloadSpan:
    start: int
    end: int


def video_payload_spans(data: bytes) -> list[PayloadSpan]:
    spans: list[PayloadSpan] = []
    if data[:4] != b"PSMF" or len(data) % SECTOR:
        raise ValueError("not an aligned PSMF file")
    for block_offset in range(SECTOR, len(data), SECTOR):
        block = data[block_offset:block_offset + SECTOR]
        if block[:4] != bytes.fromhex("000001ba"):
            raise ValueError(f"missing pack header at 0x{block_offset:X}")
        pos = 14 + (block[13] & 7)
        while pos + 6 <= len(block) and block[pos:pos + 3] == START_CODE:
            stream_id = block[pos + 3]
            packet_length = int.from_bytes(block[pos + 4:pos + 6], "big")
            end = pos + 6 + packet_length
            if end > len(block):
                raise ValueError(f"PES packet crosses pack boundary at 0x{block_offset + pos:X}")
            if stream_id == 0xE0:
                header_length = block[pos + 8]
                payload_start = pos + 9 + header_length
                spans.append(PayloadSpan(block_offset + payload_start, block_offset + end))
            pos = end
    return spans


def extract_video(data: bytes, spans: list[PayloadSpan]) -> bytes:
    return b"".join(data[span.start:span.end] for span in spans)


def split_access_units(stream: bytes) -> list[bytes]:
    offsets: list[int] = []
    cursor = 0
    while True:
        found = stream.find(AUD, cursor)
        if found < 0:
            break
        offsets.append(found)
        cursor = found + len(AUD)
    if not offsets or offsets[0] != 0:
        raise ValueError("H.264 stream does not begin with an AUD")
    return [stream[start:(offsets[index + 1] if index + 1 < len(offsets) else len(stream))]
            for index, start in enumerate(offsets)]


def nal_types(access_unit: bytes) -> list[int]:
    result: list[int] = []
    cursor = 0
    while cursor + 4 < len(access_unit):
        if access_unit[cursor:cursor + 4] == bytes.fromhex("00000001"):
            result.append(access_unit[cursor + 4] & 0x1F)
            cursor += 5
        elif access_unit[cursor:cursor + 3] == START_CODE:
            result.append(access_unit[cursor + 3] & 0x1F)
            cursor += 4
        else:
            cursor += 1
    return result


def inspect(pmf: Path) -> dict:
    data = pmf.read_bytes()
    spans = video_payload_spans(data)
    stream = extract_video(data, spans)
    units = split_access_units(stream)
    idr_frames = [index for index, unit in enumerate(units) if 5 in nal_types(unit)]
    return {
        "path": str(pmf),
        "size": len(data),
        "header_size": SECTOR,
        "stream_size_header": int.from_bytes(data[12:16], "big"),
        "video_pes_count": len(spans),
        "video_payload_size": len(stream),
        "frame_count": len(units),
        "idr_frames": idr_frames,
        "idr_intervals": [right - left for left, right in zip(idr_frames, idr_frames[1:])],
        "frame_sizes": [len(unit) for unit in units],
    }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def rebuild(original_pmf: Path, encoded_h264: Path, output: Path,
            dialogue_start: int, dialogue_end: int) -> dict:
    original = original_pmf.read_bytes()
    spans = video_payload_spans(original)
    original_stream = extract_video(original, spans)
    original_units = split_access_units(original_stream)
    encoded_units = split_access_units(encoded_h264.read_bytes())
    if len(encoded_units) != len(original_units):
        raise ValueError(f"frame count mismatch: {len(encoded_units)} != {len(original_units)}")
    original_idrs = [index for index, unit in enumerate(original_units) if 5 in nal_types(unit)]
    encoded_idrs = [index for index, unit in enumerate(encoded_units) if 5 in nal_types(unit)]
    if encoded_idrs != original_idrs:
        raise ValueError("encoded IDR positions do not match the original")
    replace_start = max(index for index in original_idrs if index <= dialogue_start)
    replace_end = min(index for index in original_idrs if index > dialogue_end)
    final_units: list[bytes] = []
    padding_bytes = 0
    maximum_slack = 0
    for index, original_unit in enumerate(original_units):
        if replace_start <= index < replace_end:
            replacement = encoded_units[index]
            if len(replacement) > len(original_unit):
                raise ValueError(
                    f"access unit overflow at frame {index}: {len(replacement)} > {len(original_unit)}"
                )
            slack = len(original_unit) - len(replacement)
            # Annex B permits trailing_zero_8bits between NAL units.
            final_units.append(replacement + bytes(slack))
            padding_bytes += slack
            maximum_slack = max(maximum_slack, slack)
        else:
            final_units.append(original_unit)
    final_stream = b"".join(final_units)
    if len(final_stream) != len(original_stream):
        raise AssertionError("rebuilt elementary stream size changed")
    rebuilt = bytearray(original)
    cursor = 0
    for span in spans:
        length = span.end - span.start
        rebuilt[span.start:span.end] = final_stream[cursor:cursor + length]
        cursor += length
    if cursor != len(final_stream):
        raise AssertionError("not all elementary stream bytes were written")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rebuilt)
    reread = output.read_bytes()
    if len(reread) != len(original) or reread[:SECTOR] != original[:SECTOR]:
        raise AssertionError("PSMF header or file size changed")
    changed_spans = [(span.start, span.end) for span in spans]
    outside_changes = []
    span_index = 0
    for index, (left, right) in enumerate(zip(original, reread)):
        while span_index < len(changed_spans) and index >= changed_spans[span_index][1]:
            span_index += 1
        inside = span_index < len(changed_spans) and changed_spans[span_index][0] <= index
        if left != right and not inside:
            outside_changes.append(index)
            if len(outside_changes) >= 20:
                break
    if outside_changes:
        raise AssertionError(f"changes outside video payload: {outside_changes}")
    return {
        "original_pmf": str(original_pmf),
        "encoded_h264": str(encoded_h264),
        "output_pmf": str(output),
        "original_sha256": sha256(original),
        "output_sha256": sha256(reread),
        "size": len(reread),
        "frame_count": len(original_units),
        "video_pes_count": len(spans),
        "dialogue_start_frame": dialogue_start,
        "dialogue_end_frame": dialogue_end,
        "replace_start_frame": replace_start,
        "replace_end_frame_exclusive": replace_end,
        "replaced_frame_count": replace_end - replace_start,
        "padding_bytes": padding_bytes,
        "maximum_frame_slack": maximum_slack,
        "header_preserved": True,
        "non_video_bytes_preserved": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pmf", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--encoded", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dialogue-start", type=int)
    parser.add_argument("--dialogue-end", type=int)
    args = parser.parse_args()
    if args.encoded:
        if len(args.pmf) != 1 or args.output is None or args.dialogue_start is None or args.dialogue_end is None:
            parser.error("rebuild requires one PMF, --encoded, --output, --dialogue-start and --dialogue-end")
        reports = [rebuild(args.pmf[0], args.encoded, args.output, args.dialogue_start, args.dialogue_end)]
    else:
        reports = [inspect(path) for path in args.pmf]
    text = json.dumps(reports, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
