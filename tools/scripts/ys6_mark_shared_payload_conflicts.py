#!/usr/bin/env python3
"""Mark differing translations for a shared Ys VI payload/index as conflict."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path

NOTE_PREFIX = "shared-payload review 043"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_conflicts(workspace: dict, catalog: dict) -> dict[tuple[str, int], list[dict]]:
    hashes = {row["iso_path"]: row["xso_sha256"] for row in catalog["files"]}
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in workspace["records"]:
        if row.get("status") not in {"draft", "override", "conflict"} or not row.get("translation"):
            continue
        digest = hashes.get(row["iso_path"])
        if digest:
            grouped[(digest, int(row["string_index"]))].append(row)
    return {
        identity: rows for identity, rows in grouped.items()
        if len(rows) > 1 and len({row["translation"] for row in rows}) > 1
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-records", type=int)
    parser.add_argument("--expected-groups", type=int)
    args = parser.parse_args()

    workspace = load(args.workspace)
    catalog = load(args.catalog)
    conflicts = find_conflicts(workspace, catalog)
    records = [row for rows in conflicts.values() for row in rows]
    if args.expected_records is not None and len(records) != args.expected_records:
        raise ValueError(f"record count mismatch: expected={args.expected_records}, actual={len(records)}")
    if args.expected_groups is not None and len(conflicts) != args.expected_groups:
        raise ValueError(f"group count mismatch: expected={args.expected_groups}, actual={len(conflicts)}")

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.workspace, args.backup)
    changed = []
    for (digest, index), rows in sorted(conflicts.items()):
        marker = f"{NOTE_PREFIX} {digest[:12]}#{index}"
        for row in rows:
            row["status"] = "conflict"
            notes = [part.strip() for part in row.get("notes", "").split("|") if part.strip()]
            notes = [part for part in notes if not part.startswith(NOTE_PREFIX)]
            notes.append(marker)
            row["notes"] = " | ".join(notes)
            changed.append({"iso_path": row["iso_path"], "string_index": int(row["string_index"]), "group": f"{digest[:12]}#{index}"})
    before_hash = sha256(args.backup)
    args.workspace.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": 1, "source_sha256": before_hash,
        "output_sha256": sha256(args.workspace), "group_count": len(conflicts),
        "changed_count": len(changed), "changed": changed,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("group_count", "changed_count", "source_sha256", "output_sha256")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
