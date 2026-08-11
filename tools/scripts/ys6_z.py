#!/usr/bin/env python3
"""Inspect and decompress Ys VI PSP .z container files safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


HEADER_SIZE = 8


class Ys6ZError(Exception):
    """Raised when a file is not a valid supported Ys VI .z container."""


@dataclass
class ContainerInfo:
    path: str
    file_size: int
    header_tag_hex: str
    expected_crc32: str
    expected_size: int
    stream_offset: int
    zlib_header_hex: str
    actual_size: int | None = None
    actual_crc32: str | None = None
    stream_eof: bool | None = None
    trailing_size: int | None = None
    valid: bool = False
    error: str | None = None


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def read_container(path: Path) -> tuple[bytes, ContainerInfo]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise Ys6ZError(f"파일을 읽을 수 없습니다: {exc}") from exc

    if len(data) < HEADER_SIZE + 2:
        raise Ys6ZError(f"파일이 너무 작습니다: {len(data)}바이트")

    expected_size = struct.unpack_from("<I", data, 4)[0]
    info = ContainerInfo(
        path=str(path),
        file_size=len(data),
        header_tag_hex=data[:4].hex().upper(),
        expected_crc32=f"{struct.unpack_from('<I', data, 0)[0]:08X}",
        expected_size=expected_size,
        stream_offset=HEADER_SIZE,
        zlib_header_hex=data[HEADER_SIZE : HEADER_SIZE + 2].hex().upper(),
    )
    return data, info


def inspect_container(path: Path, include_data: bool = False) -> tuple[ContainerInfo, bytes | None]:
    try:
        data, info = read_container(path)
        decoder = zlib.decompressobj()
        output = decoder.decompress(data[HEADER_SIZE:])
        output += decoder.flush()
        info.actual_size = len(output)
        info.actual_crc32 = f"{zlib.crc32(output) & 0xFFFFFFFF:08X}"
        info.stream_eof = decoder.eof
        info.trailing_size = len(decoder.unused_data)

        if not decoder.eof:
            raise Ys6ZError("zlib 스트림이 정상적으로 종료되지 않았습니다")
        if len(output) != info.expected_size:
            raise Ys6ZError(
                f"비압축 크기 불일치: 헤더={info.expected_size}, 실제={len(output)}"
            )
        if info.actual_crc32 != info.expected_crc32:
            raise Ys6ZError(
                f"CRC32 불일치: 헤더={info.expected_crc32}, 실제={info.actual_crc32}"
            )

        info.valid = True
        return info, output if include_data else None
    except (OSError, zlib.error, Ys6ZError) as exc:
        if "info" not in locals():
            info = ContainerInfo(
                path=str(path),
                file_size=path.stat().st_size if path.exists() else 0,
                header_tag_hex="",
                expected_crc32="",
                expected_size=0,
                stream_offset=HEADER_SIZE,
                zlib_header_hex="",
            )
        info.error = str(exc)
        return info, None


def build_container(payload: bytes, level: int = 9) -> bytes:
    if not 0 <= level <= 9:
        raise Ys6ZError(f"압축 레벨은 0~9여야 합니다: {level}")
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    header = struct.pack("<II", checksum, len(payload))
    return header + zlib.compress(payload, level=level)


def verify_container_bytes(data: bytes) -> tuple[bool, bytes | None, str | None]:
    if len(data) < HEADER_SIZE + 2:
        return False, None, f"파일이 너무 작습니다: {len(data)}바이트"
    expected_crc32, expected_size = struct.unpack_from("<II", data, 0)
    try:
        decoder = zlib.decompressobj()
        payload = decoder.decompress(data[HEADER_SIZE:]) + decoder.flush()
    except zlib.error as exc:
        return False, None, f"zlib 해제 실패: {exc}"
    if not decoder.eof:
        return False, None, "zlib 스트림이 정상적으로 종료되지 않았습니다"
    if decoder.unused_data:
        return False, None, f"zlib 스트림 뒤에 {len(decoder.unused_data)}바이트가 남았습니다"
    if len(payload) != expected_size:
        return False, None, f"비압축 크기 불일치: 헤더={expected_size}, 실제={len(payload)}"
    actual_crc32 = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_crc32 != expected_crc32:
        return False, None, f"CRC32 불일치: 헤더={expected_crc32:08X}, 실제={actual_crc32:08X}"
    return True, payload, None


def first_difference(left: bytes, right: bytes) -> int | None:
    for index, (left_byte, right_byte) in enumerate(zip(left, right)):
        if left_byte != right_byte:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return None


def find_containers(root: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*.z" if recursive else "*.z"
    yield from sorted(path for path in root.glob(pattern) if path.is_file())


def emit(payload: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    else:
        print(payload)


def command_info(args: argparse.Namespace) -> int:
    info, _ = inspect_container(args.input)
    emit(asdict(info), args.json)
    return 0 if info.valid else 1


def command_decompress(args: argparse.Namespace) -> int:
    info, output = inspect_container(args.input, include_data=True)
    if not info.valid or output is None:
        emit(asdict(info), args.json)
        return 1

    destination: Path = args.output
    if destination.exists() and not args.overwrite:
        print(f"출력 파일이 이미 존재합니다: {destination}", file=sys.stderr)
        return 2

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(output)
    except OSError as exc:
        print(f"출력 파일을 쓸 수 없습니다: {exc}", file=sys.stderr)
        return 2

    result = asdict(info)
    result["output"] = str(destination)
    emit(result, args.json)
    return 0


def command_scan(args: argparse.Namespace) -> int:
    records = []
    valid_count = 0
    invalid_count = 0
    for path in find_containers(args.input, args.recursive):
        info, _ = inspect_container(path)
        records.append(asdict(info))
        if info.valid:
            valid_count += 1
        else:
            invalid_count += 1

    result = {
        "root": str(args.input),
        "total": len(records),
        "valid": valid_count,
        "invalid": invalid_count,
        "files": records,
    }
    if args.json:
        emit(result, True)
    else:
        emit({key: value for key, value in result.items() if key != "files"}, False)
        for record in records:
            status = "OK" if record["valid"] else "ERROR"
            suffix = "" if record["valid"] else f" - {record['error']}"
            print(f"[{status}] {record['path']}{suffix}")
    return 1 if invalid_count else 0


def command_compress(args: argparse.Namespace) -> int:
    try:
        payload = args.input.read_bytes()
        container = build_container(payload, args.level)
    except (OSError, Ys6ZError) as exc:
        print(f"압축 입력을 처리할 수 없습니다: {exc}", file=sys.stderr)
        return 1
    if args.output.exists() and not args.overwrite:
        print(f"출력 파일이 이미 존재합니다: {args.output}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(container)
    valid, unpacked, error = verify_container_bytes(container)
    result = {
        "input": str(args.input),
        "output": str(args.output),
        "level": args.level,
        "payload_size": len(payload),
        "container_size": len(container),
        "payload_crc32": f"{zlib.crc32(payload) & 0xFFFFFFFF:08X}",
        "container_sha256": hashlib.sha256(container).hexdigest().upper(),
        "zlib_header_hex": container[HEADER_SIZE : HEADER_SIZE + 2].hex().upper(),
        "valid": valid,
        "payload_identical": unpacked == payload,
        "error": error,
    }
    emit(result, args.json)
    return 0 if valid and unpacked == payload else 1


def command_roundtrip(args: argparse.Namespace) -> int:
    try:
        original = args.input.read_bytes()
    except OSError as exc:
        print(f"입력 파일을 읽을 수 없습니다: {exc}", file=sys.stderr)
        return 1
    original_valid, payload, original_error = verify_container_bytes(original)
    if not original_valid or payload is None:
        result = {"path": str(args.input), "valid": False, "error": original_error}
        emit(result, args.json)
        return 1
    try:
        rebuilt = build_container(payload, args.level)
    except Ys6ZError as exc:
        emit({"path": str(args.input), "valid": False, "error": str(exc)}, args.json)
        return 1
    rebuilt_valid, rebuilt_payload, rebuilt_error = verify_container_bytes(rebuilt)
    difference = first_difference(original, rebuilt)
    result = {
        "path": str(args.input),
        "output": None if args.verify_only or args.output is None else str(args.output),
        "verify_only": args.verify_only,
        "level": args.level,
        "original_size": len(original),
        "rebuilt_size": len(rebuilt),
        "size_delta": len(rebuilt) - len(original),
        "original_sha256": hashlib.sha256(original).hexdigest().upper(),
        "rebuilt_sha256": hashlib.sha256(rebuilt).hexdigest().upper(),
        "original_zlib_header_hex": original[HEADER_SIZE : HEADER_SIZE + 2].hex().upper(),
        "rebuilt_zlib_header_hex": rebuilt[HEADER_SIZE : HEADER_SIZE + 2].hex().upper(),
        "first_difference_offset": difference,
        "container_identical": difference is None,
        "payload_identical": rebuilt_payload == payload,
        "rebuilt_valid": rebuilt_valid,
        "error": rebuilt_error,
    }
    if not args.verify_only:
        if args.output is None:
            print("출력 경로가 필요합니다. 파일을 남기지 않으려면 --verify-only를 사용하세요.", file=sys.stderr)
            return 2
        if args.output.exists() and not args.overwrite:
            print(f"출력 파일이 이미 존재합니다: {args.output}", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rebuilt)
    emit(result, args.json)
    return 0 if rebuilt_valid and rebuilt_payload == payload else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ys VI PSP의 8바이트 헤더 + zlib 형식 .z 파일 분석 도구"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("info", help="컨테이너 헤더와 무결성을 확인합니다")
    info_parser.add_argument("input", type=Path)
    info_parser.add_argument("--json", action="store_true", help="UTF-8 JSON으로 출력합니다")
    info_parser.set_defaults(func=command_info)

    decompress_parser = subparsers.add_parser("decompress", help="단일 파일을 안전하게 해제합니다")
    decompress_parser.add_argument("input", type=Path)
    decompress_parser.add_argument("output", type=Path)
    decompress_parser.add_argument("--overwrite", action="store_true")
    decompress_parser.add_argument("--json", action="store_true", help="UTF-8 JSON으로 출력합니다")
    decompress_parser.set_defaults(func=command_decompress)

    scan_parser = subparsers.add_parser("scan", help="디렉터리의 .z 파일을 검사합니다")
    scan_parser.add_argument("input", type=Path)
    scan_parser.add_argument("--recursive", action="store_true")
    scan_parser.add_argument("--json", action="store_true", help="UTF-8 JSON으로 출력합니다")
    scan_parser.set_defaults(func=command_scan)

    compress_parser = subparsers.add_parser("compress", help="비압축 파일을 Ys VI .z로 압축합니다")
    compress_parser.add_argument("input", type=Path)
    compress_parser.add_argument("output", type=Path)
    compress_parser.add_argument("--level", type=int, choices=range(10), default=9)
    compress_parser.add_argument("--overwrite", action="store_true")
    compress_parser.add_argument("--json", action="store_true")
    compress_parser.set_defaults(func=command_compress)

    roundtrip_parser = subparsers.add_parser(
        "roundtrip", help="원본 .z를 해제·재압축하고 컨테이너와 payload를 비교합니다"
    )
    roundtrip_parser.add_argument("input", type=Path)
    roundtrip_parser.add_argument("output", type=Path, nargs="?")
    roundtrip_parser.add_argument("--level", type=int, choices=range(10), default=9)
    roundtrip_parser.add_argument("--verify-only", action="store_true")
    roundtrip_parser.add_argument("--overwrite", action="store_true")
    roundtrip_parser.add_argument("--json", action="store_true")
    roundtrip_parser.set_defaults(func=command_roundtrip)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
