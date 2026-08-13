#!/usr/bin/env python3
"""Snapshot and merge large dialogue draft translation batches safely."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_cast_name_workspace import atomic_write_json
except ModuleNotFoundError:
    try:
        from .ys6_cast_name_workspace import atomic_write_json
    except ImportError:
        from ys6_cast_name_workspace import atomic_write_json


def make_snapshot(workspace: dict) -> dict:
    records = [
        {key: row.get(key) for key in ("iso_path", "map_group", "map_id", "xso_name", "string_index", "roles", "source_text", "source_raw_hex", "source_sha256")}
        for row in workspace.get("records", [])
        if row.get("status") == "untranslated" and "dialogue" in row.get("roles", [])
    ]
    return {"schema_version": 1, "target_status": "untranslated", "target_role": "dialogue", "records": records}


def progress(snapshot: dict, workspace: dict) -> dict:
    current = {(row["iso_path"], int(row["string_index"])): row for row in workspace["records"]}
    counts = Counter(); paths = set()
    for target in snapshot["records"]:
        row = current.get((target["iso_path"], int(target["string_index"])))
        status = row.get("status", "missing") if row else "missing"
        counts[status] += 1
        if status == "draft": paths.add(target["iso_path"])
    return {"schema_version": 1, "target_count": len(snapshot["records"]), "status_counts": dict(sorted(counts.items())), "draft_path_count": len(paths)}


def propagate_exact(workspace: dict) -> tuple[dict, dict]:
    translations: dict[str, set[tuple[str, bool]]] = {}
    for row in workspace["records"]:
        if "dialogue" not in row.get("roles", []): continue
        text = row["source_text"]
        if row.get("translation") and row.get("status") in {"draft", "override"}:
            translations.setdefault(text, set()).add(
                (row["translation"], bool(row.get("allow_markup_change", False)))
            )
    applied, ambiguous = 0, 0
    records = [dict(row) for row in workspace["records"]]
    for row in records:
        if row.get("status") != "untranslated" or "dialogue" not in row.get("roles", []): continue
        candidates = translations.get(row["source_text"], set())
        if len(candidates) == 1:
            translation, allow_markup_change = next(iter(candidates))
            row["translation"] = translation; row["status"] = "draft"
            if allow_markup_change:
                row["allow_markup_change"] = True
            row["notes"] = "exact-source draft propagation 033"; applied += 1
        elif len(candidates) > 1: ambiguous += 1
    return {"schema_version": workspace.get("schema_version", 1), "records": records}, {"applied":applied,"ambiguous":ambiguous}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot"); snap.add_argument("workspace", type=Path); snap.add_argument("output", type=Path)
    report = sub.add_parser("progress"); report.add_argument("snapshot", type=Path); report.add_argument("workspace", type=Path); report.add_argument("output", type=Path)
    exact = sub.add_parser("propagate-exact"); exact.add_argument("workspace", type=Path); exact.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "snapshot":
        data = make_snapshot(json.loads(args.workspace.read_text(encoding="utf-8-sig")))
    elif args.command == "progress":
        data = progress(json.loads(args.snapshot.read_text(encoding="utf-8-sig")), json.loads(args.workspace.read_text(encoding="utf-8-sig")))
    else:
        data, report_data = propagate_exact(json.loads(args.workspace.read_text(encoding="utf-8-sig")))
    atomic_write_json(args.output, data)
    shown = report_data if args.command == "propagate-exact" else (data if args.command == "progress" else {"targets":len(data["records"])})
    print(json.dumps(shown, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
