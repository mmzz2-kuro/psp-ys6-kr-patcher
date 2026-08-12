#!/usr/bin/env python3
"""Apply reviewed workspace translations to one extracted Ys VI XSO."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
try:
    from tools.scripts.ys6_hangul_codec import encode_translation, normalize_game_punctuation
    from tools.scripts.ys6_translation_workspace import validate
    from tools.scripts.ys6_xso import parse_xso, rebuild_xso
except ModuleNotFoundError:
    from ys6_hangul_codec import encode_translation, normalize_game_punctuation
    from ys6_translation_workspace import validate
    from ys6_xso import parse_xso, rebuild_xso

def build(input_xso: Path, iso_path: str, workspace: dict, mapping: list[dict]) -> tuple[bytes, dict]:
    validation=validate(workspace)
    if not validation["valid"]: raise ValueError("invalid workspace: " + "; ".join(validation["errors"]))
    parsed=parse_xso(input_xso); selected=[r for r in workspace["records"] if r["iso_path"]==iso_path and r["status"]=="reviewed"]
    if not selected: raise ValueError("no reviewed translations for ISO path")
    replacements={}
    for record in selected:
        index=int(record["string_index"])
        if not 0 <= index < len(parsed.strings): raise ValueError(f"string index out of range: {index}")
        entry=parsed.strings[index]
        if hashlib.sha256(bytes.fromhex(entry.raw_hex)).hexdigest().upper()!=record["source_sha256"]: raise ValueError(f"source mismatch at index {index}")
        if index in replacements: raise ValueError(f"duplicate replacement index: {index}")
        replacements[index]=encode_translation(record["translation"],mapping)
    _,rebuilt=rebuild_xso(input_xso,replacements,allow_length_change=True)
    output_path=input_xso.parent/".__verify.xso"; output_path.write_bytes(rebuilt)
    try: reparsed=parse_xso(output_path)
    finally: output_path.unlink(missing_ok=True)
    rows=[]
    for index,replacement in sorted(replacements.items()):
        if bytes.fromhex(reparsed.strings[index].raw_hex)!=replacement: raise ValueError(f"replacement verification failed: {index}")
        source_record = next(record for record in selected if int(record["string_index"]) == index)
        rows.append({"string_index":index,"translation":source_record["translation"],"normalized_translation":normalize_game_punctuation(source_record["translation"]),"original_length":parsed.strings[index].byte_length,"replacement_length":len(replacement),"delta":len(replacement)-parsed.strings[index].byte_length,"replacement_hex":replacement.hex().upper()})
    return rebuilt,{"iso_path":iso_path,"replacement_count":len(rows),"original_size":input_xso.stat().st_size,"output_size":len(rebuilt),"total_delta":len(rebuilt)-input_xso.stat().st_size,"replacements":rows,"output_sha256":hashlib.sha256(rebuilt).hexdigest().upper(),"valid":True}

def main():
    p=argparse.ArgumentParser(); p.add_argument("input_xso",type=Path); p.add_argument("iso_path"); p.add_argument("workspace",type=Path); p.add_argument("mapping",type=Path); p.add_argument("output_xso",type=Path); p.add_argument("--report",type=Path); p.add_argument("--overwrite",action="store_true"); a=p.parse_args()
    if a.output_xso.exists() and not a.overwrite: raise FileExistsError(a.output_xso)
    workspace=json.loads(a.workspace.read_text(encoding="utf-8-sig")); mapping=json.loads(a.mapping.read_text(encoding="utf-8-sig"))["mappings"]
    rebuilt,report=build(a.input_xso,a.iso_path,workspace,mapping); a.output_xso.parent.mkdir(parents=True,exist_ok=True); a.output_xso.write_bytes(rebuilt)
    rendered=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if a.report: a.report.write_text(rendered,encoding="utf-8")
    print(rendered,end=""); return 0
if __name__=="__main__": sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace"); raise SystemExit(main())
