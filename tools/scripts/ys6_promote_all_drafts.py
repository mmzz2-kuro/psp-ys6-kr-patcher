#!/usr/bin/env python3
"""Promote all nonempty Ys VI drafts to override with backup and validation."""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected", type=int, required=True)
    args = parser.parse_args()

    document = json.loads(args.workspace.read_text(encoding="utf-8-sig"))
    targets = [row for row in document["records"] if row.get("status") == "draft" and row.get("translation")]
    if len(targets) != args.expected:
        raise ValueError(f"target count mismatch: expected={args.expected}, actual={len(targets)}")
    before_payload = {
        (row["iso_path"], int(row["string_index"])): json.dumps(
            {key: value for key, value in row.items() if key != "status"},
            ensure_ascii=False, sort_keys=True,
        ) for row in targets
    }

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.workspace, args.backup)
    source_hash = sha256(args.backup)
    for row in targets:
        row["status"] = "override"

    report = validate(document)
    if not report["valid"]:
        raise ValueError("promoted workspace is invalid: " + "; ".join(report["errors"]))
    after_payload = {
        (row["iso_path"], int(row["string_index"])): json.dumps(
            {key: value for key, value in row.items() if key != "status"},
            ensure_ascii=False, sort_keys=True,
        ) for row in targets
    }
    changed_payloads = [identity for identity in before_payload if before_payload[identity] != after_payload[identity]]
    if changed_payloads:
        raise ValueError(f"non-status fields changed: {changed_payloads[:5]}")

    args.workspace.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "schema_version": 1,
        "source_sha256": source_hash,
        "output_sha256": sha256(args.workspace),
        "promoted_count": len(targets),
        "non_status_change_count": len(changed_payloads),
        "status_counts": {
            status: sum(row.get("status") == status for row in document["records"])
            for status in ("untranslated", "draft", "override", "excluded", "conflict", "orphaned")
        },
        "validation_error_count": len(report["errors"]),
    }
    args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
