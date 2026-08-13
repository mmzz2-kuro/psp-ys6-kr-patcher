#!/usr/bin/env python3
"""Mark unresolved Ys VI draft control-token mismatches as conflict."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

try:
    from tools.scripts.ys6_translation_workspace import validate
except ModuleNotFoundError:
    from ys6_translation_workspace import validate


NOTE = "control-linebreak review 040"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def has_control_error(record: dict) -> bool:
    candidate = dict(record)
    candidate["status"] = "override"
    report = validate({"schema_version": 1, "records": [candidate]})
    return any(
        error.endswith("control token mismatch")
        or error.endswith("invalid player-name expansion")
        for error in report["errors"]
    )


def mark(document: dict) -> tuple[dict, list[dict]]:
    result = json.loads(json.dumps(document, ensure_ascii=False))
    changed = []
    for record in result.get("records", []):
        if record.get("status") != "draft" or not record.get("translation"):
            continue
        if not has_control_error(record):
            continue
        record["status"] = "conflict"
        notes = [part.strip() for part in record.get("notes", "").split("|") if part.strip()]
        if NOTE not in notes:
            notes.append(NOTE)
        record["notes"] = " | ".join(notes)
        changed.append({"iso_path": record["iso_path"], "string_index": int(record["string_index"])})
    return result, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected", type=int)
    args = parser.parse_args()

    document = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    result, changed = mark(document)
    if args.expected is not None and len(changed) != args.expected:
        raise ValueError(f"target count mismatch: expected={args.expected}, actual={len(changed)}")

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.workspace, args.backup)
    source_hash = sha256(args.backup)
    args.workspace.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": 1,
        "source_sha256": source_hash,
        "output_sha256": sha256(args.workspace),
        "changed_count": len(changed),
        "draft_count": sum(row.get("status") == "draft" for row in result.get("records", [])),
        "conflict_count": sum(row.get("status") == "conflict" for row in result.get("records", [])),
        "changed": changed,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
