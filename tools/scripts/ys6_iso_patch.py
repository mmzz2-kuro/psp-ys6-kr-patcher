#!/usr/bin/env python3
"""Safely replace one ISO 9660 file in a copied Ys VI PSP ISO."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from tools.scripts.iso9660_info import DirectoryRecord, SECTOR_SIZE, find_record
except ModuleNotFoundError:  # Direct execution: python tools/scripts/ys6_iso_patch.py
    from iso9660_info import DirectoryRecord, SECTOR_SIZE, find_record


class IsoPatchError(Exception):
    pass


@dataclass
class DifferenceRange:
    start: int
    end_exclusive: int
    length: int


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_and_verify_record(handle, record: DirectoryRecord) -> None:
    handle.seek(record.record_byte_offset)
    raw = handle.read(34)
    if len(raw) < 34:
        raise IsoPatchError("ISO 9660 디렉터리 레코드를 끝까지 읽지 못했습니다")
    extent_le = struct.unpack_from("<I", raw, 2)[0]
    extent_be = struct.unpack_from(">I", raw, 6)[0]
    size_le = struct.unpack_from("<I", raw, 10)[0]
    size_be = struct.unpack_from(">I", raw, 14)[0]
    if extent_le != record.extent_lba or extent_be != record.extent_lba:
        raise IsoPatchError(
            f"extent LE/BE 불일치: parsed={record.extent_lba}, LE={extent_le}, BE={extent_be}"
        )
    if size_le != record.data_length or size_be != record.data_length:
        raise IsoPatchError(
            f"size LE/BE 불일치: parsed={record.data_length}, LE={size_le}, BE={size_be}"
        )


def verify_source_entry(
    iso: Path,
    record: DirectoryRecord,
    expected_size: int,
    expected_sha256: str,
) -> bytes:
    if record.is_directory:
        raise IsoPatchError("대상 엔트리가 파일이 아니라 디렉터리입니다")
    if record.data_length != expected_size:
        raise IsoPatchError(
            f"대상 파일 크기 불일치: expected={expected_size}, actual={record.data_length}"
        )
    with iso.open("rb") as handle:
        read_and_verify_record(handle, record)
        handle.seek(record.extent_lba * SECTOR_SIZE)
        data = handle.read(record.data_length)
    if len(data) != record.data_length:
        raise IsoPatchError("대상 extent 데이터를 끝까지 읽지 못했습니다")
    actual_hash = hashlib.sha256(data).hexdigest().upper()
    if actual_hash != expected_sha256.upper():
        raise IsoPatchError(
            f"대상 파일 SHA-256 불일치: expected={expected_sha256.upper()}, actual={actual_hash}"
        )
    return data


def apply_patch_to_copy(
    source: Path,
    output: Path,
    record: DirectoryRecord,
    replacement: bytes,
    overwrite: bool = False,
) -> None:
    source_resolved = source.resolve()
    output_resolved = output.resolve()
    if source_resolved == output_resolved:
        raise IsoPatchError("원본 ISO와 출력 ISO 경로가 같습니다")
    allocated_sectors = math.ceil(record.data_length / SECTOR_SIZE)
    allocated_bytes = allocated_sectors * SECTOR_SIZE
    if len(replacement) > allocated_bytes:
        raise IsoPatchError(
            f"교체 파일이 기존 할당 공간을 초과합니다: replacement={len(replacement)}, "
            f"allocated={allocated_bytes}"
        )
    if output.exists() and not overwrite:
        raise IsoPatchError(f"출력 ISO가 이미 존재합니다: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    with output.open("r+b") as handle:
        handle.seek(record.extent_lba * SECTOR_SIZE)
        handle.write(replacement)
        handle.write(b"\x00" * (allocated_bytes - len(replacement)))
        handle.seek(record.record_byte_offset + 10)
        handle.write(struct.pack("<I", len(replacement)))
        handle.seek(record.record_byte_offset + 14)
        handle.write(struct.pack(">I", len(replacement)))
        handle.flush()


def collect_difference_ranges(left: Path, right: Path, chunk_size: int = 1024 * 1024) -> list[DifferenceRange]:
    if left.stat().st_size != right.stat().st_size:
        raise IsoPatchError("diff 대상 파일 크기가 다릅니다")
    ranges: list[DifferenceRange] = []
    open_start: int | None = None
    absolute = 0
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_chunk = left_handle.read(chunk_size)
            right_chunk = right_handle.read(chunk_size)
            if not left_chunk:
                break
            if left_chunk == right_chunk:
                if open_start is not None:
                    ranges.append(
                        DifferenceRange(open_start, absolute, absolute - open_start)
                    )
                    open_start = None
                absolute += len(left_chunk)
                continue
            for index, (left_byte, right_byte) in enumerate(zip(left_chunk, right_chunk)):
                position = absolute + index
                if left_byte != right_byte and open_start is None:
                    open_start = position
                elif left_byte == right_byte and open_start is not None:
                    ranges.append(DifferenceRange(open_start, position, position - open_start))
                    open_start = None
            absolute += len(left_chunk)
    if open_start is not None:
        ranges.append(DifferenceRange(open_start, absolute, absolute - open_start))
    return ranges


def range_is_allowed(item: DifferenceRange, allowed: list[tuple[int, int]]) -> bool:
    return any(item.start >= start and item.end_exclusive <= end for start, end in allowed)


def command_patch(args: argparse.Namespace) -> int:
    try:
        source_hash = sha256_file(args.source)
        if source_hash != args.expected_iso_sha256.upper():
            raise IsoPatchError(
                f"원본 ISO SHA-256 불일치: expected={args.expected_iso_sha256.upper()}, actual={source_hash}"
            )
        replacement = args.replacement.read_bytes()
        record = find_record(args.source, args.path)
        original_entry = verify_source_entry(
            args.source,
            record,
            args.expected_file_size,
            args.expected_file_sha256,
        )
        apply_patch_to_copy(args.source, args.output, record, replacement, args.overwrite)
        patched_record = find_record(args.output, args.path)
        with args.output.open("rb") as handle:
            read_and_verify_record(handle, patched_record)
            handle.seek(patched_record.extent_lba * SECTOR_SIZE)
            patched_entry = handle.read(patched_record.data_length)
        if patched_record.extent_lba != record.extent_lba:
            raise IsoPatchError("패치 후 extent LBA가 변경됐습니다")
        if patched_entry != replacement:
            raise IsoPatchError("패치 ISO에서 다시 읽은 데이터가 교체 파일과 다릅니다")
        ranges = collect_difference_ranges(args.source, args.output)
        allocated_bytes = math.ceil(record.data_length / SECTOR_SIZE) * SECTOR_SIZE
        allowed = [
            (record.record_byte_offset + 10, record.record_byte_offset + 14),
            (record.record_byte_offset + 14, record.record_byte_offset + 18),
            (record.extent_lba * SECTOR_SIZE, record.extent_lba * SECTOR_SIZE + allocated_bytes),
        ]
        outside = [item for item in ranges if not range_is_allowed(item, allowed)]
        if outside:
            raise IsoPatchError(f"허용 범위 밖 변경이 있습니다: {outside}")
        result = {
            "source": str(args.source),
            "output": str(args.output),
            "internal_path": args.path.replace("\\", "/"),
            "source_iso_sha256": source_hash,
            "output_iso_sha256": sha256_file(args.output),
            "iso_size": args.output.stat().st_size,
            "extent_lba": record.extent_lba,
            "extent_byte_offset": record.extent_lba * SECTOR_SIZE,
            "directory_record_offset": record.record_byte_offset,
            "original_file_size": len(original_entry),
            "replacement_file_size": len(replacement),
            "allocated_bytes": allocated_bytes,
            "remaining_slack": allocated_bytes - len(replacement),
            "replacement_sha256": hashlib.sha256(replacement).hexdigest().upper(),
            "patched_entry_sha256": hashlib.sha256(patched_entry).hexdigest().upper(),
            "difference_ranges": [asdict(item) for item in ranges],
            "outside_allowed_ranges": [],
            "valid": True,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, IsoPatchError) as exc:
        print(f"ISO 패치 실패: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ys VI PSP ISO 단일 파일 안전 교체 도구")
    parser.add_argument("source", type=Path)
    parser.add_argument("path", help="ISO 내부 파일 경로")
    parser.add_argument("replacement", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-iso-sha256", required=True)
    parser.add_argument("--expected-file-size", required=True, type=int)
    parser.add_argument("--expected-file-sha256", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.set_defaults(func=command_patch)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
