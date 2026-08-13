#!/usr/bin/env python3
"""Inspect the Ys VI Korean font and decode its custom two-byte text codes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


class CodecError(ValueError):
    pass


# Glyphs whose patch-specific outlines are unique rather than byte-identical copies
# of another cmap glyph. Values were verified in a rendered atlas and against the
# corresponding PSP source context. Keeping them explicit makes the judgment auditable.
VERIFIED_VISIBLE_GLYPHS = {
    "96FB": "…",
    "9799": "─",
    "994A": "·",
    "8976": "굉",
    "9979": "!",
    "8968": "광",
    "99DA": "～",
    "999B": "?",
    "97CD": ",",
    "97D5": "《",
    "97D6": "》",
    "97CC": " ",
    "9786": "②",
    "998E": "2",
    "998C": "0",
    "97C9": "♪",
    "9984": "(",
    "9985": ")",
    "A4FD": "ㆍ",
    "998B": "/",
    "9991": "5",
    "99A3": "G",
    "99CB": "o",
    "99C8": "l",
    "99C0": "d",
    "97C5": "★",
    "9785": "①",
    "9787": "③",
}


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _i16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">h", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


@dataclass(frozen=True)
class SfntTable:
    tag: str
    offset: int
    length: int


class SfntFont:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if len(self.data) < 12:
            raise CodecError("font is shorter than its sfnt header")
        count = _u16(self.data, 4)
        self.tables: dict[str, SfntTable] = {}
        for index in range(count):
            offset = 12 + index * 16
            tag_raw, _checksum, table_offset, length = struct.unpack_from(">4sIII", self.data, offset)
            tag = tag_raw.decode("latin1")
            if table_offset + length > len(self.data):
                raise CodecError(f"font table {tag!r} exceeds file size")
            self.tables[tag] = SfntTable(tag, table_offset, length)

    def table_data(self, tag: str) -> bytes:
        try:
            table = self.tables[tag]
        except KeyError as exc:
            raise CodecError(f"font has no {tag!r} table") from exc
        return self.data[table.offset:table.offset + table.length]

    def glyph_count(self) -> int:
        return _u16(self.table_data("maxp"), 4)

    def cmap_records(self) -> list[tuple[int, int, int, bytes]]:
        cmap = self.table_data("cmap")
        count = _u16(cmap, 2)
        records = []
        for index in range(count):
            platform, encoding, offset = struct.unpack_from(">HHI", cmap, 4 + index * 8)
            if offset + 2 > len(cmap):
                raise CodecError("cmap subtable offset is out of range")
            records.append((platform, encoding, _u16(cmap, offset), cmap[offset:]))
        return records

    @staticmethod
    def _parse_format4(table: bytes) -> dict[int, int]:
        length = _u16(table, 2)
        table = table[:length]
        seg_count = _u16(table, 6) // 2
        end_base = 14
        start_base = end_base + seg_count * 2 + 2
        delta_base = start_base + seg_count * 2
        range_base = delta_base + seg_count * 2
        result: dict[int, int] = {}
        for segment in range(seg_count):
            end = _u16(table, end_base + segment * 2)
            start = _u16(table, start_base + segment * 2)
            delta = _i16(table, delta_base + segment * 2)
            range_offset_pos = range_base + segment * 2
            range_offset = _u16(table, range_offset_pos)
            if start == 0xFFFF and end == 0xFFFF:
                continue
            for codepoint in range(start, end + 1):
                if range_offset == 0:
                    glyph = (codepoint + delta) & 0xFFFF
                else:
                    glyph_pos = range_offset_pos + range_offset + (codepoint - start) * 2
                    if glyph_pos + 2 > len(table):
                        raise CodecError("cmap format 4 glyph offset is out of range")
                    glyph = _u16(table, glyph_pos)
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                if glyph:
                    result[codepoint] = glyph
        return result

    @staticmethod
    def _parse_format6(table: bytes) -> dict[int, int]:
        length, first, count = struct.unpack_from(">HHH", table, 2)
        if 10 + count * 2 > length:
            raise CodecError("invalid cmap format 6 length")
        return {first + index: _u16(table, 10 + index * 2) for index in range(count)}

    def cmaps(self) -> list[tuple[int, int, int, dict[int, int]]]:
        output = []
        for platform, encoding, format_number, table in self.cmap_records():
            if format_number == 4:
                mapping = self._parse_format4(table)
            elif format_number == 6:
                mapping = self._parse_format6(table)
            else:
                mapping = {}
            output.append((platform, encoding, format_number, mapping))
        return output

    def glyph_names(self) -> list[str | None]:
        post = self.table_data("post")
        if _u32(post, 0) != 0x00020000:
            raise CodecError("only post table format 2.0 is supported")
        count = _u16(post, 32)
        indices = [_u16(post, 34 + index * 2) for index in range(count)]
        custom_count = max(indices, default=257) - 257
        cursor = 34 + count * 2
        custom = []
        for _ in range(custom_count):
            if cursor >= len(post):
                raise CodecError("truncated post glyph name list")
            size = post[cursor]
            cursor += 1
            custom.append(post[cursor:cursor + size].decode("ascii", errors="replace"))
            cursor += size
        return [custom[value - 258] if value >= 258 and value - 258 < len(custom) else None for value in indices]

    def best_cmap(self) -> dict[int, int]:
        candidates = self.cmaps()
        for platform, encoding, _format, mapping in candidates:
            if platform == 3 and encoding == 1:
                return mapping
        for _platform, _encoding, _format, mapping in candidates:
            if mapping:
                return mapping
        raise CodecError("font contains no supported cmap")

    def glyph_data(self) -> list[bytes]:
        head = self.table_data("head")
        loca = self.table_data("loca")
        glyf = self.table_data("glyf")
        count = self.glyph_count()
        location_format = _i16(head, 50)
        if location_format == 0:
            if len(loca) < (count + 1) * 2:
                raise CodecError("short-format loca table is truncated")
            offsets = [_u16(loca, index * 2) * 2 for index in range(count + 1)]
        elif location_format == 1:
            if len(loca) < (count + 1) * 4:
                raise CodecError("long-format loca table is truncated")
            offsets = [_u32(loca, index * 4) for index in range(count + 1)]
        else:
            raise CodecError(f"unsupported indexToLocFormat: {location_format}")
        if offsets[-1] > len(glyf):
            raise CodecError("loca table exceeds glyf table")
        return [glyf[offsets[index]:offsets[index + 1]] for index in range(count)]


def load_code_map(path: Path) -> dict[bytes, str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    result: dict[bytes, str] = {}
    for row in document.get("mappings", []):
        code = bytes.fromhex(row["code_hex"])
        character = row["character"]
        if not code or len(character) != 1:
            raise CodecError("each mapping must contain one nonempty code and one character")
        if code in result and result[code] != character:
            raise CodecError(f"conflicting mapping for {code.hex().upper()}")
        result[code] = character
    return result


def decode_custom(data: bytes, mapping: dict[bytes, str]) -> tuple[str, list[str]]:
    output = []
    unresolved = []
    cursor = 0
    while cursor < len(data):
        value = data[cursor]
        if value < 0x80:
            output.append(chr(value))
            cursor += 1
            continue
        if cursor + 1 >= len(data):
            code = data[cursor:cursor + 1]
        else:
            code = data[cursor:cursor + 2]
        character = mapping.get(code)
        if character is None:
            label = code.hex().upper()
            unresolved.append(label)
            output.append(f"{{{label}}}")
        else:
            output.append(character)
        cursor += len(code)
    return "".join(output), unresolved


def derive_font_mapping(font_path: Path) -> dict:
    """Recover the patch's CP949-code-to-visible-Hangul substitutions by glyph identity."""
    font = SfntFont(font_path)
    cmap = font.best_cmap()
    glyphs = font.glyph_data()
    signatures = [hashlib.sha256(value).hexdigest().upper() if value else None for value in glyphs]

    hangul_by_signature: dict[str, list[str]] = {}
    for codepoint in range(0xAC00, 0xD7A4):
        glyph_id = cmap.get(codepoint)
        if glyph_id is None or glyph_id >= len(signatures):
            continue
        signature = signatures[glyph_id]
        if signature is not None:
            hangul_by_signature.setdefault(signature, []).append(chr(codepoint))

    mappings = []
    ambiguous = []
    seen_codes: set[bytes] = set()
    for lead in range(0x81, 0xFF):
        for trail in range(0x41, 0xFF):
            code = bytes((lead, trail))
            try:
                pseudo = code.decode("cp949")
            except UnicodeDecodeError:
                continue
            if len(pseudo) != 1 or code in seen_codes:
                continue
            seen_codes.add(code)
            glyph_id = cmap.get(ord(pseudo))
            if glyph_id is None or glyph_id >= len(signatures):
                continue
            signature = signatures[glyph_id]
            candidates = [character for character in hangul_by_signature.get(signature or "", []) if character != pseudo]
            if len(candidates) == 1:
                mappings.append({
                    "code_hex": code.hex().upper(),
                    "encoded_codepoint": f"U+{ord(pseudo):04X}",
                    "encoded_character": pseudo,
                    "character": candidates[0],
                    "glyph_id": glyph_id,
                    "evidence": "exact_glyf_sha256",
                    "confidence": "exact",
                })
            elif len(candidates) > 1:
                ambiguous.append({
                    "code_hex": code.hex().upper(),
                    "encoded_codepoint": f"U+{ord(pseudo):04X}",
                    "candidates": candidates,
                })
    mappings.sort(key=lambda row: row["code_hex"])
    existing = {row["code_hex"] for row in mappings}
    for code_hex, character in VERIFIED_VISIBLE_GLYPHS.items():
        if code_hex in existing:
            continue
        code = bytes.fromhex(code_hex)
        pseudo = code.decode("cp949")
        mappings.append({
            "code_hex": code_hex,
            "encoded_codepoint": f"U+{ord(pseudo):04X}",
            "encoded_character": pseudo,
            "character": character,
            "glyph_id": cmap.get(ord(pseudo)),
            "evidence": "rendered_atlas_and_psp_context",
            "confidence": "verified",
        })
    mappings.sort(key=lambda row: row["code_hex"])
    return {
        "schema_version": 1,
        "source_font": str(font_path).replace("\\", "/"),
        "method": "CP949 codepoint glyph matched to canonical Hangul glyph by exact glyf SHA-256",
        "source_font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest().upper(),
        "mapping_count": len(mappings),
        "ambiguous_count": len(ambiguous),
        "mappings": mappings,
        "ambiguous": ambiguous,
    }


