#!/usr/bin/env python3
"""Parse and safely patch fixed-width Ys VI invinfo.dat text fields."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

HEADER_SIZE = 16
RECORD_SIZE = 184
RECORD_COUNT = 73
NAME_SIZE = 32
METADATA_SIZE = 44
DESCRIPTION_SIZE = 108


@dataclass(frozen=True)
class ItemRecord:
    index: int
    offset: int
    resource_id: str
    name_raw: bytes
    description_raw: bytes
    metadata: bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse(data: bytes) -> list[ItemRecord]:
    if len(data) != HEADER_SIZE + RECORD_SIZE * RECORD_COUNT:
        raise ValueError(f"invinfo.dat size mismatch: {len(data)}")
    record_size, count = struct.unpack_from("<II", data, 8)
    if (record_size, count) != (RECORD_SIZE, RECORD_COUNT):
        raise ValueError(f"invinfo.dat layout mismatch: record_size={record_size}, count={count}")
    records = []
    for index in range(count):
        offset = HEADER_SIZE + index * RECORD_SIZE
        row = data[offset:offset + RECORD_SIZE]
        name = row[:NAME_SIZE].split(b"\0", 1)[0]
        metadata = row[NAME_SIZE:NAME_SIZE + METADATA_SIZE]
        description = row[NAME_SIZE + METADATA_SIZE:].split(b"\0", 1)[0]
        # The resource identifier starts at record-relative 0x34, after the
        # 20-byte price/stat block at 0x20..0x33.
        resource_id = metadata[20:30].split(b"\0", 1)[0].decode("ascii")
        records.append(ItemRecord(index, offset, resource_id, name, description, metadata))
    return records


def fixed_field(value: bytes, size: int, label: str) -> bytes:
    if b"\0" in value:
        raise ValueError(f"{label} contains NUL")
    if len(value) + 1 > size:
        raise ValueError(f"{label} is too long: {len(value) + 1}/{size} bytes including NUL")
    return value + bytes(size - len(value))


def patch(data: bytes, replacements: dict[int, tuple[bytes, bytes]]) -> tuple[bytes, list[dict]]:
    source = parse(data)
    output = bytearray(data)
    report = []
    for index, (name, description) in sorted(replacements.items()):
        if not 0 <= index < len(source):
            raise ValueError(f"item index out of range: {index}")
        row = source[index]
        name_field = fixed_field(name, NAME_SIZE, f"item {index} name")
        description_field = fixed_field(description, DESCRIPTION_SIZE, f"item {index} description")
        output[row.offset:row.offset + NAME_SIZE] = name_field
        desc_offset = row.offset + NAME_SIZE + METADATA_SIZE
        output[desc_offset:desc_offset + DESCRIPTION_SIZE] = description_field
        report.append({"index": index, "resource_id": row.resource_id,
                       "name_length": len(name), "description_length": len(description)})
    rebuilt = bytes(output)
    after = parse(rebuilt)
    for before, current in zip(source, after):
        if before.metadata != current.metadata:
            raise ValueError(f"item metadata changed: {before.index}")
        if before.index not in replacements:
            start = before.offset
            if data[start:start + RECORD_SIZE] != rebuilt[start:start + RECORD_SIZE]:
                raise ValueError(f"unselected item changed: {before.index}")
    return rebuilt, report
