#!/usr/bin/env python3
"""Build the ULJM-05155 minimal Hangul font proof and optional test ISO."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_iso_multi_patch import Replacement, patch_atomic
except ModuleNotFoundError:
    try:
        from .iso9660_info import SECTOR_SIZE, find_record
        from .ys6_iso_multi_patch import Replacement, patch_atomic
    except ImportError:
        from iso9660_info import SECTOR_SIZE, find_record
        from ys6_iso_multi_patch import Replacement, patch_atomic


ISO_SHA256 = "C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9"
BOOT_SHA256 = "224F0AE02849521F688C438AFEA096E7081188832312E38B89B6A9D871976C5E"
EBOOT_SHA256 = "CC21DA799DA763A9AA7ADDD006C36A0ADD48C847EC158FB64CF8F9F4D1C9E902"
FONT_OFFSET = 0x15EB2A
FONT_COUNT = 1771
RECORD_SIZE = 30
GLYPH_WIDTH = 16
GLYPH_HEIGHT = 14
GLYPH_SIZE = 28
TEST_STRING_OFFSET = 0x147B58
TEST_SOURCE = "再開".encode("cp932")
TEST_TEXT = "한글"
SLOTS = ((0xE5E5, "한"), (0xE978, "글"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_iso_file(iso: Path, internal_path: str) -> bytes:
    record = find_record(iso, internal_path)
    with iso.open("rb") as handle:
        handle.seek(record.extent_lba * SECTOR_SIZE)
        data = handle.read(record.data_length)
    if len(data) != record.data_length:
        raise OSError(f"short ISO read: {internal_path}")
    return data


def render_glyph(character: str, font_path: Path, font_size: int = 14, threshold: int = 96) -> tuple[bytes, Image.Image]:
    font = ImageFont.truetype(str(font_path), font_size, index=0)
    bbox = font.getbbox(character)
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if width > GLYPH_WIDTH or height > GLYPH_HEIGHT:
        raise ValueError(f"glyph {character!r} is {width}x{height}, exceeds 16x14")
    x = 1 - bbox[0]
    if x + width > GLYPH_WIDTH: x = (GLYPH_WIDTH - width) // 2 - bbox[0]
    y = (GLYPH_HEIGHT - height) // 2 - bbox[1]
    gray = Image.new("L", (GLYPH_WIDTH, GLYPH_HEIGHT), 0)
    ImageDraw.Draw(gray).text((x, y), character, font=font, fill=255)
    mono = gray.point(lambda value: 255 if value >= threshold else 0)
    bitmap = bytearray()
    for row in range(GLYPH_HEIGHT):
        value = 0
        for column in range(GLYPH_WIDTH):
            if mono.getpixel((column, row)): value |= 1 << (15 - column)
        bitmap.extend(value.to_bytes(2, "big"))
    if not any(bitmap): raise ValueError(f"blank glyph: {character}")
    return bytes(bitmap), mono


def locate_slots(data: bytes) -> dict[int, int]:
    if data[FONT_OFFSET:FONT_OFFSET + 2] != b"\x40\x81": raise ValueError("font table signature mismatch")
    result: dict[int, int] = {}
    for index in range(FONT_COUNT):
        offset = FONT_OFFSET + index * RECORD_SIZE
        code = struct.unpack_from("<H", data, offset)[0]
        if code in dict(SLOTS):
            if code in result: raise ValueError(f"duplicate font code 0x{code:04X}")
            result[code] = offset
    if set(result) != {code for code, _character in SLOTS}: raise ValueError("test font slots not found")
    table_end = FONT_OFFSET + FONT_COUNT * RECORD_SIZE
    for code in result:
        encoded = code.to_bytes(2, "big")
        if data[:FONT_OFFSET].count(encoded) + data[table_end:].count(encoded):
            raise ValueError(f"font slot 0x{code:04X} is used outside the font table")
    return result


def build_proof(boot: bytes, font_path: Path) -> tuple[bytes, dict, Image.Image]:
    if sha(boot) != BOOT_SHA256: raise ValueError(f"SPECIAL VERSION BOOT.BIN SHA-256 mismatch: {sha(boot)}")
    if boot[TEST_STRING_OFFSET:TEST_STRING_OFFSET + len(TEST_SOURCE)] != TEST_SOURCE:
        raise ValueError("test source string mismatch")
    slots = locate_slots(boot); output = bytearray(boot); reports = []; previews = []
    replacement = bytearray()
    for code, character in SLOTS:
        bitmap, preview = render_glyph(character, font_path)
        record_offset = slots[code]; bitmap_offset = record_offset + 2
        before = boot[bitmap_offset:bitmap_offset + GLYPH_SIZE]
        output[bitmap_offset:bitmap_offset + GLYPH_SIZE] = bitmap
        replacement.extend(code.to_bytes(2, "big")); previews.append(preview)
        reports.append({"character": character, "game_code": f"0x{code:04X}", "font_index": (record_offset - FONT_OFFSET) // RECORD_SIZE,
                        "record_offset": f"0x{record_offset:X}", "bitmap_offset": f"0x{bitmap_offset:X}",
                        "original_bitmap_sha256": sha(before), "output_bitmap_sha256": sha(bitmap)})
    output[TEST_STRING_OFFSET:TEST_STRING_OFFSET + len(TEST_SOURCE)] = replacement
    changed = [index for index, (left, right) in enumerate(zip(boot, output)) if left != right]
    allowed = set(range(TEST_STRING_OFFSET, TEST_STRING_OFFSET + len(TEST_SOURCE)))
    for row in reports:
        start = int(row["bitmap_offset"], 0); allowed.update(range(start, start + GLYPH_SIZE))
    if any(index not in allowed for index in changed): raise ValueError("unexpected changed byte outside proof ranges")
    atlas = Image.new("L", (GLYPH_WIDTH * len(previews), GLYPH_HEIGHT), 0)
    for index, preview in enumerate(previews): atlas.paste(preview, (index * GLYPH_WIDTH, 0))
    result = bytes(output)
    report = {"valid": True, "profile": "ULJM-05155", "font_offset": f"0x{FONT_OFFSET:X}", "font_count": FONT_COUNT,
              "record_size": RECORD_SIZE, "glyph_width": GLYPH_WIDTH, "glyph_height": GLYPH_HEIGHT,
              "test_string_offset": f"0x{TEST_STRING_OFFSET:X}", "test_source": "再開", "test_translation": TEST_TEXT,
              "test_encoded_hex": replacement.hex().upper(), "input_size": len(boot), "output_size": len(result),
              "input_sha256": sha(boot), "output_sha256": sha(result), "changed_byte_count": len(changed),
              "changed_ranges": [{"start": f"0x{start:X}", "length": length} for start, length in contiguous_ranges(changed)],
              "glyphs": reports}
    return result, report, atlas


def contiguous_ranges(offsets: list[int]) -> list[tuple[int, int]]:
    if not offsets: return []
    result = []; start = previous = offsets[0]
    for offset in offsets[1:]:
        if offset != previous + 1:
            result.append((start, previous - start + 1)); start = offset
        previous = offset
    result.append((start, previous - start + 1)); return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path); parser.add_argument("work", type=Path); parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output-iso", type=Path); parser.add_argument("--overwrite", action="store_true"); args = parser.parse_args()
    if sha(args.iso.read_bytes()) != ISO_SHA256: raise ValueError("SPECIAL VERSION ISO SHA-256 mismatch")
    boot = read_iso_file(args.iso, "PSP_GAME/SYSDIR/BOOT.BIN"); eboot = read_iso_file(args.iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    if sha(eboot) != EBOOT_SHA256: raise ValueError("SPECIAL VERSION EBOOT.BIN SHA-256 mismatch")
    patched, report, atlas = build_proof(boot, args.font); args.work.mkdir(parents=True, exist_ok=True)
    boot_path = args.work / "BOOT-font-proof.bin"; eboot_path = args.work / "EBOOT-font-proof.bin"
    patched_eboot = patched + eboot[len(patched):]
    if len(patched_eboot) != len(eboot): raise ValueError("padded EBOOT size mismatch")
    boot_path.write_bytes(patched); eboot_path.write_bytes(patched_eboot)
    atlas.resize((atlas.width * 12, atlas.height * 12), Image.Resampling.NEAREST).save(args.work / "hangul-proof-atlas.png")
    report["original_eboot_sha256"] = sha(eboot); report["output_eboot_sha256"] = sha(patched_eboot)
    report["output_eboot_size"] = len(patched_eboot); report["plain_elf_eboot"] = True
    report["preserved_eboot_tail_size"] = len(eboot) - len(patched); report["iso"] = None
    if args.output_iso:
        replacements = [Replacement("PSP_GAME/SYSDIR/BOOT.BIN", boot_path, len(boot), sha(boot)),
                        Replacement("PSP_GAME/SYSDIR/EBOOT.BIN", eboot_path, len(eboot), sha(eboot))]
        result = patch_atomic(args.iso, args.output_iso, replacements, ISO_SHA256, args.overwrite)
        report["iso"] = {"path": str(args.output_iso), **result}
    (args.work / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
