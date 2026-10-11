#!/usr/bin/env python3
"""Catalog SPECIAL VERSION IDM resources and resolve existing Korean translations."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
try:
 from tools.scripts.iso9660_info import SECTOR_SIZE
 from tools.scripts.ys6_arc import parse_archive
 from tools.scripts.ys6_idm import parse_idm,rebuild_idm,sha256
except ModuleNotFoundError:
 from iso9660_info import SECTOR_SIZE
 from ys6_arc import parse_archive
 from ys6_idm import parse_idm,rebuild_idm,sha256

ISO_SHA256="C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9"
def file_sha(path):
 d=hashlib.sha256()
 with path.open("rb") as f:
  while c:=f.read(1024*1024):d.update(c)
 return d.hexdigest().upper()
def rows(path):
 with path.open("r",encoding="utf-8-sig",newline="") as f:return {r["path"].casefold():r for r in csv.DictReader(f)}
def read_at(handle,row):handle.seek(int(row["second_lba"])*SECTOR_SIZE);return handle.read(int(row["second_size"]))
def map_id(path):return Path(path).parent.name
def catalog(iso,inventory,workspace_path,mapping_path,output):
 if file_sha(iso)!=ISO_SHA256:raise ValueError("SPECIAL VERSION ISO SHA-256 mismatch")
 output.mkdir(parents=True,exist_ok=True);inv=rows(inventory);workspace=json.loads(workspace_path.read_text(encoding="utf-8-sig"));mapping_doc=json.loads(mapping_path.read_text(encoding="utf-8-sig"));mapping=mapping_doc["mappings"]
 idm_rows=[r for r in inv.values() if r["second_size"] and r["path"].lower().startswith("psp_game/usrdir/data/idm/") and r["path"].lower().endswith("/s_scene.idm")]
 files=[];by_map={};runtime=[];failures=[]
 with iso.open("rb") as handle:
  for row in sorted(idm_rows,key=lambda x:x["path"]):
   data=read_at(handle,row)
   try:
    parsed=parse_idm(data);rebuilt=rebuild_idm(parsed)
    if rebuilt!=data:raise ValueError("non-identical no-op rebuild")
   except Exception as exc:failures.append({"iso_path":row["path"],"error":str(exc)});continue
   mid=map_id(row["path"]);entry={"map_id":mid,"iso_path":row["path"],"size":len(data),"sha256":sha256(data),"record_count":parsed["count"],"string_count":len(parsed["strings"]),"strings":[{k:s[k] for k in ("flat_index","record_index","record_id","string_index","raw_hex","text","sha256")} for s in parsed["strings"]]};files.append(entry);by_map[mid]=(entry,parsed,data)
   arc_key=f"psp_game/usrdir/data/arc/{mid}.bin".casefold();arc_row=inv.get(arc_key)
   copies=[]
   if arc_row:
    arc=read_at(handle,arc_row)
    try:
     entries=parse_archive(arc);data_entries=sorted((e for e in entries if e.offset and e.size),key=lambda e:e.offset)
     for pos,e in enumerate(data_entries):
      if e.name!="s_scene.idm":continue
      blob=arc[e.offset:e.offset+e.size]
      if blob==data:
       allocated=(data_entries[pos+1].offset if pos+1<len(data_entries) else len(arc))-e.offset;copies.append({"archive_path":arc_row["path"],"entry_index":e.index,"entry_name":e.name,"flags_hex":f"0x{e.flags:08X}","size":e.size,"allocated_size":allocated,"sha256":sha256(blob)})
    except Exception as exc:failures.append({"iso_path":arc_row["path"],"error":str(exc)})
   runtime.append({"map_id":mid,"iso_path":row["path"],"standalone_allocated_size":math.ceil(len(data)/SECTOR_SIZE)*SECTOR_SIZE,"copies":copies})
 old_by_file=defaultdict(dict)
 for r in workspace["records"]:old_by_file[r["iso_path"]][int(r["string_index"])]=r
 resolved=[];ambiguous=[];unmatched=[]
 for source_path,indexed in old_by_file.items():
  mid=Path(source_path).parent.name;target=by_map.get(mid)
  if not target:
   for r in indexed.values():
    if r.get("status")=="override":unmatched.append({"source_iso_path":source_path,"string_index":int(r["string_index"]),"reason":"target_map_absent"})
   continue
  entry,parsed,_data=target;raw_hits=defaultdict(list)
  for s in parsed["strings"]:raw_hits[s["raw_hex"]].append(s)
  ordered=sorted(indexed)
  for old_index in ordered:
   r=indexed[old_index]
   if r.get("status")!="override":continue
   hits=raw_hits.get(r["source_raw_hex"].upper(),[])
   method="unique_raw" if len(hits)==1 else ""
   if len(hits)>1:
    scored=[]
    for h in hits:
     score=0
     for delta in (-1,1):
      neighbor=indexed.get(old_index+delta);target_i=h["flat_index"]+delta
      if neighbor and 0<=target_i<len(parsed["strings"]) and neighbor["source_raw_hex"].upper()==parsed["strings"][target_i]["raw_hex"]:score+=1
     scored.append((score,h))
    best=max((x[0] for x in scored),default=0);winners=[h for score,h in scored if score==best]
    if best>0 and len(winners)==1:hits=winners;method="neighbor_context"
   if len(hits)==1 and method:
    h=hits[0];resolved.append({"map_id":mid,"source_iso_path":source_path,"source_string_index":old_index,"target_iso_path":entry["iso_path"],"target_flat_index":h["flat_index"],"target_record_index":h["record_index"],"target_record_id":h["record_id"],"target_string_index":h["string_index"],"source_text":r["source_text"],"source_raw_hex":r["source_raw_hex"],"translation":r["translation"],"method":method,"status":"override"})
   elif hits:ambiguous.append({"source_iso_path":source_path,"string_index":old_index,"map_id":mid,"hit_count":len(hits),"reason":"ambiguous_raw_context"})
   else:unmatched.append({"source_iso_path":source_path,"string_index":old_index,"map_id":mid,"reason":"raw_not_found"})
 conflicts=[];by_target=defaultdict(list)
 for r in resolved:by_target[(r["target_iso_path"],r["target_flat_index"])].append(r)
 final=[]
 for key,group in by_target.items():
  translations={r["translation"] for r in group}
  if len(translations)>1:conflicts.append({"target_iso_path":key[0],"target_flat_index":key[1],"translations":sorted(translations),"source_count":len(group)})
  else:final.append(group[0])
 mapped={r["character"] for r in mapping};needed=sorted({c for r in final for c in r["translation"] if "가"<=c<="힣" and c not in mapped},key=ord)
 selected=[];selected_new=set();deferred=[]
 for r in sorted(final,key=lambda x:(x["map_id"],x["target_flat_index"],x["source_iso_path"],x["source_string_index"])):
  add={c for c in r["translation"] if "가"<=c<="힣" and c not in mapped and c not in selected_new}
  if len(selected_new|add)<=95:selected.append(r);selected_new|=add
  else:deferred.append({**r,"defer_reason":"safe_glyph_capacity"})
 document={"schema_version":1,"profile":"ULJM-05155","source":{"iso_sha256":ISO_SHA256,"workspace_sha256":file_sha(workspace_path),"mapping_sha256":file_sha(mapping_path)},"summary":{"idm_file_count":len(files),"parse_failure_count":len(failures),"record_count":sum(f["record_count"] for f in files),"string_count":sum(f["string_count"] for f in files),"runtime_copy_count":sum(len(r["copies"]) for r in runtime),"resolved_count":len(final),"ambiguous_count":len(ambiguous),"unmatched_count":len(unmatched),"conflict_count":len(conflicts),"required_new_glyph_count":len(needed),"capacity_selected_count":len(selected),"capacity_selected_new_glyph_count":len(selected_new),"capacity_deferred_count":len(deferred)},"records":selected}
 (output/"idm-catalog.json").write_text(json.dumps({"schema_version":1,"profile":"ULJM-05155","files":files},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (output/"runtime-map.json").write_text(json.dumps({"schema_version":1,"profile":"ULJM-05155","resources":runtime},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (output/"idm-translations.json").write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (output/"resolution-report.json").write_text(json.dumps({"summary":document["summary"],"failures":failures,"ambiguous":ambiguous,"unmatched":unmatched,"conflicts":conflicts,"all_resolved":final,"capacity_deferred":deferred,"required_new_glyphs":needed,"selected_new_glyphs":sorted(selected_new,key=ord)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return document["summary"]
def main():
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser();p.add_argument("iso",type=Path);p.add_argument("inventory",type=Path);p.add_argument("workspace",type=Path);p.add_argument("mapping",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
 try:print(json.dumps(catalog(a.iso,a.inventory,a.workspace,a.mapping,a.output),ensure_ascii=False,indent=2));return 0
 except Exception as exc:print(f"SPECIAL VERSION IDM 조사 실패: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
