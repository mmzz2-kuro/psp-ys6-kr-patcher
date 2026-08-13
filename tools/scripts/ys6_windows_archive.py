#!/usr/bin/env python3
"""Read and safely extract Falcom NNI/NA archives used by Ys VI Windows."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator


class ArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    index: int
    name: str
    name_hash: int
    offset: int
    packed_size: int
    compressed: bool


@dataclass(frozen=True)
class ExtractedEntry:
    entry: ArchiveEntry
    data: bytes
    expected_crc32: int | None
    actual_crc32: int | None
    expected_size: int | None


def _decode_index(data: bytes) -> bytes:
    key = 0x7C53F961
    output = bytearray()
    for value in data:
        key = (key * 0x3D09) & 0xFFFFFFFF
        output.append((value - (key >> 16)) & 0xFF)
    return bytes(output)


def filename_hash(name: bytes) -> int:
    return sum((value - 32) * (1 << ((index % 5) * 5)) for index, value in enumerate(name)) % 0xFFF1


def read_index(path: Path, *, verify_hashes: bool = True) -> list[ArchiveEntry]:
    data = path.read_bytes()
    if len(data) < 16:
        raise ArchiveError("NNI file is shorter than its header")
    magic, count, names_size, flags = struct.unpack_from("<4sIII", data)
    if magic != b"NNI\0":
        raise ArchiveError(f"invalid NNI magic: {magic!r}")
    if flags & 1:
        raise ArchiveError("incrementally linked NNI archives are unsupported")
    toc_end = 16 + count * 16
    names_end = toc_end + names_size
    if names_end != len(data):
        raise ArchiveError(f"invalid NNI regions: expected {names_end} bytes, got {len(data)}")
    toc = _decode_index(data[16:toc_end])
    names = _decode_index(data[toc_end:names_end])
    entries: list[ArchiveEntry] = []
    for index, (stored_hash, size, offset, name_offset) in enumerate(struct.iter_unpack("<IIII", toc)):
        if name_offset >= len(names):
            raise ArchiveError(f"entry {index}: name offset is out of range")
        terminator = names.find(b"\0", name_offset)
        if terminator < 0:
            raise ArchiveError(f"entry {index}: unterminated name")
        raw_name = names[name_offset:terminator]
        if verify_hashes and filename_hash(raw_name) != stored_hash:
            raise ArchiveError(f"entry {index}: filename hash mismatch")
        try:
            name = raw_name.decode("cp932").replace("\\", "/").lower()
        except UnicodeDecodeError as exc:
            raise ArchiveError(f"entry {index}: invalid CP932 filename") from exc
        entries.append(ArchiveEntry(index, name, stored_hash, offset, size, name.endswith(".z")))
    return entries


def _safe_relative_name(name: str) -> PurePosixPath:
    value = PurePosixPath(name[:-2] if name.endswith(".z") else name)
    if value.is_absolute() or not value.parts or any(part in ("", ".", "..") for part in value.parts):
        raise ArchiveError(f"unsafe archive path: {name!r}")
    if ":" in value.parts[0]:
        raise ArchiveError(f"unsafe archive path: {name!r}")
    return value


def read_entry(archive_path: Path, entry: ArchiveEntry, *, verify: bool = True) -> ExtractedEntry:
    with archive_path.open("rb") as stream:
        stream.seek(0, 2)
        archive_size = stream.tell()
        if entry.offset + entry.packed_size > archive_size:
            raise ArchiveError(f"entry {entry.index}: payload exceeds NA size")
        stream.seek(entry.offset)
        packed = stream.read(entry.packed_size)
    if len(packed) != entry.packed_size:
        raise ArchiveError(f"entry {entry.index}: short payload read")
    if not entry.compressed:
        return ExtractedEntry(entry, packed, None, None, None)
    if len(packed) < 8:
        raise ArchiveError(f"entry {entry.index}: compressed payload has no header")
    expected_crc32, expected_size = struct.unpack_from("<II", packed)
    try:
        data = zlib.decompress(packed[8:])
    except zlib.error as exc:
        raise ArchiveError(f"entry {entry.index}: zlib decompression failed") from exc
    actual_crc32 = zlib.crc32(data) & 0xFFFFFFFF
    if verify and len(data) != expected_size:
        raise ArchiveError(f"entry {entry.index}: size mismatch ({len(data)} != {expected_size})")
    if verify and actual_crc32 != expected_crc32:
        raise ArchiveError(f"entry {entry.index}: CRC32 mismatch")
    return ExtractedEntry(entry, data, expected_crc32, actual_crc32, expected_size)


def iter_selected(entries: list[ArchiveEntry], pattern: str | None) -> Iterator[ArchiveEntry]:
    normalized = pattern.lower().replace("\\", "/") if pattern else None
    for entry in entries:
        if normalized is None or PurePosixPath(entry.name).match(normalized):
            if (entry.offset, entry.packed_size) != (0, 0):
                yield entry


def extract(ni_path: Path, na_path: Path, output_dir: Path, *, pattern: str | None = None) -> dict:
    entries = read_index(ni_path)
    output_root = output_dir.resolve()
    rows = []
    for entry in iter_selected(entries, pattern):
        relative = _safe_relative_name(entry.name)
        destination = (output_root / Path(*relative.parts)).resolve()
        if output_root != destination and output_root not in destination.parents:
            raise ArchiveError(f"entry {entry.index}: output escaped destination root")
        extracted = read_entry(na_path, entry)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(extracted.data)
        rows.append({
            **asdict(entry),
            "output_path": relative.as_posix(),
            "unpacked_size": len(extracted.data),
            "crc32": f"{extracted.actual_crc32:08X}" if extracted.actual_crc32 is not None else None,
        })
    return {"entry_count": len(entries), "extracted_count": len(rows), "files": rows}


def verify_archive(ni_path: Path, na_path: Path) -> dict:
    entries = read_index(ni_path)
    verified = 0
    compressed = 0
    blank = 0
    for entry in entries:
        if (entry.offset, entry.packed_size) == (0, 0):
            blank += 1
            continue
        read_entry(na_path, entry, verify=True)
        verified += 1
        compressed += int(entry.compressed)
    return {
        "entry_count": len(entries),
        "verified_payload_count": verified,
        "verified_compressed_count": compressed,
        "blank_entry_count": blank,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ni", type=Path, required=True, help="data_us.ni path")
    parser.add_argument("--na", type=Path, help="data_us.na path; defaults beside --ni")
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list", help="list archive entries as JSON")
    listing.add_argument("--pattern", help="optional pathlib-style glob")
    extracting = subparsers.add_parser("extract", help="extract and verify selected entries")
    extracting.add_argument("--output", type=Path, required=True)
    extracting.add_argument("--pattern", help="optional pathlib-style glob")
    subparsers.add_parser("verify", help="verify every indexed payload without extracting")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ni_path = args.ni.resolve()
    na_path = (args.na or ni_path.with_suffix(".na")).resolve()
    if args.command == "list":
        entries = [asdict(entry) for entry in iter_selected(read_index(ni_path), args.pattern)]
        result = {"entry_count": len(read_index(ni_path)), "selected_count": len(entries), "files": entries}
    elif args.command == "extract":
        result = extract(ni_path, na_path, args.output, pattern=args.pattern)
    else:
        result = verify_archive(ni_path, na_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
