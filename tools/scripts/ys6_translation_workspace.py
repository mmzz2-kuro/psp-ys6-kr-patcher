#!/usr/bin/env python3
"""Create, synchronize, and validate a Ys VI translation workspace."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

VALID_STATUSES = {"untranslated", "draft", "override", "excluded", "conflict", "orphaned"}
TOKEN_PATTERN = re.compile(r"\\(?:x[0-9A-Fa-f]+|[A-Za-z]+|[0-9]+)")
MARKUP_PATTERN = re.compile(r"<[^<>]+>")
FIELDS = ("iso_path", "map_group", "map_id", "xso_name", "string_index", "roles", "source_text", "source_raw_hex", "source_sha256", "translation", "status", "notes")


def source_hash(raw_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(raw_hex)).hexdigest().upper()


def normalize_editor_translation(text: str) -> str:
    """Store editor line breaks as the game's literal backslash-n control token."""
    return text.rstrip("\r\n").replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def catalog_record(record: dict) -> dict:
    raw_hex = record["raw_hex"]
    return {
        "iso_path": record["iso_path"], "map_group": record.get("map_group", ""),
        "map_id": record.get("map_id", ""), "xso_name": record.get("xso_name", ""),
        "string_index": int(record["string_index"]), "roles": list(record.get("roles", [])),
        "source_text": record["text"], "source_raw_hex": raw_hex,
        "source_sha256": source_hash(raw_hex), "translation": "",
        "status": "untranslated", "notes": "",
    }


def key(record: dict) -> tuple[str, int]:
    return record["iso_path"], int(record["string_index"])


def synchronize(catalog: dict, existing: dict | None = None) -> dict:
    old = {key(item): item for item in (existing or {}).get("records", [])}
    if len(old) != len((existing or {}).get("records", [])):
        raise ValueError("translation workspace contains duplicate keys")
    records = []
    seen = set()
    for source in catalog["strings"]:
        fresh = catalog_record(source); identity = key(fresh); seen.add(identity)
        previous = old.get(identity)
        if previous:
            fresh["translation"] = previous.get("translation", "")
            fresh["notes"] = previous.get("notes", "")
            if "allow_markup_change" in previous:
                fresh["allow_markup_change"] = bool(previous["allow_markup_change"])
            if previous.get("source_sha256") != fresh["source_sha256"]:
                fresh["status"] = "conflict"
            else:
                fresh["status"] = previous.get("status", "untranslated")
        records.append(fresh)
    for identity, previous in old.items():
        if identity not in seen:
            orphan = dict(previous); orphan["status"] = "orphaned"; records.append(orphan)
    return {"schema_version": 1, "records": records}


def validate(workspace: dict) -> dict:
    errors, warnings = [], []
    seen = set()
    for position, record in enumerate(workspace.get("records", [])):
        label = f"record[{position}]"
        missing = [field for field in FIELDS if field not in record]
        if missing: errors.append(f"{label}: missing fields: {missing}"); continue
        identity = key(record)
        if identity in seen: errors.append(f"{label}: duplicate key: {identity}")
        seen.add(identity)
        if record["status"] not in VALID_STATUSES: errors.append(f"{label}: invalid status: {record['status']}")
        try: actual_hash = source_hash(record["source_raw_hex"])
        except ValueError: errors.append(f"{label}: invalid source_raw_hex"); continue
        if actual_hash != record["source_sha256"]: errors.append(f"{label}: source hash mismatch")
        if "\x00" in record["translation"]: errors.append(f"{label}: translation contains NUL")
        if record["status"] == "override":
            if not record["translation"]: errors.append(f"{label}: override translation is empty")
            source_tokens = sorted(TOKEN_PATTERN.findall(record["source_text"]))
            target_tokens = sorted(TOKEN_PATTERN.findall(record["translation"]))
            if source_tokens != target_tokens: errors.append(f"{label}: control token mismatch")
            source_markup = sorted(MARKUP_PATTERN.findall(record["source_text"]))
            target_markup = sorted(MARKUP_PATTERN.findall(record["translation"]))
            if source_markup != target_markup and not record.get("allow_markup_change", False): errors.append(f"{label}: markup mismatch")
        elif record["translation"]:
            warnings.append(f"{label}: translation exists but status is {record['status']}")
    override_count = sum(r.get("status") == "override" for r in workspace.get("records", []))
    return {"valid": not errors, "record_count": len(workspace.get("records", [])), "override_count": override_count, "reviewed_count": override_count, "errors": errors, "warnings": warnings}


