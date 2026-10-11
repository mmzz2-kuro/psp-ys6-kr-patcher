#!/usr/bin/env python3
"""Merge PSP-muxed video packs with private-stream packs from an original PMF."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

SECTOR_SIZE = 0x800
HEADER_SIZE = 0x800
PACK_START = b"\x00\x00\x01\xBA"

class MergeError(RuntimeError):
    pass

@dataclass(frozen=True)
class TimedPack:
    scr_27mhz: int
    source_order: int
    ordinal: int
    data: bytes

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def split_packs(data: bytes, label: str) -> list[bytes]:
    if len(data) % SECTOR_SIZE:
        raise MergeError(f"{label}: 크기가 0x800 배수가 아닙니다: {len(data)}")
    packs = [data[offset:offset + SECTOR_SIZE] for offset in range(0, len(data), SECTOR_SIZE)]
    for index, pack in enumerate(packs):
        if not pack.startswith(PACK_START):
            raise MergeError(f"{label}: pack {index}에 MPEG-PS pack header가 없습니다")
    return packs

def decode_scr_27mhz(pack: bytes) -> int:
    if not pack.startswith(PACK_START) or len(pack) < 10:
        raise MergeError("유효하지 않은 MPEG-PS pack입니다")
    p = pack[4:10]
    base = (((p[0] & 0x38) >> 3) << 30 | (p[0] & 0x03) << 28 | p[1] << 20 |
            ((p[2] & 0xF8) >> 3) << 15 | (p[2] & 0x03) << 13 | p[3] << 5 |
            ((p[4] & 0xF8) >> 3))
    extension = ((p[4] & 0x03) << 7) | (p[5] >> 1)
    return base * 300 + extension

def contains_stream(pack: bytes, stream_id: int) -> bool:
    return b"\x00\x00\x01" + bytes([stream_id]) in pack

def count_streams(packs: list[bytes]) -> dict[str, int]:
    ids = (0xE0, 0xBD, 0xBB, 0xBF, 0xBE)
    return {f"0x{stream_id:02X}": sum(contains_stream(pack, stream_id) for pack in packs) for stream_id in ids}

def merge(original_pmf: bytes, video_mps: bytes) -> tuple[bytes, dict[str, object]]:
    if len(original_pmf) < HEADER_SIZE or original_pmf[:4] != b"PSMF":
        raise MergeError("원본 파일에 PSMF 헤더가 없습니다")
    original_packs = split_packs(original_pmf[HEADER_SIZE:], "original PMF")
    video_packs = split_packs(video_mps, "video MPS")
    private_packs = [pack for pack in original_packs if contains_stream(pack, 0xBD)]
    if not private_packs:
        raise MergeError("원본 PMF에서 0xBD private stream을 찾지 못했습니다")
    if any(contains_stream(pack, 0xBD) for pack in video_packs):
        raise MergeError("새 video MPS에 예상하지 않은 0xBD stream이 있습니다")
    timed = ([TimedPack(decode_scr_27mhz(pack), 0, i, pack) for i, pack in enumerate(video_packs)] +
             [TimedPack(decode_scr_27mhz(pack), 1, i, pack) for i, pack in enumerate(private_packs)])
    timed.sort(key=lambda item: (item.scr_27mhz, item.source_order, item.ordinal))
    merged_packs = [item.data for item in timed]
    scrs = [item.scr_27mhz for item in timed]
    if any(left > right for left, right in zip(scrs, scrs[1:])):
        raise MergeError("병합 결과의 SCR 순서가 역전되었습니다")
    body = b"".join(merged_packs)
    header = bytearray(original_pmf[:HEADER_SIZE])
    header[12:16] = struct.pack(">I", len(body))
    output = bytes(header) + body
    report: dict[str, object] = {
        "original_size": len(original_pmf), "video_mps_size": len(video_mps), "output_size": len(output),
        "fits_original_allocation": len(output) <= len(original_pmf), "original_pack_count": len(original_packs),
        "video_pack_count": len(video_packs), "preserved_private_pack_count": len(private_packs),
        "output_pack_count": len(merged_packs), "original_stream_pack_counts": count_streams(original_packs),
        "video_stream_pack_counts": count_streams(video_packs), "output_stream_pack_counts": count_streams(merged_packs),
        "first_scr_27mhz": scrs[0], "last_scr_27mhz": scrs[-1], "sha256": sha256(output),
    }
    if not report["fits_original_allocation"]:
        raise MergeError("병합 PMF가 원본 ISO 할당 크기를 초과합니다")
    return output, report

def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_pmf", type=Path); parser.add_argument("video_mps", type=Path)
    parser.add_argument("output_pmf", type=Path); parser.add_argument("--report", type=Path)
    parser.add_argument("--overwrite", action="store_true"); args = parser.parse_args(argv)
    try:
        if args.output_pmf.exists() and not args.overwrite:
            raise MergeError(f"출력 파일이 이미 있습니다: {args.output_pmf}")
        output, report = merge(args.original_pmf.read_bytes(), args.video_mps.read_bytes())
        args.output_pmf.parent.mkdir(parents=True, exist_ok=True); args.output_pmf.write_bytes(output)
        report.update({"original_pmf": str(args.original_pmf), "video_mps": str(args.video_mps), "output_pmf": str(args.output_pmf)})
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    except (OSError, MergeError) as exc:
        print(f"PMF pack 병합 실패: {exc}", file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())
