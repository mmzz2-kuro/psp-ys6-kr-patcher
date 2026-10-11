#!/usr/bin/env python3
"""Build the validated SPECIAL VERSION system-message workspace."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

try:
    from tools.scripts.ys6_system_message_workspace import (
        encode_system_translation,
        extract,
        format_tokens,
        validate_workspace,
    )
except ModuleNotFoundError:
    from ys6_system_message_workspace import (
        encode_system_translation,
        extract,
        format_tokens,
        validate_workspace,
    )


def build(seed_boot: Path, audit_report: Path, mapping_path: Path, output: Path,
          aliases_path: Path | None = None) -> dict:
    executable = seed_boot.read_bytes()
    document = extract(executable)
    # BOOT.BIN and EBOOT.BIN have the same string offsets and bytes but different
    # whole-file hashes. Per-record source hashes remain the authority.
    document.pop("source_eboot_sha256", None)
    document["profile"] = "ULJM-05155"
    document["source"] = {
        "audit_report": str(audit_report),
        "mapping": str(mapping_path),
    }

    audit = json.loads(audit_report.read_text(encoding="utf-8-sig"))["system_messages"]
    mapping = json.loads(mapping_path.read_text(encoding="utf-8-sig"))["mappings"]
    if aliases_path:
        aliases = json.loads(aliases_path.read_text(encoding="utf-8-sig"))["aliases"]
        mapping = [*mapping, *aliases]
        document["source"]["aliases"] = str(aliases_path)
    by_offset: dict[int, list[dict]] = defaultdict(list)
    for candidate in audit["candidates"]:
        if not candidate.get("translation"):
            continue
        for value in candidate.get("special_offsets", []):
            by_offset[int(value, 16)].append(candidate)

    applied = []
    blocked = []
    conflicts = []
    matched = 0
    for row in document["records"]:
        candidates = by_offset.get(int(row["offset"]), [])
        if not candidates:
            continue
        matched += 1
        translations = {candidate["translation"] for candidate in candidates}
        if len(translations) != 1:
            row["status"] = "conflict"
            row["notes"] = "SPECIAL 동일 위치의 승인 번역 충돌"
            conflicts.append(row["identifier"])
            continue
        translation = next(iter(translations))
        reasons = []
        if any(candidate.get("source") != row["source"] for candidate in candidates):
            reasons.append("source_mismatch")
        if format_tokens(translation) != row["format_tokens"]:
            reasons.append("format_token_mismatch")
        try:
            encoded = encode_system_translation(translation, mapping)
        except ValueError as exc:
            encoded = b""
            reasons.append(f"encoding:{exc}")
        if encoded and len(encoded) + 1 > int(row["allocated_size"]):
            reasons.append(f"overflow:{len(encoded) + 1}/{row['allocated_size']}")
        row["translation"] = translation
        if reasons:
            row["status"] = "draft"
            row["notes"] = "; ".join(reasons)
            blocked.append({"identifier": row["identifier"], "reasons": reasons})
        else:
            row["status"] = "override"
            row["notes"] = "115번 승인 번역의 SPECIAL 원문·위치 정확 대응"
            applied.append(row["identifier"])

    document["summary"] = {
        "extracted_count": len(document["records"]),
        "approved_offset_match_count": matched,
        "override_count": len(applied),
        "blocked_count": len(blocked),
        "conflict_count": len(conflicts),
        "untranslated_count": sum(row["status"] == "untranslated" for row in document["records"]),
    }
    errors = validate_workspace(document)
    if errors:
        raise ValueError("generated system-message workspace invalid: " + "; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "valid": True,
        **document["summary"],
        "applied": applied,
        "blocked": blocked,
        "conflicts": conflicts,
    }
    report_path = output.with_name("system-message-build-report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed_boot", type=Path)
    parser.add_argument("audit_report", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--aliases", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.seed_boot, args.audit_report, args.mapping, args.output, args.aliases),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
