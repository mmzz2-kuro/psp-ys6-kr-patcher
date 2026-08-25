#!/usr/bin/env python3
"""Patch ULJM-05009 to keep PSP controller sampling in analog mode."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

EXPECTED_SHA256 = "EB20970858EC420FB1E068C38DFF5765CD3C99FC624266E2989DAC92E39108E5"
OLD_WORD, NEW_WORD = 0x00002021, 0x24040001
PATCH_ADDRESSES = (0x000E1318, 0x000E1A9C, 0x000E1C68, 0x000E1D68,
                   0x000E2A14, 0x000E3F84, 0x000E40B0, 0x000E4158)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def text_mapping(data: bytes) -> tuple[int, int, int]:
    if data[:4] != b"\x7fELF" or data[4:6] != b"\x01\x01": raise ValueError("ELF32 little-endian file required")
    shoff = struct.unpack_from("<I", data, 0x20)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x2E)
    headers = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize) for i in range(shnum)]
    shstr = headers[shstrndx]; names = data[shstr[4]:shstr[4] + shstr[5]]
    for header in headers:
        end = names.find(b"\0", header[0])
        if names[header[0]:end] == b".text": return header[3], header[4], header[5]
    raise ValueError(".text section not found")

def patch_bytes(original: bytes, *, require_original_sha: bool = False) -> tuple[bytes, dict[str, object]]:
    if require_original_sha and sha(original) != EXPECTED_SHA256: raise ValueError(f"unsupported decrypted EBOOT SHA-256: {sha(original)}")
    text_address, text_offset, text_size = text_mapping(original); output = bytearray(original); changes = []
    for address in PATCH_ADDRESSES:
        if not text_address <= address < text_address + text_size: raise ValueError(f"patch address outside .text: 0x{address:08X}")
        offset = text_offset + address - text_address; before = struct.unpack_from("<I", original, offset)[0]
        if before != OLD_WORD: raise ValueError(f"unexpected instruction at 0x{address:08X}: 0x{before:08X}")
        struct.pack_into("<I", output, offset, NEW_WORD)
        changes.append({"address": f"0x{address:08X}", "file_offset": offset, "before_word": f"0x{before:08X}", "after_word": f"0x{NEW_WORD:08X}"})
    changed = [i for i, (a, b) in enumerate(zip(original, output)) if a != b]
    expected = sorted(row["file_offset"] + byte for row in changes for byte in range(4) if original[row["file_offset"] + byte] != output[row["file_offset"] + byte])
    if changed != expected: raise ValueError("bytes changed outside the eight approved instructions")
    result = bytes(output)
    return result, {"input_size": len(original), "output_size": len(result), "input_sha256": sha(original), "output_sha256": sha(result), "instruction_change_count": len(changes), "changed_byte_count": len(changed), "changes": changes, "valid": True}

def patch(input_path: Path, output_path: Path) -> dict[str, object]:
    output, report = patch_bytes(input_path.read_bytes(), require_original_sha=True)
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_bytes(output)
    if output_path.read_bytes() != output: raise ValueError("output EBOOT verification failed")
    return {"input": str(input_path), "output": str(output_path), **report}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("input", type=Path); parser.add_argument("output", type=Path); parser.add_argument("--report", type=Path); args = parser.parse_args()
    report = patch(args.input, args.output)
    if args.report: args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())
