#!/usr/bin/env python3
"""Trace standalone-only Ys VI XSO files to static runtime candidates."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
try:
 from tools.scripts.iso9660_info import PVD_SECTOR,SECTOR_SIZE,parse_record
 from tools.scripts.ys6_iso_z_search import iter_files
 from tools.scripts.ys6_arc import parse_archive
 from tools.scripts.ys6_translation_workspace import validate
 from tools.scripts.ys6_xso import HEADER_SIZE,parse_xso
except ModuleNotFoundError:
 from iso9660_info import PVD_SECTOR,SECTOR_SIZE,parse_record
 from ys6_iso_z_search import iter_files
 from ys6_arc import parse_archive
 from ys6_translation_workspace import validate
 from ys6_xso import HEADER_SIZE,parse_xso

EXPECTED_ISO_SHA256="0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B"
EXPECTED_TARGET_XSO=21;EXPECTED_TRANSLATIONS=35
class TraceError(Exception):pass
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def file_sha(path):
 d=hashlib.sha256()
 with path.open("rb") as f:
  while c:=f.read(1024*1024):d.update(c)
 return d.hexdigest().upper()
def clean_iso_path(path):return "/".join(x.split(";",1)[0] for x in path.replace("\\","/").split("/"))
def compressed_path(root,iso_path):return root/Path(*iso_path.split("/"))
def decompressed_path(root,iso_path):return root/Path(*iso_path[:-2].split("/"))

def select_targets(workspace,catalog,runtime_map):
 validation=validate(workspace)
 if not validation["valid"]:raise TraceError("invalid workspace: "+"; ".join(validation["errors"]))
 files={x["iso_path"]:x for x in catalog["files"]};maps={x["xso_sha256"]:x for x in runtime_map["mappings"]};groups=defaultdict(list)
 for r in workspace["records"]:
  if not r.get("translation"):continue
  f=files.get(r["iso_path"]);m=maps.get(f["xso_sha256"]) if f else None
  if m and m["status"]=="standalone_only":groups[r["iso_path"]].append(r)
 targets=[]
 for path,records in sorted(groups.items()):
  f=files[path];targets.append({"iso_path":path,"map_group":f.get("map_group",""),"map_id":f.get("map_id",""),"xso_name":f.get("xso_name",""),"compressed_size":f["compressed_size"],"xso_size":f["decompressed_size"],"compressed_sha256":f["compressed_sha256"],"xso_sha256":f["xso_sha256"],"string_count":f["string_count"],"command_count":f["command_count"],"translations":[{"string_index":int(r["string_index"]),"roles":r.get("roles",[]),"source_text":r["source_text"],"source_raw_hex":r["source_raw_hex"],"source_sha256":r["source_sha256"],"translation":r["translation"],"status":r["status"]} for r in sorted(records,key=lambda x:int(x["string_index"]))]})
 return targets

def iso_inventory(iso):
 rows=[]
 with iso.open("rb") as f:
  f.seek(PVD_SECTOR*SECTOR_SIZE);pvd=f.read(SECTOR_SIZE);root=parse_record(pvd,156,PVD_SECTOR*SECTOR_SIZE)
  for path,rec in iter_files(f,root):
   f.seek(rec.extent_lba*SECTOR_SIZE);data=f.read(rec.data_length);clean=clean_iso_path(path)
   rows.append({"iso_path":clean,"extent_lba":rec.extent_lba,"byte_offset":rec.extent_lba*SECTOR_SIZE,"file_size":rec.data_length,"sha256":sha(data),"extension":Path(clean).suffix.lower()})
 return sorted(rows,key=lambda x:x["iso_path"].casefold())

def find_all(blob,needle):
 out=[];start=0
 if not needle:return out
 while True:
  pos=blob.find(needle,start)
  if pos<0:return out
  out.append(pos);start=pos+1

def code_hash(path):
 data=path.read_bytes();parsed=parse_xso(path);end=HEADER_SIZE+parsed.info.code_word_count*4
 return sha(data[HEADER_SIZE:end])

def auxiliary_arc_entries(iso,inventory,target_hashes):
 rows=[]
 by_path={x["iso_path"]:x for x in inventory}
 with iso.open("rb") as f:
  for item in inventory:
   if not item["iso_path"].lower().startswith("psp_game/usrdir/data/arc/") or not item["iso_path"].lower().endswith(".bin"):continue
   f.seek(item["byte_offset"]);data=f.read(item["file_size"]);entries=parse_archive(data)
   data_entries=sorted((e for e in entries if e.offset>0 and e.size>0),key=lambda e:e.offset)
   next_offset={e.index:(data_entries[i+1].offset if i+1<len(data_entries) else len(data)) for i,e in enumerate(data_entries)}
   for e in data_entries:
    if e.flags!=0x41000000 or not e.name.lower().endswith(".xso.z"):continue
    container=data[e.offset:e.offset+e.size]
    target=next((digest for digest,compressed_hash in target_hashes.items() if sha(container)==compressed_hash),None)
    rows.append({"archive_iso_path":item["iso_path"],"entry_index":e.index,"entry_name":e.name,"flags_hex":f"0x{e.flags:08X}","data_offset":e.offset,"compressed_size":e.size,"allocated_size":next_offset[e.index]-e.offset,"slack_size":next_offset[e.index]-e.offset-e.size,"container_sha256":sha(container),"matched_target_xso_sha256":target or ""})
 return rows

def build(catalog_root,decompressed_root,iso,workspace,catalog,runtime_map):
 targets=select_targets(workspace,catalog,runtime_map)
 if len(targets)!=EXPECTED_TARGET_XSO or sum(len(x["translations"]) for x in targets)!=EXPECTED_TRANSLATIONS:raise TraceError(f"target count changed: xso={len(targets)}, translations={sum(len(x['translations']) for x in targets)}")
 inventory=iso_inventory(iso);iso_blob=iso.read_bytes();by_name=defaultdict(list)
 for f in catalog["files"]:by_name[f["xso_name"].casefold()].append(f)
 exact=[];names=[];structural=[];target_results=[]
 for target in targets:
  cp=compressed_path(catalog_root,target["iso_path"]);dp=decompressed_path(decompressed_root,target["iso_path"])
  if not cp.exists() or not dp.exists():raise TraceError(f"catalog source missing: {target['iso_path']}")
  container=cp.read_bytes();payload=dp.read_bytes()
  if sha(container)!=target["compressed_sha256"] or sha(payload)!=target["xso_sha256"]:raise TraceError(f"catalog source hash mismatch: {target['iso_path']}")
  target_code=code_hash(dp);hit_kinds=defaultdict(list)
  patterns=[("compressed",container),("payload",payload)]
  unique_strings=[]
  for tr in target["translations"]:
   raw=bytes.fromhex(tr["source_raw_hex"])
   if len(raw)>=4 and raw not in unique_strings:unique_strings.append(raw)
  patterns += [("source_string",x) for x in unique_strings]
  for kind,needle in patterns:
   for pos in find_all(iso_blob,needle):
    owner=next((x for x in inventory if x["byte_offset"]<=pos<x["byte_offset"]+x["file_size"]),None)
    row={"target_iso_path":target["iso_path"],"kind":kind,"absolute_offset":pos,"owner_iso_path":owner["iso_path"] if owner else "","owner_relative_offset":pos-owner["byte_offset"] if owner else None,"needle_size":len(needle)};exact.append(row);hit_kinds[kind].append(row)
  basename=Path(target["iso_path"]).name.casefold()
  for item in inventory:
   if Path(item["iso_path"]).name.casefold()==basename:names.append({"target_iso_path":target["iso_path"],"candidate_kind":"iso_file","candidate_path":item["iso_path"],"same_path":item["iso_path"].casefold()==target["iso_path"].casefold()})
  candidates=by_name[target["xso_name"].casefold()]
  for candidate in candidates:
   cdp=decompressed_path(decompressed_root,candidate["iso_path"])
   if not cdp.exists():continue
   parsed=parse_xso(cdp);candidate_strings={s.text for s in parsed.strings};source_texts={tr["source_text"] for tr in target["translations"]};intersection=sorted(source_texts&candidate_strings)
   row={"target_iso_path":target["iso_path"],"candidate_iso_path":candidate["iso_path"],"same_xso_sha256":candidate["xso_sha256"]==target["xso_sha256"],"same_code_sha256":code_hash(cdp)==target_code,"target_string_count":target["string_count"],"candidate_string_count":candidate["string_count"],"translated_source_match_count":len(intersection),"translated_source_count":len(source_texts),"translated_source_matches":" | ".join(intersection)};structural.append(row)
  hidden=[x for x in hit_kinds["compressed"]+hit_kinds["payload"] if x["owner_iso_path"].casefold()!=target["iso_path"].casefold()]
  if hidden:status="embedded_exact"
  elif any(x["same_code_sha256"] and x["translated_source_match_count"] for x in structural if x["target_iso_path"]==target["iso_path"] and x["candidate_iso_path"]!=target["iso_path"]):status="embedded_variant"
  elif hit_kinds["compressed"] or hit_kinds["payload"]:status="direct_standalone_candidate"
  elif hit_kinds["source_string"]:status="reference_only"
  else:status="no_static_evidence"
  target_results.append({**target,"code_sha256":target_code,"static_status":status,"compressed_hit_count":len(hit_kinds["compressed"]),"payload_hit_count":len(hit_kinds["payload"]),"source_string_hit_count":len(hit_kinds["source_string"]),"requires_runtime_trace":status not in {"embedded_exact"}})
 auxiliary=auxiliary_arc_entries(iso,inventory,{x["xso_sha256"]:x["compressed_sha256"] for x in targets})
 return targets,inventory,exact,names,structural,auxiliary,target_results

def write_csv(path,rows,fields):
 with path.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
def main(argv=None):
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("iso",type=Path);p.add_argument("workspace",type=Path);p.add_argument("catalog",type=Path);p.add_argument("runtime_map",type=Path);p.add_argument("compressed_root",type=Path);p.add_argument("decompressed_root",type=Path);p.add_argument("output",type=Path);p.add_argument("--overwrite",action="store_true");a=p.parse_args(argv)
 out=a.output/"runtime-path-map.json"
 if out.exists() and not a.overwrite:print(f"출력 파일이 이미 존재합니다: {out}",file=sys.stderr);return 2
 try:
  if file_sha(a.iso)!=EXPECTED_ISO_SHA256:raise TraceError("original ISO SHA-256 mismatch")
  w=json.loads(a.workspace.read_text(encoding="utf-8-sig"));c=json.loads(a.catalog.read_text(encoding="utf-8-sig"));m=json.loads(a.runtime_map.read_text(encoding="utf-8-sig"));a.output.mkdir(parents=True,exist_ok=True)
  targets,inventory,exact,names,structural,auxiliary,results=build(a.compressed_root,a.decompressed_root,a.iso,w,c,m)
  summary={"target_xso_count":len(targets),"translation_count":sum(len(x["translations"]) for x in targets),"iso_file_count":len(inventory),"exact_hit_count":len(exact),"name_candidate_count":len(names),"structural_candidate_count":len(structural),"auxiliary_arc_xso_count":len(auxiliary),"matched_auxiliary_target_count":sum(bool(x["matched_target_xso_sha256"]) for x in auxiliary),"status_counts":dict(sorted(__import__('collections').Counter(x["static_status"] for x in results).items()))}
  document={"schema_version":1,"source":{"iso":str(a.iso),"iso_sha256":EXPECTED_ISO_SHA256,"workspace_sha256":file_sha(a.workspace),"catalog_sha256":file_sha(a.catalog),"runtime_map_sha256":file_sha(a.runtime_map)},"summary":summary,"targets":results}
  (a.output/"targets.json").write_text(json.dumps({"schema_version":1,"targets":targets},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  out.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  write_csv(a.output/"iso-files.csv",inventory,["iso_path","extent_lba","byte_offset","file_size","sha256","extension"])
  write_csv(a.output/"exact-hits.csv",exact,["target_iso_path","kind","absolute_offset","owner_iso_path","owner_relative_offset","needle_size"])
  write_csv(a.output/"name-candidates.csv",names,["target_iso_path","candidate_kind","candidate_path","same_path"])
  write_csv(a.output/"structural-candidates.csv",structural,["target_iso_path","candidate_iso_path","same_xso_sha256","same_code_sha256","target_string_count","candidate_string_count","translated_source_match_count","translated_source_count","translated_source_matches"])
  write_csv(a.output/"auxiliary-arc-xso.csv",auxiliary,["archive_iso_path","entry_index","entry_name","flags_hex","data_offset","compressed_size","allocated_size","slack_size","container_sha256","matched_target_xso_sha256"])
  lines=["# standalone-only XSO 정적 조사 요약",""]+[f"- {k}: {v}" for k,v in summary.items() if k!="status_counts"]+["","## 상태",""]+[f"- {k}: {v}" for k,v in summary["status_counts"].items()]
  (a.output/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8");print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
 except (OSError,KeyError,ValueError,json.JSONDecodeError,TraceError) as exc:print(f"standalone 런타임 조사 실패: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
