#!/usr/bin/env python3
"""Extract, validate, and patch EUC-JP system messages stored in Ys VI EBOOT."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

try:
    from tools.scripts.ys6_hangul_codec import normalize_game_punctuation
except ModuleNotFoundError:
    from ys6_hangul_codec import normalize_game_punctuation

STATUSES = ("untranslated", "draft", "override", "excluded", "conflict")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _is_japanese(text: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        for char in text
    )


FORMAT_TOKEN = re.compile(r"%(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.\d+|\.\*)?(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcspn%]")
ALLOWED_CONTROLS = frozenset("\r\n\t")
CONFIRMED_EXTENDED_RANGES = (
    (0x1223E8, 0x122DE2),
    (0x12DCB4, 0x12E8A6),
)
CONFIRMED_SHORT_OFFSETS = frozenset((
    0x11E4B8, 0x11EC28, 0x11F1C4, 0x120DF4, 0x120DFC, 0x121648,
))


def _is_candidate(text: str, offset: int) -> bool:
    visible = text.strip()
    if not visible or not _is_japanese(visible):
        return False
    if any(ord(c) < 0x20 and c not in ALLOWED_CONTROLS for c in visible):
        return False
    if len(visible) >= 4:
        return True
    # Short labels are only accepted in the EBOOT's read-only data region and
    # must consist entirely of Japanese/fullwidth characters.
    return offset >= 0x110000 and len(visible) >= 2 and all(
        ord(c) >= 0x80 or c in ALLOWED_CONTROLS for c in visible
    )


def format_tokens(text: str) -> list[str]:
    return FORMAT_TOKEN.findall(text)


def classify_offset(offset: int) -> str:
    if 0x1223E8 <= offset < 0x122DE2:
        return "저장·불러오기"
    if 0x12DCB4 <= offset < 0x12E8A6:
        return "검·마법·강화"
    return ""


def is_confirmed_extension(row: dict) -> bool:
    offset = int(row["offset"])
    return offset in CONFIRMED_SHORT_OFFSETS or any(start <= offset < end for start, end in CONFIRMED_EXTENDED_RANGES)


def extract(eboot: bytes) -> dict:
    """Extract null-terminated EUC-JP strings beginning after a null byte."""
    records: list[dict] = []
    start = 0
    size = len(eboot)
    while start < size:
        end = eboot.find(b"\0", start)
        if end < 0:
            break
        raw = eboot[start:end]
        if raw:
            try:
                text = raw.decode("euc_jp")
            except UnicodeDecodeError:
                text = ""
            if text and _is_candidate(text, start):
                records.append({
                    "identifier": f"SYS_{start:08X}",
                    "offset": start,
                    "source": text,
                    "source_raw_hex": raw.hex().upper(),
                    "source_sha256": sha256(raw),
                    "allocated_size": len(raw) + 1,
                    "translation": "",
                    "status": "untranslated",
                    "category": classify_offset(start),
                    "format_tokens": format_tokens(text),
                    "notes": "",
                })
        start = end + 1
    return {
        "schema_version": 1,
        "source_eboot_sha256": sha256(eboot),
        "record_count": len(records),
        "encoding": "euc_jp",
        "records": records,
    }


def load_workspace(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_workspace(document)
    if errors:
        raise ValueError("; ".join(errors))
    return document


def encoded_length(text: str) -> int:
    """Length of the EUC-JP storage form (spaces and game punctuation are fullwidth)."""
    text = normalize_game_punctuation(text)
    return sum(1 if ord(char) < 0x80 and char != " " else 2 for char in text)


def encode_system_translation(text: str, mapping: list[dict]) -> bytes:
    """Encode Korean text for the EBOOT EUC-JP layer before its runtime SJIS conversion."""
    text = normalize_game_punctuation(text)
    codes = {row["character"]: int(row["game_code"], 0) for row in mapping}
    output = bytearray()
    for character in text:
        if character == " ":
            output.extend("　".encode("euc_jp"))
        elif character in codes:
            game_code = codes[character]
            game_bytes = game_code.to_bytes(2, "big")
            try:
                original_character = game_bytes.decode("cp932")
                euc_bytes = original_character.encode("euc_jp")
            except (UnicodeDecodeError, UnicodeEncodeError) as exc:
                raise ValueError(
                    f"{character!r}: game code 0x{game_code:04X} cannot be represented in EUC-JP"
                ) from exc
            if len(euc_bytes) != 2:
                raise ValueError(
                    f"{character!r}: game code 0x{game_code:04X} has unexpected EUC-JP length"
                )
            output.extend(euc_bytes)
        elif ord(character) < 0x80:
            output.append(ord(character))
        else:
            try:
                encoded = character.encode("euc_jp")
            except UnicodeEncodeError as exc:
                raise ValueError(f"unsupported system-message character: {character!r}") from exc
            output.extend(encoded)
    return bytes(output)


def validate_workspace(document: dict) -> list[str]:
    errors: list[str] = []
    rows = document.get("records")
    if document.get("schema_version") != 1 or not isinstance(rows, list):
        return ["unsupported system-message workspace schema"]
    if document.get("encoding") != "euc_jp":
        errors.append("system-message encoding must be euc_jp")
    if document.get("record_count") != len(rows):
        errors.append(f"record_count mismatch: {document.get('record_count')} != {len(rows)}")
    seen_ids: set[str] = set()
    seen_offsets: set[int] = set()
    for position, row in enumerate(rows):
        identifier = row.get("identifier")
        offset = row.get("offset")
        if not isinstance(identifier, str) or not identifier or identifier in seen_ids:
            errors.append(f"record {position}: invalid or duplicate identifier")
        else:
            seen_ids.add(identifier)
        if not isinstance(offset, int) or offset < 0 or offset in seen_offsets:
            errors.append(f"record {position}: invalid or duplicate offset")
        else:
            seen_offsets.add(offset)
        raw_hex = row.get("source_raw_hex")
        try:
            raw = bytes.fromhex(raw_hex) if isinstance(raw_hex, str) else b""
        except ValueError:
            raw = b""
        if not raw or sha256(raw) != row.get("source_sha256"):
            errors.append(f"{identifier}: invalid source bytes or SHA-256")
        else:
            try:
                if raw.decode("euc_jp") != row.get("source"):
                    errors.append(f"{identifier}: source text does not match EUC-JP bytes")
            except UnicodeDecodeError:
                errors.append(f"{identifier}: source is not valid EUC-JP")
        allocated = row.get("allocated_size")
        if not isinstance(allocated, int) or allocated != len(raw) + 1:
            errors.append(f"{identifier}: invalid allocated_size")
        if row.get("status") not in STATUSES:
            errors.append(f"{identifier}: invalid status")
        translation = row.get("translation", "")
        if not isinstance(translation, str) or "\0" in translation:
            errors.append(f"{identifier}: invalid translation")
            translation = ""
        if row.get("status") == "override" and not translation.strip():
            errors.append(f"{identifier}: override translation is empty")
        expected_tokens = row.get("format_tokens", format_tokens(row.get("source", "")))
        if not isinstance(expected_tokens, list) or not all(isinstance(x, str) for x in expected_tokens):
            errors.append(f"{identifier}: invalid format_tokens")
            expected_tokens = []
        if row.get("status") == "override" and format_tokens(translation) != expected_tokens:
            errors.append(
                f"{identifier}: format token mismatch "
                f"({expected_tokens!r} != {format_tokens(translation)!r})"
            )
        if row.get("status") == "override" and encoded_length(translation) + 1 > allocated:
            errors.append(
                f"{identifier}: translation is too long "
                f"({encoded_length(translation) + 1}/{allocated} bytes)"
            )
    return errors


def verify_source(eboot: bytes, workspace: dict) -> list[str]:
    errors: list[str] = []
    expected_hash = workspace.get("source_eboot_sha256")
    if expected_hash and sha256(eboot) != expected_hash:
        errors.append("source EBOOT SHA-256 mismatch")
    for row in workspace.get("records", []):
        offset = int(row["offset"])
        raw = bytes.fromhex(row["source_raw_hex"])
        actual = eboot[offset:offset + len(raw)]
        if actual != raw or eboot[offset + len(raw):offset + len(raw) + 1] != b"\0":
            errors.append(f"{row['identifier']}: source bytes mismatch at 0x{offset:X}")
    return errors


def patch_overrides(eboot: bytes, workspace: dict, mapping: list[dict]) -> tuple[bytes, list[dict]]:
    errors = validate_workspace(workspace) + verify_source(eboot, workspace)
    if errors:
        raise ValueError("; ".join(errors))
    output = bytearray(eboot)
    report: list[dict] = []
    for row in workspace["records"]:
        if row.get("status") != "override":
            continue
        encoded = encode_system_translation(row["translation"], mapping)
        allocated = int(row["allocated_size"])
        if len(encoded) + 1 > allocated:
            raise ValueError(
                f"{row['identifier']}: encoded translation is too long "
                f"({len(encoded) + 1}/{allocated} bytes)"
            )
        offset = int(row["offset"])
        output[offset:offset + allocated] = encoded + bytes(allocated - len(encoded))
        report.append({
            "identifier": row["identifier"], "offset_hex": f"0x{offset:X}",
            "source": row["source"], "translation": row["translation"],
            "allocated_size": allocated, "encoded_length": len(encoded) + 1,
            "encoded_hex": encoded.hex().upper(),
        })
    return bytes(output), report


def atomic_write_json(path: Path, document: dict, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        path.with_suffix(path.suffix + ".bak").write_bytes(path.read_bytes())
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def merge_workspace(existing: dict, extracted: dict) -> tuple[dict, dict]:
    """Preserve every existing editable field and append only new source records."""
    errors = validate_workspace(existing)
    if errors:
        raise ValueError("existing workspace is invalid: " + "; ".join(errors))
    if existing.get("source_eboot_sha256") != extracted.get("source_eboot_sha256"):
        raise ValueError("workspace and extraction source EBOOT SHA-256 mismatch")
    extracted_by_offset = {row["offset"]: row for row in extracted["records"]}
    before_rows = existing["records"]
    for row in before_rows:
        fresh = extracted_by_offset.get(row["offset"])
        if fresh is not None and fresh["source_sha256"] != row["source_sha256"]:
            raise ValueError(f"existing source record changed: {row['identifier']}")
    merged_rows = [dict(row) for row in before_rows]
    existing_offsets = {row["offset"] for row in before_rows}
    new_rows = [dict(row) for row in extracted["records"] if row["offset"] not in existing_offsets]
    added = [row for row in new_rows if is_confirmed_extension(row)]
    candidates = [row for row in new_rows if not is_confirmed_extension(row)]
    merged_rows.extend(added)
    merged_rows.sort(key=lambda row: row["offset"])
    merged = dict(existing)
    merged["records"] = merged_rows
    merged["record_count"] = len(merged_rows)
    return merged, {
        "before_count": len(before_rows), "extracted_count": len(extracted["records"]),
        "added_count": len(added), "after_count": len(merged_rows),
        "added_identifiers": [row["identifier"] for row in added],
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def write_analysis_reports(directory: Path, merge_report: dict, merged: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    added_ids = set(merge_report["added_identifiers"])
    confirmed = [row for row in merged["records"] if row["identifier"] in added_ids]
    candidates = merge_report.get("candidates", [])
    for name, rows in (("confirmed-new", confirmed), ("candidate-review", candidates)):
        (directory / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        with (directory / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            fields = ("identifier", "offset", "source", "allocated_size", "category", "format_tokens", "status")
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                item = dict(row); item["offset"] = f"0x{int(row['offset']):X}"
                item["format_tokens"] = " | ".join(row.get("format_tokens", []))
                writer.writerow(item)
    summary = {key: value for key, value in merge_report.items() if key not in ("candidates", "added_identifiers")}
    summary["status_counts"] = {
        status: sum(row.get("status") == status for row in merged["records"])
        for status in STATUSES
    }
    (directory / "merge-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eboot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--merge", type=Path, help="preserve and extend an existing workspace")
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        document = extract(args.eboot.read_bytes())
        merge_report = None
        if args.merge:
            document, merge_report = merge_workspace(load_workspace(args.merge), document)
        atomic_write_json(args.output, document, backup=bool(args.merge))
        if merge_report is not None and args.report_dir is not None:
            write_analysis_reports(args.report_dir, merge_report, document)
        known = next((row for row in document["records"] if row["source"] == "装備全般の設定を行います。"), None)
        if known is None or known["offset"] != 0x12CF34:
            raise ValueError("known equipment message was not extracted at 0x12CF34")
        print(json.dumps({"records": len(document["records"]), "known_offset": known["offset"], "merge": merge_report}, ensure_ascii=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"시스템 메시지 추출 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
