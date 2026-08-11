#!/usr/bin/env python3
"""Read-only inspector and string dumper for Ys VI PSP XSR/XSO files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


MAGIC = b"XSR\x00"
HEADER_SIZE = 0x24
TOKEN_PATTERN = re.compile(r"\\(?:x[0-9A-Fa-f]+|[A-Za-z]+|[0-9]+)")
MARKUP_PATTERN = re.compile(r"<[^<>]+>")


class XsoError(Exception):
    """Raised for unsupported or structurally invalid XSR files."""


@dataclass
class StringEntry:
    index: int
    relative_offset: int
    file_offset: int
    byte_length: int
    storage_length: int
    padding_length: int
    raw_hex: str
    text: str
    tokens: list[str]
    markup: list[str]


@dataclass
class CodeCommand:
    index: int
    file_offset: int
    opcode: str
    argument_count: int
    arguments: list[int]
    possible_string_arguments: list[int]


@dataclass
class XsoInfo:
    path: str
    file_size: int
    sha256: str
    magic: str
    header_unknown_hex: str
    code_word_count: int
    string_count: int
    code_offset: int
    offset_table_offset: int
    string_pool_offset: int
    terminal_word_hex: str
    valid: bool
    error: str | None = None


@dataclass
class ParsedXso:
    info: XsoInfo
    strings: list[StringEntry]
    commands: list[CodeCommand]


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _invalid_info(path: Path, file_size: int, error: str) -> XsoInfo:
    return XsoInfo(
        path=str(path),
        file_size=file_size,
        sha256="",
        magic="",
        header_unknown_hex="",
        code_word_count=0,
        string_count=0,
        code_offset=HEADER_SIZE,
        offset_table_offset=0,
        string_pool_offset=0,
        terminal_word_hex="",
        valid=False,
        error=error,
    )


def parse_xso(path: Path) -> ParsedXso:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise XsoError(f"파일을 읽을 수 없습니다: {exc}") from exc

    if len(data) < HEADER_SIZE:
        raise XsoError(f"XSR 헤더보다 파일이 작습니다: {len(data)}바이트")
    if data[:4] != MAGIC:
        raise XsoError(f"XSR 매직이 아닙니다: {data[:4].hex().upper()}")

    code_word_count, string_count = struct.unpack_from("<II", data, 0x1C)
    offset_table_offset = HEADER_SIZE + code_word_count * 4
    string_pool_offset = offset_table_offset + string_count * 4
    if offset_table_offset > len(data):
        raise XsoError("명령 워드 수가 파일 범위를 벗어납니다")
    if string_pool_offset > len(data):
        raise XsoError("문자열 오프셋 테이블이 파일 범위를 벗어납니다")

    offsets = [
        struct.unpack_from("<I", data, offset_table_offset + index * 4)[0]
        for index in range(string_count)
    ]
    if offsets and offsets[0] != 0:
        raise XsoError(f"첫 문자열 상대 오프셋이 0이 아닙니다: {offsets[0]}")
    if any(current >= following for current, following in zip(offsets, offsets[1:])):
        raise XsoError("문자열 상대 오프셋이 엄격한 오름차순이 아닙니다")

    pool_size = len(data) - string_pool_offset
    if any(offset >= pool_size for offset in offsets):
        raise XsoError("문자열 상대 오프셋이 문자열 풀 범위를 벗어납니다")

    entries: list[StringEntry] = []
    boundaries = offsets[1:] + [pool_size]
    for index, (start, end) in enumerate(zip(offsets, boundaries)):
        stored = data[string_pool_offset + start : string_pool_offset + end]
        terminator = stored.find(b"\x00")
        if terminator < 0:
            raise XsoError(f"문자열 {index}에 NUL 종료자가 없습니다")
        raw = stored[:terminator]
        padding = stored[terminator + 1 :]
        if any(padding):
            raise XsoError(f"문자열 {index}의 NUL 종료 뒤에 0이 아닌 데이터가 있습니다")
        try:
            text = raw.decode("cp932")
        except UnicodeDecodeError as exc:
            raise XsoError(f"문자열 {index} CP932 디코딩 실패: {exc}") from exc
        if text.encode("cp932") != raw:
            raise XsoError(f"문자열 {index} CP932 왕복 불일치")

        entries.append(
            StringEntry(
                index=index,
                relative_offset=start,
                file_offset=string_pool_offset + start,
                byte_length=len(raw),
                storage_length=len(stored),
                padding_length=len(padding),
                raw_hex=raw.hex().upper(),
                text=text,
                tokens=TOKEN_PATTERN.findall(text),
                markup=MARKUP_PATTERN.findall(text),
            )
        )

    commands: list[CodeCommand] = []
    cursor = HEADER_SIZE
    command_index = 0
    while cursor < offset_table_offset:
        word = data[cursor : cursor + 4]
        if len(word) != 4:
            raise XsoError(f"명령 {command_index} 워드가 잘렸습니다")
        argument_count = word[0]
        command_size = 4 * (1 + argument_count)
        if cursor + command_size > offset_table_offset:
            raise XsoError(
                f"명령 {command_index}가 명령 영역을 벗어납니다: argc={argument_count}"
            )
        arguments = [
            struct.unpack_from("<I", data, cursor + 4 + argument_index * 4)[0]
            for argument_index in range(argument_count)
        ]
        commands.append(
            CodeCommand(
                index=command_index,
                file_offset=cursor,
                opcode=word[1:4].hex().upper(),
                argument_count=argument_count,
                arguments=arguments,
                possible_string_arguments=[
                    index for index, value in enumerate(arguments) if value < string_count
                ],
            )
        )
        cursor += command_size
        command_index += 1
    if cursor != offset_table_offset:
        raise XsoError("명령 스트림 경계가 오프셋 테이블과 일치하지 않습니다")

    terminal_word = data[offset_table_offset - 4 : offset_table_offset]
    info = XsoInfo(
        path=str(path),
        file_size=len(data),
        sha256=hashlib.sha256(data).hexdigest().upper(),
        magic="XSR\\0",
        header_unknown_hex=data[4:0x1C].hex().upper(),
        code_word_count=code_word_count,
        string_count=string_count,
        code_offset=HEADER_SIZE,
        offset_table_offset=offset_table_offset,
        string_pool_offset=string_pool_offset,
        terminal_word_hex=terminal_word.hex().upper(),
        valid=True,
    )
    return ParsedXso(info=info, strings=entries, commands=commands)


def safe_parse(path: Path) -> ParsedXso:
    try:
        return parse_xso(path)
    except XsoError as exc:
        size = path.stat().st_size if path.exists() else 0
        return ParsedXso(info=_invalid_info(path, size, str(exc)), strings=[], commands=[])


def find_xso_files(root: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*.xso" if recursive else "*.xso"
    yield from sorted(path for path in root.glob(pattern) if path.is_file())


def rebuild_xso(path: Path) -> tuple[ParsedXso, bytes]:
    """Rebuild an XSR using parsed raw strings while preserving non-string bytes."""
    parsed = parse_xso(path)
    original = path.read_bytes()
    prefix = original[: parsed.info.offset_table_offset]
    offsets: list[int] = []
    pool = bytearray()
    for entry in parsed.strings:
        offsets.append(len(pool))
        pool.extend(bytes.fromhex(entry.raw_hex))
        pool.append(0)
        pool.extend(b"\x00" * entry.padding_length)
    table = b"".join(struct.pack("<I", offset) for offset in offsets)
    rebuilt = prefix + table + bytes(pool)
    return parsed, rebuilt


def first_difference(left: bytes, right: bytes) -> int | None:
    for index, (left_byte, right_byte) in enumerate(zip(left, right)):
        if left_byte != right_byte:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return None


def write_json(payload: object, output: Path | None, overwrite: bool) -> int:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
        return 0
    if output.exists() and not overwrite:
        print(f"출력 파일이 이미 존재합니다: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


def command_info(args: argparse.Namespace) -> int:
    parsed = safe_parse(args.input)
    payload = asdict(parsed.info)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0 if parsed.info.valid else 1


def command_dump(args: argparse.Namespace) -> int:
    parsed = safe_parse(args.input)
    payload = {
        "info": asdict(parsed.info),
        "strings": [asdict(entry) for entry in parsed.strings],
    }
    result = write_json(payload, args.output, args.overwrite)
    if result:
        return result
    return 0 if parsed.info.valid else 1


def command_scan(args: argparse.Namespace) -> int:
    records = []
    token_counts: Counter[str] = Counter()
    markup_counts: Counter[str] = Counter()
    string_total = 0
    valid_count = 0
    invalid_count = 0
    for path in find_xso_files(args.input, args.recursive):
        parsed = safe_parse(path)
        records.append(asdict(parsed.info))
        if parsed.info.valid:
            valid_count += 1
            string_total += len(parsed.strings)
            token_counts.update(token for entry in parsed.strings for token in entry.tokens)
            markup_counts.update(markup for entry in parsed.strings for markup in entry.markup)
        else:
            invalid_count += 1

    payload = {
        "root": str(args.input),
        "file_count": len(records),
        "valid": valid_count,
        "invalid": invalid_count,
        "string_count": string_total,
        "token_counts": dict(sorted(token_counts.items())),
        "markup_counts": dict(sorted(markup_counts.items())),
        "files": records,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key in (
            "root",
            "file_count",
            "valid",
            "invalid",
            "string_count",
            "token_counts",
            "markup_counts",
        ):
            print(f"{key}: {payload[key]}")
        for record in records:
            status = "OK" if record["valid"] else "ERROR"
            suffix = "" if record["valid"] else f" - {record['error']}"
            print(f"[{status}] {record['path']}{suffix}")
    return 1 if invalid_count else 0


def command_code_stats(args: argparse.Namespace) -> int:
    parsed = safe_parse(args.input)
    opcode_counts: Counter[str] = Counter(command.opcode for command in parsed.commands)
    candidate_counts: Counter[str] = Counter()
    for command in parsed.commands:
        for argument_index in command.possible_string_arguments:
            key = f"{command.opcode}:arg{argument_index}"
            candidate_counts[key] += 1
    payload = {
        "info": asdict(parsed.info),
        "command_count": len(parsed.commands),
        "opcode_counts": dict(sorted(opcode_counts.items())),
        "possible_string_reference_counts": dict(sorted(candidate_counts.items())),
        "commands": [asdict(command) for command in parsed.commands] if args.include_commands else [],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if parsed.info.valid else 1


def command_roundtrip(args: argparse.Namespace) -> int:
    try:
        parsed, rebuilt = rebuild_xso(args.input)
        original = args.input.read_bytes()
    except (OSError, XsoError) as exc:
        payload = {"path": str(args.input), "valid": False, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")
        return 1

    difference = first_difference(original, rebuilt)
    original_hash = hashlib.sha256(original).hexdigest().upper()
    rebuilt_hash = hashlib.sha256(rebuilt).hexdigest().upper()
    identical = difference is None
    payload = {
        "path": str(args.input),
        "output": None if args.verify_only or args.output is None else str(args.output),
        "verify_only": args.verify_only,
        "original_size": len(original),
        "rebuilt_size": len(rebuilt),
        "original_sha256": original_hash,
        "rebuilt_sha256": rebuilt_hash,
        "first_difference_offset": difference,
        "identical": identical,
        "string_count": parsed.info.string_count,
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

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0 if identical else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ys VI PSP XSR/XSO 읽기 전용 분석 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("info", help="XSR 구조 정보를 검사합니다")
    info_parser.add_argument("input", type=Path)
    info_parser.add_argument("--json", action="store_true")
    info_parser.set_defaults(func=command_info)

    dump_parser = subparsers.add_parser("dump", help="문자열을 UTF-8 JSON으로 덤프합니다")
    dump_parser.add_argument("input", type=Path)
    dump_parser.add_argument("--output", type=Path)
    dump_parser.add_argument("--overwrite", action="store_true")
    dump_parser.set_defaults(func=command_dump)

    scan_parser = subparsers.add_parser("scan", help="디렉터리의 XSO 파일을 검사합니다")
    scan_parser.add_argument("input", type=Path)
    scan_parser.add_argument("--recursive", action="store_true")
    scan_parser.add_argument("--json", action="store_true")
    scan_parser.set_defaults(func=command_scan)

    stats_parser = subparsers.add_parser(
        "code-stats", help="가변 길이 명령 스트림과 문자열 인자 후보를 JSON으로 출력합니다"
    )
    stats_parser.add_argument("input", type=Path)
    stats_parser.add_argument("--include-commands", action="store_true")
    stats_parser.set_defaults(func=command_code_stats)

    roundtrip_parser = subparsers.add_parser(
        "roundtrip", help="XSR을 무수정 재조립하고 원본과 바이트 단위로 비교합니다"
    )
    roundtrip_parser.add_argument("input", type=Path)
    roundtrip_parser.add_argument("output", type=Path, nargs="?")
    roundtrip_parser.add_argument("--verify-only", action="store_true")
    roundtrip_parser.add_argument("--overwrite", action="store_true")
    roundtrip_parser.add_argument("--json", action="store_true")
    roundtrip_parser.set_defaults(func=command_roundtrip)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
