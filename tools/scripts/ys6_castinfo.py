#!/usr/bin/env python3
"""Inspect and safely patch fixed-width names in Ys VI castinfo.dat."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IDENTIFIER_PATTERN = re.compile(rb"CAST_[A-Z][0-9]{3}\x00")
IDENTIFIER_SIZE = 16
NAME_SIZE = 32


@dataclass(frozen=True)
class CastRecord:
    identifier: str
    identifier_offset: int
    name_offset: int
    name_raw_hex: str
    name_cp932: str


def parse_records(data: bytes) -> list[CastRecord]:
    records = []
    for match in IDENTIFIER_PATTERN.finditer(data):
        identifier_offset = match.start()
        name_offset = identifier_offset + IDENTIFIER_SIZE
        if name_offset + NAME_SIZE > len(data):
            raise ValueError(f"name field exceeds file: {identifier_offset:#x}")
        field = data[name_offset:name_offset + NAME_SIZE]
        raw = field.split(b"\x00", 1)[0]
        try:
            name = raw.decode("cp932")
        except UnicodeDecodeError:
            name = ""
        records.append(CastRecord(match.group()[:-1].decode("ascii"), identifier_offset, name_offset, field.hex().upper(), name))
    if not records:
        raise ValueError("cast records not found")
    return records


def encode_game_name(name: str, mappings: list[dict]) -> bytes:
    codes = {row["character"]: int(row["game_code"], 0) for row in mappings}
    output = bytearray()
    for character in name:
        if character in codes:
            output.extend(codes[character].to_bytes(2, "big"))
        else:
            output.extend(character.encode("cp932"))
    if len(output) >= NAME_SIZE:
        raise ValueError(f"encoded name is too long: {len(output)}")
    return bytes(output)


def patch_name(data: bytes, identifier: str, encoded_name: bytes, expected_name: str | None = None) -> tuple[bytes, dict]:
    matches = [record for record in parse_records(data) if record.identifier == identifier]
    if len(matches) != 1:
        raise ValueError(f"cast identifier is not unique: {identifier} count={len(matches)}")
    record = matches[0]
    if expected_name is not None and record.name_cp932 != expected_name:
        raise ValueError(f"cast name mismatch: expected={expected_name!r}, actual={record.name_cp932!r}")
    replacement = encoded_name + b"\x00" * (NAME_SIZE - len(encoded_name))
    patched = bytearray(data); patched[record.name_offset:record.name_offset + NAME_SIZE] = replacement
    differences = [index for index, (left, right) in enumerate(zip(data, patched)) if left != right]
    if any(not record.name_offset <= index < record.name_offset + NAME_SIZE for index in differences):
        raise ValueError("change outside cast name field")
    return bytes(patched), {**asdict(record), "encoded_name_hex": encoded_name.hex().upper(), "changed_byte_count": len(differences), "input_sha256": hashlib.sha256(data).hexdigest().upper(), "output_sha256": hashlib.sha256(patched).hexdigest().upper(), "size": len(data)}


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect"); inspect.add_argument("input", type=Path)
    patch = sub.add_parser("patch"); patch.add_argument("input", type=Path); patch.add_argument("mapping", type=Path); patch.add_argument("identifier"); patch.add_argument("name"); patch.add_argument("output", type=Path); patch.add_argument("--expected-name"); patch.add_argument("--report", type=Path); patch.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = args.input.read_bytes()
        if args.command == "inspect":
            result = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest().upper(), "records": [asdict(record) for record in parse_records(data)]}
        else:
            if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
            mappings = json.loads(args.mapping.read_text(encoding="utf-8-sig"))["mappings"]
            patched, result = patch_name(data, args.identifier, encode_game_name(args.name, mappings), args.expected_name)
            args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(patched)
            if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (OSError, KeyError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"castinfo 처리 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
