#!/usr/bin/env python3
"""Create, validate and save the Ys VI item translation workspace."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

try:
    from tools.scripts.ys6_invinfo import parse
    from tools.scripts.ys6_windows_korean_codec import decode_custom, load_code_map
    from tools.scripts.ys6_hangul_codec import normalize_game_punctuation
except ModuleNotFoundError:
    from ys6_invinfo import parse
    from ys6_windows_korean_codec import decode_custom, load_code_map
    from ys6_hangul_codec import normalize_game_punctuation

STATUSES = ("untranslated", "draft", "override", "excluded", "conflict")
FULLWIDTH_PUNCTUATION = frozenset(",.?!")


def normalize_description(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def encoded_length(text: str, description: bool = False) -> int:
    """Return the byte length used by the current game encoder."""
    text = normalize_description(text)
    if description: text = text.replace("\n", "\r\n")
    text = normalize_game_punctuation(text)
    total = 0
    for character in text:
        if ord(character) < 0x80: total += 1
        else: total += 2
    return total


def create(psp_data: bytes, windows_data: bytes, code_map: dict[bytes, str]) -> dict:
    psp_rows, windows_rows = parse(psp_data), parse(windows_data)
    records = []
    for psp, windows in zip(psp_rows, windows_rows):
        if psp.index != windows.index or psp.resource_id != windows.resource_id or psp.metadata != windows.metadata:
            raise ValueError(f"PSP/Windows item metadata mismatch: {psp.index}")
        ko_name, name_unknown = decode_custom(windows.name_raw, code_map)
        ko_description, desc_unknown = decode_custom(windows.description_raw, code_map)
        replacements = {"{97D7}": "「", "{97D8}": "」"}
        for before, after in replacements.items():
            ko_name = ko_name.replace(before, after)
            ko_description = ko_description.replace(before, after)
        unresolved = [x for x in name_unknown + desc_unknown if "{" + x + "}" not in replacements]
        records.append({
            "index": psp.index, "resource_id": psp.resource_id,
            "source_name": psp.name_raw.decode("cp932"),
            "source_description": normalize_description(psp.description_raw.decode("cp932")),
            "source_record_sha256": hashlib.sha256(psp_data[psp.offset:psp.offset + 184]).hexdigest().upper(),
            "translation_name": ko_name,
            "translation_description": normalize_description(ko_description),
            "status": "conflict" if unresolved else "draft",
            "notes": ("미해결 Windows 코드: " + ", ".join(unresolved)) if unresolved else "Windows 한글판 초깃값",
        })
    return {"schema_version": 1, "source_sha256": hashlib.sha256(psp_data).hexdigest().upper(),
            "record_count": len(records), "records": records}


def load_workspace(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_workspace(document)
    if errors:
        raise ValueError("; ".join(errors))
    return document


def validate_workspace(document: dict) -> list[str]:
    errors = []
    rows = document.get("records")
    if document.get("schema_version") != 1 or not isinstance(rows, list):
        return ["unsupported item workspace schema"]
    if len(rows) != 73:
        errors.append(f"item record count must be 73: {len(rows)}")
    seen = set()
    for pos, row in enumerate(rows):
        index = row.get("index")
        if not isinstance(index, int) or not 0 <= index < 73 or index in seen:
            errors.append(f"invalid or duplicate item index: {index}")
        seen.add(index)
        if row.get("status") not in STATUSES:
            errors.append(f"item {index}: invalid status")
        for key in ("translation_name", "translation_description"):
            value = row.get(key, "")
            if not isinstance(value, str) or "\0" in value:
                errors.append(f"item {index}: invalid {key}")
        if row.get("status") == "override" and not row.get("translation_name", "").strip():
            errors.append(f"item {index}: override name is empty")
        name_length = encoded_length(row.get("translation_name", "")) + 1
        description_length = encoded_length(row.get("translation_description", ""), True) + 1
        if name_length > 32: errors.append(f"item {index}: name is too long ({name_length}/32 bytes)")
        if description_length > 108: errors.append(f"item {index}: description is too long ({description_length}/108 bytes)")
    return errors


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
        if os.path.exists(temporary): os.unlink(temporary)