def inspect_font(font_path: Path, codepoints: list[int]) -> dict:
    font = SfntFont(font_path)
    names = font.glyph_names()
    cmaps = []
    for platform, encoding, format_number, mapping in font.cmaps():
        rows = []
        for codepoint in codepoints:
            glyph = mapping.get(codepoint)
            rows.append({
                "codepoint": f"U+{codepoint:04X}",
                "glyph_id": glyph,
                "glyph_name": names[glyph] if glyph is not None and glyph < len(names) else None,
            })
        cmaps.append({
            "platform": platform,
            "encoding": encoding,
            "format": format_number,
            "mapping_count": len(mapping),
            "selected": rows,
        })
    return {"font": str(font_path), "glyph_count": font.glyph_count(), "cmap": cmaps}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect-font")
    inspect_parser.add_argument("--font", type=Path, required=True)
    inspect_parser.add_argument("--codepoint", action="append", default=[])
    decode_parser = subparsers.add_parser("decode")
    decode_parser.add_argument("--map", type=Path, required=True)
    decode_parser.add_argument("--hex", required=True)
    derive_parser = subparsers.add_parser("derive-map")
    derive_parser.add_argument("--font", type=Path, required=True)
    derive_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "inspect-font":
        codepoints = [int(value.removeprefix("U+").removeprefix("0x"), 16) for value in args.codepoint]
        result = inspect_font(args.font, codepoints)
    elif args.command == "decode":
        text, unresolved = decode_custom(bytes.fromhex(args.hex), load_code_map(args.map))
        result = {"text": text, "unresolved": unresolved}
    else:
        result = derive_font_mapping(args.font)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {
                "output": str(args.output),
                "mapping_count": result["mapping_count"],
                "ambiguous_count": result["ambiguous_count"],
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
