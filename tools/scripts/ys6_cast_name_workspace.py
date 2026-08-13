#!/usr/bin/env python3
"""Create, synchronize, validate, and export Ys VI cast-name workspaces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

try:
    from tools.scripts.ys6_castinfo import NAME_SIZE, encode_game_name, parse_records
except ModuleNotFoundError:
    try:
        from .ys6_castinfo import NAME_SIZE, encode_game_name, parse_records
    except ImportError:
        from ys6_castinfo import NAME_SIZE, encode_game_name, parse_records


STATUSES = ("untranslated", "draft", "reviewed", "excluded", "conflict")
CSV_FIELDS = (
    "identifier", "identifier_offset", "name_offset", "source", "source_raw_hex",
    "source_sha256", "translation", "status", "notes",
)


def field_sha256(raw_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(raw_hex)).hexdigest().upper()


def records_from_castinfo(data: bytes) -> list[dict]:
    result = []
    for record in parse_records(data):
        result.append({
            "identifier": record.identifier,
            "identifier_offset": record.identifier_offset,
            "name_offset": record.name_offset,
            "source": record.name_cp932,
            "source_raw_hex": record.name_raw_hex,
            "source_sha256": field_sha256(record.name_raw_hex),
            "translation": "",
            "status": "untranslated",
            "notes": "",
        })
    return result


def synchronize(data: bytes, previous: dict | None = None) -> tuple[dict, list[str]]:
    fresh = records_from_castinfo(data)
    old_by_id = {row.get("identifier"): row for row in (previous or {}).get("records", [])}
    seen = {row["identifier"] for row in fresh}
    for row in fresh:
        old = old_by_id.get(row["identifier"])
        if not old:
            continue
        row["translation"] = old.get("translation", "")
        row["notes"] = old.get("notes", "")
        if old.get("source_sha256") == row["source_sha256"]:
            row["status"] = old.get("status", "untranslated")
        else:
            row["status"] = "conflict"
            note = "원문 32바이트 필드 변경 감지"
            row["notes"] = f"{row['notes']} | {note}".strip(" |")
    orphaned = sorted(identifier for identifier in old_by_id if identifier not in seen)
    workspace = {
        "schema_version": 1,
        "source": {
            "castinfo_sha256": hashlib.sha256(data).hexdigest().upper(),
            "size": len(data),
        },
        "records": fresh,
    }
    return workspace, orphaned


def load_workspace(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("records"), list):
        raise ValueError("지원하는 인물명 작업공간 형식이 아닙니다")
    return data


def reviewed_records(workspace: dict) -> list[dict]:
    return [row for row in workspace["records"] if row.get("status") == "reviewed"]


def validate_workspace(workspace: dict, mappings: list[dict] | None = None) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(workspace.get("records", [])):
        identifier = row.get("identifier", f"#{index}")
        prefix = f"{identifier}: "
        if identifier in seen:
            errors.append(prefix + "identifier 중복")
        seen.add(identifier)
        if row.get("status") not in STATUSES:
            errors.append(prefix + f"알 수 없는 상태 {row.get('status')!r}")
        raw_hex = row.get("source_raw_hex", "")
        try:
            raw = bytes.fromhex(raw_hex)
            if len(raw) != NAME_SIZE:
                errors.append(prefix + f"원문 필드는 {NAME_SIZE}바이트여야 합니다")
            if field_sha256(raw_hex) != row.get("source_sha256"):
                errors.append(prefix + "원문 SHA-256 불일치")
        except ValueError:
            errors.append(prefix + "원문 HEX 형식 오류")
        if row.get("status") == "reviewed":
            translation = row.get("translation", "")
            if not translation:
                errors.append(prefix + "reviewed 번역이 비어 있습니다")
            elif "\x00" in translation:
                errors.append(prefix + "번역에 NUL이 포함되어 있습니다")
            elif mappings is not None:
                try:
                    encode_game_name(translation, mappings)
                except (KeyError, UnicodeError, ValueError) as exc:
                    errors.append(prefix + str(exc))
            else:
                # Every game character is two bytes in the current mapping/CP932 path.
                if len(translation.encode("utf-16-be")) >= NAME_SIZE:
                    errors.append(prefix + "번역이 32바이트 이름 필드에 들어갈 수 없습니다")
    return errors


def atomic_write_json(path: Path, data: dict, backup: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def write_csv(path: Path, workspace: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in CSV_FIELDS} for row in workspace["records"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync")
    sync.add_argument("castinfo", type=Path); sync.add_argument("output", type=Path)
    sync.add_argument("--previous", type=Path); sync.add_argument("--csv", type=Path)
    sync.add_argument("--reviewed", action="append", default=[], metavar="IDENTIFIER=TRANSLATION")
    sync.add_argument("--reviewed-note", default="")
    check = sub.add_parser("validate"); check.add_argument("workspace", type=Path); check.add_argument("--mapping", type=Path)
    export = sub.add_parser("export-csv"); export.add_argument("workspace", type=Path); export.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            previous = load_workspace(args.previous) if args.previous else None
            workspace, orphaned = synchronize(args.castinfo.read_bytes(), previous)
            by_id = {row["identifier"]: row for row in workspace["records"]}
            for assignment in args.reviewed:
                identifier, separator, translation = assignment.partition("=")
                if not separator or identifier not in by_id: raise ValueError(f"잘못된 reviewed 지정: {assignment}")
                by_id[identifier]["translation"] = translation
                by_id[identifier]["status"] = "reviewed"
                by_id[identifier]["notes"] = args.reviewed_note
            errors = validate_workspace(workspace)
            if errors: raise ValueError("; ".join(errors))
            atomic_write_json(args.output, workspace)
            if args.csv: write_csv(args.csv, workspace)
            print(json.dumps({"records": len(workspace["records"]), "orphaned": orphaned}, ensure_ascii=False))
        elif args.command == "validate":
            workspace = load_workspace(args.workspace)
            mappings = json.loads(args.mapping.read_text(encoding="utf-8-sig"))["mappings"] if args.mapping else None
            errors = validate_workspace(workspace, mappings)
            if errors: raise ValueError("\n".join(errors))
            print(json.dumps({"valid": True, "records": len(workspace["records"]), "reviewed": len(reviewed_records(workspace))}, ensure_ascii=False))
        else:
            workspace = load_workspace(args.workspace); write_csv(args.output, workspace)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"인물명 작업공간 처리 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
