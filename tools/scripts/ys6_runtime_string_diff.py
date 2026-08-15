#!/usr/bin/env python3
"""Search readable PPSSPP process memory for encoded system-message strings."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import struct
from ctypes import wintypes
from pathlib import Path


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("PartitionId", wintypes.WORD),
                ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]


def variants(texts: list[str]) -> list[tuple[str, str, bytes]]:
    result = []
    for text in dict.fromkeys(texts):
        for encoding in ("cp932", "utf-16le", "utf-16be", "utf-8"):
            result.append((text, encoding, text.encode(encoding)))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--text", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dump-matches", type=Path)
    parser.add_argument("--dump-region-base", type=lambda value: int(value, 0))
    parser.add_argument("--dump-region-size", type=lambda value: int(value, 0))
    args = parser.parse_args()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, args.pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "OpenProcess failed")
    if args.dump_region_base is not None:
        if args.dump_region_size is None or args.dump_matches is None:
            parser.error("--dump-region-base requires --dump-region-size and --dump-matches")
        buffer = ctypes.create_string_buffer(args.dump_region_size); actual = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(args.dump_region_base), buffer,
                                          args.dump_region_size, ctypes.byref(actual)):
            raise OSError(ctypes.get_last_error(), "ReadProcessMemory dump failed")
        args.dump_matches.parent.mkdir(parents=True, exist_ok=True)
        args.dump_matches.write_bytes(buffer.raw[:actual.value])
        if not args.text:
            kernel32.CloseHandle(handle)
            result = {"pid": args.pid, "dump_address": f"0x{args.dump_region_base:016X}",
                      "dump_size": actual.value, "output": str(args.dump_matches)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2)); return 0
    pats = variants(args.text); address = 0; regions = read_bytes = 0; hits = []
    info = MEMORY_BASIC_INFORMATION()
    max_address = (1 << (struct.calcsize("P") * 8)) - 1
    try:
        while address < max_address:
            queried = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info))
            if not queried: break
            base = int(info.BaseAddress or 0); size = int(info.RegionSize)
            readable = info.State == MEM_COMMIT and not (info.Protect & (PAGE_GUARD | PAGE_NOACCESS))
            if readable and 0 < size <= 512 * 1024 * 1024:
                buffer = ctypes.create_string_buffer(size); actual = ctypes.c_size_t()
                if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buffer, size, ctypes.byref(actual)):
                    data = buffer.raw[:actual.value]; regions += 1; read_bytes += len(data)
                    for text, encoding, pattern in pats:
                        cursor = 0
                        while True:
                            offset = data.find(pattern, cursor)
                            if offset < 0: break
                            start, end = max(0, offset - 64), min(len(data), offset + len(pattern) + 64)
                            hit = {"address": f"0x{base + offset:016X}", "region_base": f"0x{base:016X}",
                                   "region_size": size, "text": text, "encoding": encoding,
                                   "context_hex": data[start:end].hex().upper()}
                            hits.append(hit); cursor = offset + 1
                # Failure is expected for some changing or protected regions.
            next_address = base + size
            if next_address <= address: break
            address = next_address
    finally:
        kernel32.CloseHandle(handle)
    result = {"schema_version": 1, "pid": args.pid, "region_count": regions,
              "read_bytes": read_bytes, "hit_count": len(hits), "hits": hits}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("pid", "region_count", "read_bytes", "hit_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
