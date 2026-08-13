#!/usr/bin/env python3
"""Extract and decode every XSO string from a Ys VI Windows Korean archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_windows_archive import read_entry, read_index
    from tools.scripts.ys6_windows_korean_codec import decode_custom, load_code_map
    from tools.scripts.ys6_xso import parse_xso
except ModuleNotFoundError:
    from ys6_windows_archive import read_entry, read_index
    from ys6_windows_korean_codec import decode_custom, load_code_map
    from ys6_xso import parse_xso


def normalized_iso_path(archive_name: str) -> str:
    name = archive_name[:-2] if archive_name.endswith(".z") else archive_name
    if name.endswith(".xso"):
        name += ".z"
    return "PSP_GAME/USRDIR/data/" + name


def execute(ni_path: Path, na_path: Path, map_path: Path) -> dict:
    mapping = load_code_map(map_path)
    entries = [entry for entry in read_index(ni_path) if entry.name.endswith((".xso", ".xso.z"))]
    records = []
    files = []
    errors = []
    unresolved_counts: Counter[str] = Counter()
    with tempfile.TemporaryDirectory(prefix="ys6-win-xso-") as temporary:
        scratch = Path(temporary) / "entry.xso"
        for entry in entries:
            try:
                extracted = read_entry(na_path, entry)
                scratch.write_bytes(extracted.data)
                parsed = parse_xso(scratch)
                if not parsed.info.valid:
                    raise ValueError(parsed.info.error or "invalid XSO")
                iso_path = normalized_iso_path(entry.name)
                for string in parsed.strings:
                    raw = bytes.fromhex(string.raw_hex)
                    text, unresolved = decode_custom(raw, mapping)
                    unresolved_counts.update(unresolved)
                    records.append({
                        "windows_archive_path": entry.name,
                        "psp_iso_path_candidate": iso_path,
                        "string_index": string.index,
                        "raw_hex": string.raw_hex,
                        "raw_sha256": hashlib.sha256(raw).hexdigest().upper(),
                        "text": text,
                        "unresolved_codes": unresolved,
                        "decode_status": "exact" if not unresolved else "partial",
                    })
                files.append({
                    "windows_archive_path": entry.name,
                    "psp_iso_path_candidate": iso_path,
                    "archive_index": entry.index,
                    "xso_sha256": hashlib.sha256(extracted.data).hexdigest().upper(),
                    "string_count": len(parsed.strings),
                    "command_count": len(parsed.commands),
                })
            except Exception as exc:  # keep a complete audit rather than hiding one bad resource
                errors.append({"archive_index": entry.index, "path": entry.name, "error": str(exc)})
    exact = sum(record["decode_status"] == "exact" for record in records)
    return {
        "schema_version": 1,
        "source": {
            "ni": str(ni_path).replace("\\", "/"),
            "na": str(na_path).replace("\\", "/"),
            "code_map": str(map_path).replace("\\", "/"),
        },
        "stats": {
            "xso_entry_count": len(entries),
            "parsed_xso_count": len(files),
            "error_count": len(errors),
            "string_count": len(records),
            "exact_string_count": exact,
            "partial_string_count": len(records) - exact,
            "unique_unresolved_code_count": len(unresolved_counts),
        },
        "unresolved_code_counts": dict(unresolved_counts.most_common()),
        "errors": errors,
        "files": files,
        "records": records,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ni", type=Path, required=True)
    parser.add_argument("--na", type=Path)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ni_path = args.ni.resolve()
    result = execute(ni_path, (args.na or ni_path.with_suffix(".na")).resolve(), args.map.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
