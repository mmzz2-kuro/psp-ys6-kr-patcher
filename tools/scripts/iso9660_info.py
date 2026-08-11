#!/usr/bin/env python3
"""Read-only ISO 9660 file extent inspector."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SECTOR_SIZE = 2048
PVD_SECTOR = 16


class Iso9660Error(Exception):
    pass


@dataclass
class DirectoryRecord:
    name: str
    extent_lba: int
    data_length: int
    is_directory: bool
    record_byte_offset: int


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def normalize_name(name: str) -> str:
    return name.split(";", 1)[0].rstrip(".").upper()


def parse_record(data: bytes, offset: int, base_byte_offset: int = 0) -> DirectoryRecord:
    length = data[offset]
    if length < 34 or offset + length > len(data):
        raise Iso9660Error(f"잘못된 디렉터리 레코드 길이: offset={offset}, length={length}")
    extent_lba = struct.unpack_from("<I", data, offset + 2)[0]
    data_length = struct.unpack_from("<I", data, offset + 10)[0]
    flags = data[offset + 25]
    name_length = data[offset + 32]
    raw_name = data[offset + 33 : offset + 33 + name_length]
    if raw_name == b"\x00":
        name = "."
    elif raw_name == b"\x01":
        name = ".."
    else:
        try:
            name = raw_name.decode("ascii")
        except UnicodeDecodeError as exc:
            raise Iso9660Error(f"ASCII가 아닌 ISO 9660 식별자: {raw_name.hex()}") from exc
    return DirectoryRecord(
        name,
        extent_lba,
        data_length,
        bool(flags & 0x02),
        base_byte_offset + offset,
    )


def read_directory(handle, record: DirectoryRecord) -> list[DirectoryRecord]:
    handle.seek(record.extent_lba * SECTOR_SIZE)
    data = handle.read(record.data_length)
    if len(data) != record.data_length:
        raise Iso9660Error("디렉터리 데이터를 끝까지 읽지 못했습니다")
    records: list[DirectoryRecord] = []
    offset = 0
    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset = ((offset // SECTOR_SIZE) + 1) * SECTOR_SIZE
            continue
        record_item = parse_record(data, offset, record.extent_lba * SECTOR_SIZE)
        if record_item.name not in (".", ".."):
            records.append(record_item)
        offset += length
    return records


def find_record(iso_path: Path, internal_path: str) -> DirectoryRecord:
    parts = [normalize_name(part) for part in internal_path.replace("\\", "/").split("/") if part]
    if not parts:
        raise Iso9660Error("ISO 내부 경로가 비어 있습니다")
    with iso_path.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        if len(pvd) != SECTOR_SIZE or pvd[0] != 1 or pvd[1:6] != b"CD001":
            raise Iso9660Error("Primary Volume Descriptor를 찾을 수 없습니다")
        current = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for index, part in enumerate(parts):
            entries = read_directory(handle, current)
            match = next((entry for entry in entries if normalize_name(entry.name) == part), None)
            if match is None:
                raise Iso9660Error(f"ISO 내부 엔트리를 찾을 수 없습니다: {'/'.join(parts[:index + 1])}")
            if index < len(parts) - 1 and not match.is_directory:
                raise Iso9660Error(f"중간 경로가 디렉터리가 아닙니다: {match.name}")
            current = match
        return current


def command_info(args: argparse.Namespace) -> int:
    try:
        record = find_record(args.iso, args.path)
    except (OSError, Iso9660Error) as exc:
        print(f"ISO 엔트리를 조회할 수 없습니다: {exc}", file=sys.stderr)
        return 1
    allocated_sectors = math.ceil(record.data_length / SECTOR_SIZE)
    payload = {
        "iso": str(args.iso),
        "path": args.path.replace("\\", "/"),
        "record": asdict(record),
        "byte_offset": record.extent_lba * SECTOR_SIZE,
        "allocated_sectors": allocated_sectors,
        "allocated_bytes": allocated_sectors * SECTOR_SIZE,
        "last_sector_slack": allocated_sectors * SECTOR_SIZE - record.data_length,
        "data_length_le_offset": record.record_byte_offset + 10,
        "data_length_be_offset": record.record_byte_offset + 14,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "\n".join(
        f"{key}: {value}" for key, value in payload.items()
    ))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="읽기 전용 ISO 9660 파일 LBA/할당 조회기")
    parser.add_argument("iso", type=Path)
    parser.add_argument("path", help="ISO 내부 파일 경로")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(func=command_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