def prepare_reviewed(workspace: dict, iso_path: str, first_index: int, last_index: int) -> dict:
    selected = []
    for record in workspace.get("records", []):
        index = int(record.get("string_index", -1))
        if record.get("iso_path") != iso_path or not first_index <= index <= last_index:
            continue
        prepared = dict(record)
        prepared["translation"] = prepared.get("translation", "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
        prepared["status"] = "override"
        selected.append(prepared)
    expected = set(range(first_index, last_index + 1))
    actual = {int(record["string_index"]) for record in selected}
    if actual != expected:
        raise ValueError(f"target indices mismatch: missing={sorted(expected - actual)}")
    result = {"schema_version": 1, "records": selected}
    report = validate(result)
    if not report["valid"]:
        raise ValueError("prepared workspace is invalid: " + "; ".join(report["errors"]))
    return result


def prepare_translated(workspace: dict, iso_path: str, overrides: dict[int, str] | None = None) -> dict:
    overrides = overrides or {}
    selected = []
    for record in workspace.get("records", []):
        if record.get("iso_path") != iso_path or not record.get("translation"):
            continue
        prepared = dict(record)
        if int(prepared["string_index"]) in overrides:
            prepared["translation"] = overrides[int(prepared["string_index"])]
        prepared["translation"] = prepared["translation"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
        prepared["status"] = "override"
        selected.append(prepared)
    if not selected:
        raise ValueError(f"no translated records for ISO path: {iso_path}")
    result = {"schema_version": 1, "records": selected}
    report = validate(result)
    if not report["valid"]:
        raise ValueError("prepared workspace is invalid: " + "; ".join(report["errors"]))
    return result


def prepare_translated_paths(workspace: dict, iso_paths: list[str], overrides: dict[tuple[str, int], str] | None = None, allow_markup_changes: set[tuple[str, int]] | None = None) -> dict:
    """Copy translated records for several paths into one reviewed workspace."""
    overrides = overrides or {}
    allow_markup_changes = allow_markup_changes or set()
    requested = set(iso_paths)
    if len(requested) != len(iso_paths):
        raise ValueError("duplicate ISO path")
    selected = []
    for record in workspace.get("records", []):
        iso_path = record.get("iso_path")
        if iso_path not in requested or not record.get("translation"):
            continue
        prepared = dict(record)
        identity = (iso_path, int(prepared["string_index"]))
        if identity in overrides:
            prepared["translation"] = overrides[identity]
        if identity in allow_markup_changes:
            prepared["allow_markup_change"] = True
            prepared["notes"] = (prepared.get("notes", "") + " | approved Japanese ruby removal").strip(" |")
        prepared["translation"] = prepared["translation"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
        prepared["status"] = "override"
        selected.append(prepared)
    missing = requested - {record["iso_path"] for record in selected}
    if missing:
        raise ValueError(f"no translated records for ISO paths: {sorted(missing)}")
    result = {"schema_version": 1, "records": selected}
    report = validate(result)
    if not report["valid"]:
        raise ValueError("prepared workspace is invalid: " + "; ".join(report["errors"]))
    return result


def append_propagated(prepared: dict, source_workspace: dict, source_path: str, target_path: str, index_pairs: list[tuple[int, int]]) -> dict:
    """Append explicitly paired translations after verifying identical source text."""
    base_report = validate(prepared)
    if not base_report["valid"]:
        raise ValueError("base prepared workspace is invalid: " + "; ".join(base_report["errors"]))
    source = {(r["iso_path"], int(r["string_index"])): r for r in source_workspace.get("records", [])}
    records = [dict(r) for r in prepared["records"]]
    existing = {key(r) for r in records}
    for source_index, target_index in index_pairs:
        source_record = source.get((source_path, source_index))
        target_record = source.get((target_path, target_index))
        if source_record is None or target_record is None:
            raise ValueError(f"propagation record missing: {source_index}:{target_index}")
        if not source_record.get("translation"):
            raise ValueError(f"source translation is empty: {source_index}")
        if source_record["source_text"] != target_record["source_text"]:
            raise ValueError(f"propagation source text mismatch: {source_index}:{target_index}")
        if key(target_record) in existing:
            raise ValueError(f"propagation target already exists: {target_index}")
        propagated = dict(target_record)
        propagated["translation"] = source_record["translation"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
        propagated["status"] = "override"
        propagated["notes"] = f"approved exact propagation from {source_path}#{source_index}"
        records.append(propagated); existing.add(key(propagated))
    result = {"schema_version": 1, "records": records}
    report = validate(result)
    if not report["valid"]:
        raise ValueError("propagated workspace is invalid: " + "; ".join(report["errors"]))
    return result


def append_translated_path(prepared: dict, source_workspace: dict, iso_path: str) -> dict:
    """Append nonempty translations for one path to an existing reviewed workspace."""
    base_report = validate(prepared)
    if not base_report["valid"]:
        raise ValueError("base prepared workspace is invalid: " + "; ".join(base_report["errors"]))
    additions = prepare_translated(source_workspace, iso_path)["records"]
    records = [dict(r) for r in prepared["records"]]
    existing = {key(r) for r in records}
    duplicates = [key(r) for r in additions if key(r) in existing]
    if duplicates:
        raise ValueError(f"translated path contains existing keys: {duplicates}")
    records.extend(additions)
    result = {"schema_version": 1, "records": records}
    report = validate(result)
    if not report["valid"]:
        raise ValueError("combined workspace is invalid: " + "; ".join(report["errors"]))
    return result


def write_csv(workspace: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader()
        for record in workspace["records"]:
            row = dict(record); row["roles"] = " | ".join(row["roles"]); writer.writerow(row)


def apply_drafts(workspace: dict, drafts: dict) -> dict:
    records = [dict(record) for record in workspace.get("records", [])]
    by_key = {key(record): record for record in records}
    if len(by_key) != len(records): raise ValueError("translation workspace contains duplicate keys")
    seen = set()
    for draft in drafts.get("records", []):
        identity = (draft["iso_path"], int(draft["string_index"]))
        if identity in seen: raise ValueError(f"duplicate draft key: {identity}")
        seen.add(identity)
        target = by_key.get(identity)
        if target is None: raise ValueError(f"draft target missing: {identity}")
        if "dialogue" not in target.get("roles", []): raise ValueError(f"draft target is not dialogue: {identity}")
        if "source_sha256" in draft:
            if target["source_sha256"] != draft["source_sha256"]: raise ValueError(f"draft source hash mismatch: {identity}")
        elif "source_text" in draft:
            if target["source_text"] != draft["source_text"]: raise ValueError(f"draft source text mismatch: {identity}")
        else:
            raise ValueError(f"draft source fingerprint missing: {identity}")
        if target.get("status") not in {"untranslated", "draft"}: raise ValueError(f"draft would replace {target.get('status')}: {identity}")
        translation = draft.get("translation", "")
        if not translation: raise ValueError(f"draft translation is empty: {identity}")
        if sorted(TOKEN_PATTERN.findall(target["source_text"])) != sorted(TOKEN_PATTERN.findall(translation)):
            raise ValueError(f"draft control token mismatch: {identity}")
        allow_markup_change = bool(draft.get("allow_markup_change", False))
        if sorted(MARKUP_PATTERN.findall(target["source_text"])) != sorted(MARKUP_PATTERN.findall(translation)) and not allow_markup_change:
            raise ValueError(f"draft markup mismatch: {identity}")
        target["translation"] = translation
        target["status"] = "draft"
        target["notes"] = draft.get("notes", "Codex 초벌 번역 030")
        if allow_markup_change:
            target["allow_markup_change"] = True
    result = {"schema_version": workspace.get("schema_version", 1), "records": records}
    report = validate(result)
    if not report["valid"]: raise ValueError("draft workspace is invalid: " + "; ".join(report["errors"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("sync"); create.add_argument("catalog", type=Path); create.add_argument("output_json", type=Path); create.add_argument("--existing", type=Path); create.add_argument("--csv", type=Path); create.add_argument("--migrate-reviewed-to-override", action="store_true"); create.add_argument("--overwrite", action="store_true")
    check = sub.add_parser("validate"); check.add_argument("workspace", type=Path)
    prepare = sub.add_parser("prepare"); prepare.add_argument("workspace", type=Path); prepare.add_argument("iso_path"); prepare.add_argument("first_index", type=int); prepare.add_argument("last_index", type=int); prepare.add_argument("output", type=Path); prepare.add_argument("--overwrite", action="store_true")
    prepare_translated_parser = sub.add_parser("prepare-translated"); prepare_translated_parser.add_argument("workspace", type=Path); prepare_translated_parser.add_argument("iso_path"); prepare_translated_parser.add_argument("output", type=Path); prepare_translated_parser.add_argument("--translation-override", action="append", default=[]); prepare_translated_parser.add_argument("--overwrite", action="store_true")
    prepare_paths_parser = sub.add_parser("prepare-translated-paths"); prepare_paths_parser.add_argument("workspace", type=Path); prepare_paths_parser.add_argument("output", type=Path); prepare_paths_parser.add_argument("iso_paths", nargs="+"); prepare_paths_parser.add_argument("--translation-override", action="append", default=[]); prepare_paths_parser.add_argument("--allow-markup-change", action="append", default=[]); prepare_paths_parser.add_argument("--overwrite", action="store_true")
    propagate_parser = sub.add_parser("append-propagated"); propagate_parser.add_argument("prepared", type=Path); propagate_parser.add_argument("source_workspace", type=Path); propagate_parser.add_argument("source_path"); propagate_parser.add_argument("target_path"); propagate_parser.add_argument("output", type=Path); propagate_parser.add_argument("index_pairs", nargs="+"); propagate_parser.add_argument("--overwrite", action="store_true")
    append_path_parser = sub.add_parser("append-translated-path"); append_path_parser.add_argument("prepared", type=Path); append_path_parser.add_argument("source_workspace", type=Path); append_path_parser.add_argument("iso_path"); append_path_parser.add_argument("output", type=Path); append_path_parser.add_argument("--overwrite", action="store_true")
    draft_parser = sub.add_parser("apply-drafts"); draft_parser.add_argument("workspace", type=Path); draft_parser.add_argument("drafts", type=Path); draft_parser.add_argument("output", type=Path); draft_parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.command == "validate":
        report = validate(json.loads(args.workspace.read_text(encoding="utf-8-sig"))); print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if report["valid"] else 1
    if args.command == "prepare":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig")); prepared = prepare_reviewed(workspace, args.iso_path, args.first_index, args.last_index)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(prepared["records"]), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.command == "prepare-translated":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        overrides = {}
        for value in args.translation_override:
            raw_index, separator, translation = value.partition("=")
            if not separator: raise ValueError(f"invalid translation override: {value}")
            overrides[int(raw_index)] = translation.replace("\\n", "\n")
        workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig")); prepared = prepare_translated(workspace, args.iso_path, overrides)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(prepared["records"]), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.command == "prepare-translated-paths":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        overrides = {}
        for value in args.translation_override:
            raw_path, separator, remainder = value.partition("::")
            raw_index, equals, translation = remainder.partition("=")
            if not separator or not equals: raise ValueError(f"invalid translation override: {value}")
            overrides[(raw_path, int(raw_index))] = translation.replace("\\n", "\n")
        allow_markup_changes = set()
        for value in args.allow_markup_change:
            raw_path, separator, raw_index = value.partition("::")
            if not separator: raise ValueError(f"invalid markup-change approval: {value}")
            allow_markup_changes.add((raw_path, int(raw_index)))
        workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig")); prepared = prepare_translated_paths(workspace, args.iso_paths, overrides, allow_markup_changes)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(prepared["records"]), "paths": len(args.iso_paths), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.command == "append-propagated":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        pairs = []
        for value in args.index_pairs:
            left, separator, right = value.partition(":")
            if not separator: raise ValueError(f"invalid index pair: {value}")
            pairs.append((int(left), int(right)))
        prepared = json.loads(args.prepared.read_text(encoding="utf-8-sig")); source_workspace = json.loads(args.source_workspace.read_text(encoding="utf-8-sig"))
        result = append_propagated(prepared, source_workspace, args.source_path, args.target_path, pairs)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(result["records"]), "propagated": len(pairs), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.command == "append-translated-path":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        prepared = json.loads(args.prepared.read_text(encoding="utf-8-sig")); source_workspace = json.loads(args.source_workspace.read_text(encoding="utf-8-sig"))
        result = append_translated_path(prepared, source_workspace, args.iso_path)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(result["records"]), "added": len(result["records"]) - len(prepared["records"]), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.command == "apply-drafts":
        if args.output.exists() and not args.overwrite: raise FileExistsError(args.output)
        workspace = json.loads(args.workspace.read_text(encoding="utf-8-sig")); drafts = json.loads(args.drafts.read_text(encoding="utf-8-sig"))
        result = apply_drafts(workspace, drafts)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": len(result["records"]), "drafts": len(drafts.get("records", [])), "output": str(args.output)}, ensure_ascii=False, indent=2)); return 0
    if args.output_json.exists() and not args.overwrite: raise FileExistsError(args.output_json)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8-sig")); existing = json.loads(args.existing.read_text(encoding="utf-8-sig")) if args.existing else None
    if existing and args.migrate_reviewed_to_override:
        for record in existing.get("records", []):
            if record.get("status") == "reviewed": record["status"] = "override"
    workspace = synchronize(catalog, existing); args.output_json.parent.mkdir(parents=True, exist_ok=True); args.output_json.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.csv: write_csv(workspace, args.csv)
    print(json.dumps({"records": len(workspace["records"]), "output": str(args.output_json)}, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace"); raise SystemExit(main())
