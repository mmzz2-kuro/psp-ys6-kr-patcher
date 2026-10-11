#!/usr/bin/env python3
"""Apply reviewed manual translations to a remaining SPECIAL IDM workspace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply(workspace_path: Path, overrides_path: Path, output_path: Path) -> dict:
    workspace = json.loads(workspace_path.read_text(encoding="utf-8-sig"))
    overrides = json.loads(overrides_path.read_text(encoding="utf-8-sig"))["translations"]
    by_id = {row["unit_id"]: row for row in workspace["units"]}
    missing = sorted(set(overrides) - set(by_id))
    if missing: raise ValueError(f"unknown remaining IDM unit IDs: {missing}")
    changed = []
    for unit_id, translation in overrides.items():
        if not translation: raise ValueError(f"blank manual translation: {unit_id}")
        row = by_id[unit_id]
        if row["status"] not in ("needs_translation", "ambiguous_review", "translated"):
            raise ValueError(f"manual translation would replace {row['status']}: {unit_id}")
        row["translation"] = translation; row["status"] = "translated"
        row["reuse_method"] = "manual_reviewed"; changed.append(unit_id)
    from collections import Counter
    workspace["summary"]["status_counts"] = dict(Counter(row["status"] for row in workspace["units"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"valid": True, "manual_translation_count": len(changed), "unit_ids": sorted(changed),
            "status_counts": workspace["summary"]["status_counts"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path); parser.add_argument("overrides", type=Path)
    parser.add_argument("output", type=Path); args = parser.parse_args()
    print(json.dumps(apply(args.workspace, args.overrides, args.output), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
