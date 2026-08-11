#!/usr/bin/env python3
"""Inspect, extract, and safely replace files in Ys VI PSP map .bin archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


RECORD_SIZE = 40
NAME_SIZE = 28
FILE_FLAG = 0x01000000
ALIGNMENT = 0x800


class ArcError(Exception):
    pass


@dataclass(frozen=True)
class ArcEntry:
    index: int
    name: str
    flags: int
    offset: int
    size: int
    record_offset: int
    size_field_offset: int
    allocated_size: int = 0


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_archive(data: bytes) -> list[ArcEntry]:
    if len(data) < 4:
        raise ArcError("아카이브가 헤더보다 짧습니다")
    table_end = struct.unpack_from("<I", data, 0)[0]
    if table_end < 4 or table_end > len(data) or (table_end - 4) % RECORD_SIZE:
        raise ArcError(f"잘못된 파일 테이블 끝 오프셋: 0x{table_end:X}")
    raw_entries = []
    for index, record_offset in enumerate(range(4, table_end, RECORD_SIZE)):
        raw_name = data[record_offset : record_offset + NAME_SIZE].split(b"\0", 1)[0]
        try:
            name = raw_name.decode("cp932")
        except UnicodeDecodeError as exc:
            raise ArcError(f"레코드 {index} 이름이 CP932가 아닙니다") from exc
        flags, offset, size = struct.unpack_from("<III", data, record_offset + NAME_SIZE)
        raw_entries.append((index, name, flags, offset, size, record_offset))

    files = [item for item in raw_entries if item[2] == FILE_FLAG]
    offsets = [item[3] for item in files]
    if len(offsets) != len(set(offsets)):
        raise ArcError("파일 데이터 오프셋이 중복됩니다")
    for index, name, _flags, offset, size, _record_offset in files:
        if offset % ALIGNMENT:
            raise ArcError(f"파일 오프셋이 0x800 정렬이 아닙니다: {name} @ 0x{offset:X}")
        if offset < table_end or offset + size > len(data):
            raise ArcError(f"파일 범위가 아카이브 밖입니다: {name}")

    files_by_offset = sorted(files, key=lambda item: item[3])
    next_offsets = {
        item[3]: (files_by_offset[pos + 1][3] if pos + 1 < len(files_by_offset) else len(data))
        for pos, item in enumerate(files_by_offset)
    }
    entries = []
    for index, name, flags, offset, size, record_offset in raw_entries:
        allocated = next_offsets[offset] - offset if flags == FILE_FLAG else 0
        if flags == FILE_FLAG and size > allocated:
            raise ArcError(f"파일 크기가 할당 공간을 초과합니다: {name}")
        entries.append(ArcEntry(index, name, flags, offset, size, record_offset, record_offset + 36, allocated))
    return entries


def find_file(entries: list[ArcEntry], name: str) -> ArcEntry:
    matches = [entry for entry in entries if entry.flags == FILE_FLAG and entry.name.casefold() == name.casefold()]
    if not matches:
        raise ArcError(f"파일 엔트리를 찾을 수 없습니다: {name}")
    if len(matches) != 1:
        raise ArcError(f"중복 파일명이 있어 안전하게 선택할 수 없습니다: {name}")
    return matches[0]


def replace_file(data: bytes, entry: ArcEntry, replacement: bytes) -> bytes:
    if len(replacement) > entry.allocated_size:
        raise ArcError(
            f"교체 파일이 할당 공간을 초과합니다: replacement={len(replacement)}, allocated={entry.allocated_size}"
        )
    output = bytearray(data)
    struct.pack_into("<I", output, entry.size_field_offset, len(replacement))
    output[entry.offset : entry.offset + entry.allocated_size] = replacement + bytes(entry.allocated_size - len(replacement))
    return bytes(output)


def write_new(path: Path, data: bytes, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise ArcError(f"출력 파일이 이미 존재합니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def entry_json(entry: ArcEntry) -> dict:
    result = asdict(entry)
    result["flags_hex"] = f"0x{entry.flags:08X}"
    return result


def command_info(args) -> int:
    data = args.archive.read_bytes()
    entries = parse_archive(data)
    payload = {
        "archive": str(args.archive),
        "archive_size": len(data),
        "archive_sha256": sha256(data),
        "table_end": struct.unpack_from("<I", data, 0)[0],
        "record_count": len(entries),
        "file_count": sum(entry.flags == FILE_FLAG for entry in entries),
    }
    if args.name:
        payload["entry"] = entry_json(find_file(entries, args.name))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_extract(args) -> int:
    data = args.archive.read_bytes()
    entry = find_file(parse_archive(data), args.name)
    extracted = data[entry.offset : entry.offset + entry.size]
    write_new(args.output, extracted, args.overwrite)
    print(json.dumps({"entry": entry_json(entry), "output": str(args.output), "sha256": sha256(extracted)}, ensure_ascii=False, indent=2))
    return 0


def command_replace(args) -> int:
    data = args.archive.read_bytes()
    entry = find_file(parse_archive(data), args.name)
    replacement = args.replacement.read_bytes()
    output = replace_file(data, entry, replacement)
    reparsed = find_file(parse_archive(output), args.name)
    if output[reparsed.offset : reparsed.offset + reparsed.size] != replacement:
        raise ArcError("교체 후 엔트리 재검증에 실패했습니다")
    write_new(args.output, output, args.overwrite)
    print(json.dumps({
        "archive": str(args.archive), "output": str(args.output), "entry": entry_json(entry),
        "original_size": entry.size, "replacement_size": len(replacement),
        "remaining_slack": entry.allocated_size - len(replacement),
        "replacement_sha256": sha256(replacement), "output_sha256": sha256(output), "valid": True,
    }, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    info = sub.add_parser("info")
    info.add_argument("archive", type=Path)
    info.add_argument("--name")
    info.set_defaults(func=command_info)
    extract = sub.add_parser("extract")
    extract.add_argument("archive", type=Path)
    extract.add_argument("name")
    extract.add_argument("output", type=Path)
    extract.add_argument("--overwrite", action="store_true")
    extract.set_defaults(func=command_extract)
    replace = sub.add_parser("replace")
    replace.add_argument("archive", type=Path)
    replace.add_argument("name")
    replace.add_argument("replacement", type=Path)
    replace.add_argument("output", type=Path)
    replace.add_argument("--overwrite", action="store_true")
    replace.set_defaults(func=command_replace)
    return parser


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ArcError) as exc:
        print(f"아카이브 처리 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
