#!/usr/bin/env python3
"""Inventory translated Ys VI records and resolve conservative runtime candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tools.scripts.ys6_translation_workspace import MARKUP_PATTERN, TOKEN_PATTERN, key, source_hash, validate
except ModuleNotFoundError:
    from ys6_translation_workspace import MARKUP_PATTERN, TOKEN_PATTERN, key, source_hash, validate


def translated_records(workspace: dict) -> list[dict]:
    return [r for r in workspace.get("records", []) if r.get("translation")]


def inventory(workspace: dict, applied: dict) -> dict:
    applied_by_key = {key(r): r for r in applied.get("records", [])}
    rows = []
    for record in translated_records(workspace):
        identity = key(record); current = applied_by_key.get(identity)
        errors = []
        try:
            if source_hash(record["source_raw_hex"]) != record["source_sha256"]:
                errors.append("source_sha256")
        except (KeyError, ValueError):
            errors.append("source_raw_hex")
        normalized = record["translation"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
        if sorted(TOKEN_PATTERN.findall(record["source_text"])) != sorted(TOKEN_PATTERN.findall(normalized)):
            errors.append("control_tokens")
        if sorted(MARKUP_PATTERN.findall(record["source_text"])) != sorted(MARKUP_PATTERN.findall(normalized)):
            errors.append("markup")
        if current and current.get("translation") == normalized:
            status = "already_applied"
        elif current and current.get("status") == "override":
            status = "already_applied_override"
        elif errors:
            status = "invalid_tokens" if any(x in errors for x in ("control_tokens", "markup")) else "source_changed"
        else:
            status = "new_exact_source"
        rows.append({"iso_path": identity[0], "string_index": identity[1], "source_text": record["source_text"], "translation": normalized, "source_sha256": record["source_sha256"], "status": status, "errors": " | ".join(errors)})
    applied_source_keys = {key(r) for r in translated_records(workspace)}
    derived = [r for r in applied.get("records", []) if key(r) not in applied_source_keys]
    return {"schema_version": 1, "summary": {"translated_source_count": len(rows), "status_counts": dict(sorted(Counter(r["status"] for r in rows).items())), "derived_applied_count": len(derived), "applied_reviewed_count": len(applied.get("records", []))}, "records": rows}


def resolve(inv: dict, catalog: dict, runtime_map: dict) -> dict:
    new_rows = [r for r in inv["records"] if r["status"] == "new_exact_source"]
    files = {f["iso_path"]: f for f in catalog["files"]}
    strings_by_path = defaultdict(list)
    for row in catalog["strings"]:
        strings_by_path[row["iso_path"]].append(row)
    for rows in strings_by_path.values(): rows.sort(key=lambda x: int(x["string_index"]))
    mapping_by_hash = {m["xso_sha256"]: m for m in runtime_map["mappings"]}
    runtime_by_key = {r["runtime_key"]: r for r in runtime_map["runtime_entries"]}
    by_path = defaultdict(list)
    for row in new_rows: by_path[row["iso_path"]].append(row)
    targets = []
    for source_path, translations in sorted(by_path.items()):
        source_file = files[source_path]; digest = source_file["xso_sha256"]; mapping = mapping_by_hash.get(digest)
        exact_runtime = list(mapping.get("runtime_keys", [])) if mapping else []
        exact_standalone = list(mapping.get("standalone_paths", [])) if mapping else []
        candidates = []
        wanted = [r["source_text"] for r in translations]
        for candidate_path, candidate_strings in strings_by_path.items():
            if candidate_path == source_path: continue
            positions = defaultdict(list)
            for item in candidate_strings: positions[item["text"]].append(int(item["string_index"]))
            if not all(text in positions for text in wanted): continue
            pairs = []
            unique = True
            for row in translations:
                hits = positions[row["source_text"]]
                if len(hits) != 1: unique = False
                pairs.append({"source_index": int(row["string_index"]), "target_indices": hits, "source_text": row["source_text"]})
            candidate_file = files[candidate_path]; candidate_mapping = mapping_by_hash.get(candidate_file["xso_sha256"])
            source_nonempty = [x["text"] for x in strings_by_path[source_path] if x["text"]]
            target_nonempty = [x["text"] for x in candidate_strings if x["text"]]
            if source_nonempty == target_nonempty:
                grade = "exact_structure"
            elif unique and len(wanted) > 1:
                grade = "partial_structure"
            else:
                grade = "text_only"
            candidates.append({"iso_path": candidate_path, "xso_sha256": candidate_file["xso_sha256"], "grade": grade, "index_pairs": pairs, "runtime_keys": list(candidate_mapping.get("runtime_keys", [])) if candidate_mapping else [], "mapping_status": candidate_mapping.get("status") if candidate_mapping else None})
        exact_duplicate_paths = exact_standalone if len(exact_standalone) > 1 else []
        if exact_runtime:
            grade = "exact_payload"
            decision = "automatic"
        elif exact_duplicate_paths:
            grade = "exact_payload"
            decision = "approval_required"
        elif candidates:
            grade = max((c["grade"] for c in candidates), key=lambda x: {"text_only":0,"partial_structure":1,"exact_structure":2}[x])
            decision = "approval_required"
        else:
            grade = "unresolved"; decision = "unresolved"
        targets.append({"source_path": source_path, "xso_sha256": digest, "translation_count": len(translations), "source_indices": [int(r["string_index"]) for r in translations], "grade": grade, "decision": decision, "mapping_status": mapping.get("status") if mapping else None, "exact_runtime_keys": exact_runtime, "exact_runtime_entries": [runtime_by_key[k] for k in exact_runtime], "exact_standalone_paths": exact_standalone, "exact_duplicate_paths": exact_duplicate_paths, "candidates": sorted(candidates, key=lambda c: (c["grade"], c["iso_path"]), reverse=True)})
    return {"schema_version": 1, "summary": {"target_path_count": len(targets), "translation_count": sum(t["translation_count"] for t in targets), "decision_counts": dict(sorted(Counter(t["decision"] for t in targets).items())), "grade_counts": dict(sorted(Counter(t["grade"] for t in targets).items()))}, "targets": targets}


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def write_report(path: Path, inv: dict, resolution: dict) -> None:
    lines = ["# Ys VI 번역 자동 대응 검토 보고서", "", "## 요약", "", f"- 번역 정본 레코드: {inv['summary']['translated_source_count']}", f"- 현재 누적 검수 레코드: {inv['summary']['applied_reviewed_count']}", f"- 파생 적용 레코드: {inv['summary']['derived_applied_count']}", f"- 신규 번역: {resolution['summary']['translation_count']}개 / {resolution['summary']['target_path_count']}경로", f"- 판정: `{resolution['summary']['decision_counts']}`", "", "## 대상", ""]
    for target in resolution["targets"]:
        lines += [f"### `{target['source_path']}`", "", f"- 번역: {target['translation_count']}개, 인덱스 {target['source_indices']}", f"- 등급: `{target['grade']}`", f"- 판정: `{target['decision']}`", f"- 런타임: {target['exact_runtime_keys'] or '없음'}", f"- standalone: {target['exact_standalone_paths'] or '없음'}"]
        for candidate in target["candidates"][:10]:
            lines.append(f"- 후보 `{candidate['grade']}`: `{candidate['iso_path']}` / runtime={candidate['runtime_keys'] or '없음'}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_routes(applied: dict, workspace: dict, catalog: dict, routes: dict) -> tuple[dict, dict]:
    base_report = validate(applied)
    if not base_report["valid"]:
        raise ValueError("applied workspace is invalid: " + "; ".join(base_report["errors"]))
    source_records = {key(r): r for r in workspace.get("records", [])}
    catalog_records = {(r["iso_path"], int(r["string_index"])): r for r in catalog["strings"]}
    files = {f["iso_path"]: f for f in catalog["files"]}
    result = [dict(r) for r in applied["records"]]; existing = {key(r) for r in result}; rows = []
    for route in routes.get("routes", []):
        source_path = route["source_path"]; source_file = files[source_path]
        if route["mode"] == "exact_payload":
            for target_path in route["target_paths"]:
                if files[target_path]["xso_sha256"] != source_file["xso_sha256"]:
                    raise ValueError(f"exact payload route mismatch: {source_path} -> {target_path}")
        default_pairs = route.get("index_pairs", [])
        for target_path in route["target_paths"]:
            pairs = route.get("target_index_pairs", {}).get(target_path, default_pairs)
            if not pairs: raise ValueError(f"route has no index pairs: {target_path}")
            for source_index, target_index in pairs:
                source = source_records.get((source_path, int(source_index))); target = catalog_records.get((target_path, int(target_index)))
                if source is None or target is None: raise ValueError(f"route record missing: {source_path}#{source_index} -> {target_path}#{target_index}")
                if not source.get("translation"): raise ValueError(f"route source translation is empty: {source_path}#{source_index}")
                if source["source_text"] != target["text"]: raise ValueError(f"route source text mismatch: {source_path}#{source_index} -> {target_path}#{target_index}")
                identity = (target_path, int(target_index)); normalized = source["translation"].replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
                if identity in existing:
                    current = next(r for r in result if key(r) == identity)
                    if current["translation"] != normalized: raise ValueError(f"route conflicts with applied translation: {identity}")
                    action = "kept"
                else:
                    prepared = {"iso_path":target_path,"map_group":target.get("map_group",""),"map_id":target.get("map_id",""),"xso_name":target.get("xso_name",""),"string_index":int(target_index),"roles":list(target.get("roles",[])),"source_text":target["text"],"source_raw_hex":target["raw_hex"],"source_sha256":source_hash(target["raw_hex"]),"translation":normalized,"status":"override","notes":f"approved {route['mode']} route from {source_path}#{source_index} (issue {route['approved_issue']})"}
                    result.append(prepared);existing.add(identity);action="added"
                rows.append({"source_path":source_path,"source_index":source_index,"target_path":target_path,"target_index":target_index,"mode":route["mode"],"action":action,"translation":normalized})
    prepared={"schema_version":1,"records":result};report=validate(prepared)
    if not report["valid"]:raise ValueError("routed workspace is invalid: "+"; ".join(report["errors"]))
    return prepared,{"schema_version":1,"summary":{"route_count":len(routes.get("routes",[])),"row_count":len(rows),"added_count":sum(r["action"]=="added" for r in rows),"kept_count":sum(r["action"]=="kept" for r in rows),"reviewed_count":len(result)},"rows":rows}


def analyze(args) -> dict:
    workspace=json.loads(args.workspace.read_text(encoding="utf-8-sig"));applied=json.loads(args.applied.read_text(encoding="utf-8-sig"));catalog=json.loads(args.catalog.read_text(encoding="utf-8-sig"));runtime=json.loads(args.runtime_map.read_text(encoding="utf-8-sig"))
    inv=inventory(workspace,applied);resolution=resolve(inv,catalog,runtime);args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"translation-inventory.json").write_text(json.dumps(inv,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_csv(args.output/"translation-inventory.csv",inv["records"],["iso_path","string_index","status","source_text","translation","source_sha256","errors"])
    (args.output/"resolution-candidates.json").write_text(json.dumps(resolution,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    flat=[]
    for t in resolution["targets"]: flat.append({"source_path":t["source_path"],"translation_count":t["translation_count"],"source_indices":" | ".join(map(str,t["source_indices"])),"grade":t["grade"],"decision":t["decision"],"mapping_status":t["mapping_status"],"runtime_keys":" | ".join(t["exact_runtime_keys"]),"standalone_paths":" | ".join(t["exact_standalone_paths"]),"candidate_count":len(t["candidates"])})
    write_csv(args.output/"resolution-summary.csv",flat,["source_path","translation_count","source_indices","grade","decision","mapping_status","runtime_keys","standalone_paths","candidate_count"])
    write_report(args.output/"review-report.md",inv,resolution)
    summary={"inventory":inv["summary"],"resolution":resolution["summary"]};(args.output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return summary


def main(argv=None) -> int:
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8",errors="backslashreplace")
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True);p=sub.add_parser("analyze");p.add_argument("--workspace",type=Path,required=True);p.add_argument("--applied",type=Path,required=True);p.add_argument("--catalog",type=Path,required=True);p.add_argument("--runtime-map",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    q=sub.add_parser("prepare");q.add_argument("--workspace",type=Path,required=True);q.add_argument("--applied",type=Path,required=True);q.add_argument("--catalog",type=Path,required=True);q.add_argument("--routes",type=Path,required=True);q.add_argument("--output-workspace",type=Path,required=True);q.add_argument("--output-report",type=Path,required=True);args=parser.parse_args(argv)
    try:
        if args.command=="analyze":result=analyze(args)
        else:
            applied=json.loads(args.applied.read_text(encoding="utf-8-sig"));workspace=json.loads(args.workspace.read_text(encoding="utf-8-sig"));catalog=json.loads(args.catalog.read_text(encoding="utf-8-sig"));routes=json.loads(args.routes.read_text(encoding="utf-8-sig"));prepared,report=prepare_routes(applied,workspace,catalog,routes);args.output_workspace.parent.mkdir(parents=True,exist_ok=True);args.output_workspace.write_text(json.dumps(prepared,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");args.output_report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");result=report["summary"]
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,KeyError,ValueError,json.JSONDecodeError) as exc:print(f"번역 대응 분석 실패: {exc}",file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
