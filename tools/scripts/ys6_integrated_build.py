#!/usr/bin/env python3
"""Preflight and build reviewed Ys VI translations across runtime archives."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys,tempfile
from collections import defaultdict
from pathlib import Path
try:
    from tools.scripts.iso9660_info import SECTOR_SIZE,find_record
    from tools.scripts.ys6_arc import find_file,parse_archive,replace_file
    from tools.scripts.ys6_hangul_codec import encode_translation,extend_mapping,write_mapping
    from tools.scripts.ys6_hangul_font_build import build as build_font
    from tools.scripts.ys6_iso_multi_patch import Replacement,patch_atomic
    from tools.scripts.ys6_translation_workspace import validate
    from tools.scripts.ys6_xso import parse_xso,rebuild_xso
    from tools.scripts.ys6_z import build_container,verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE,find_record
    from ys6_arc import find_file,parse_archive,replace_file
    from ys6_hangul_codec import encode_translation,extend_mapping,write_mapping
    from ys6_hangul_font_build import build as build_font
    from ys6_iso_multi_patch import Replacement,patch_atomic
    from ys6_translation_workspace import validate
    from ys6_xso import parse_xso,rebuild_xso
    from ys6_z import build_container,verify_container_bytes

EXPECTED_ISO_SHA256="0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B"
EBOOT_PATH="PSP_GAME/SYSDIR/EBOOT.BIN"
EBOOT_ORIGINAL_SHA256="EB20970858EC420FB1E068C38DFF5765CD3C99FC624266E2989DAC92E39108E5"

class IntegratedBuildError(Exception): pass
def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest().upper()
def file_sha256(path:Path)->str:
 d=hashlib.sha256()
 with path.open("rb") as f:
  while c:=f.read(1024*1024):d.update(c)
 return d.hexdigest().upper()

def select_reviewed(workspace:dict)->list[dict]:
 report=validate(workspace)
 if not report["valid"]:raise IntegratedBuildError("invalid workspace: "+"; ".join(report["errors"]))
 selected=[dict(x) for x in workspace["records"] if x["status"]=="reviewed"]
 if not selected:raise IntegratedBuildError("reviewed translation is empty")
 return selected

def group_translations(records:list[dict],catalog:dict,runtime_map:dict)->list[dict]:
 files={x["iso_path"]:x for x in catalog["files"]}; mapping_by_hash={x["xso_sha256"]:x for x in runtime_map["mappings"]}; grouped=defaultdict(list)
 for record in records:
  source=files.get(record["iso_path"])
  if not source:raise IntegratedBuildError(f"catalog path missing: {record['iso_path']}")
  grouped[source["xso_sha256"]].append(record)
 result=[]
 for digest,items in sorted(grouped.items()):
  mapping=mapping_by_hash.get(digest)
  if not mapping or mapping["status"] not in {"exact_one_to_one","standalone_duplicate"} or len(mapping["runtime_keys"])!=1:
   raise IntegratedBuildError(f"unsupported runtime mapping: {digest}")
  merged={}; origins=defaultdict(list)
  for item in items:
   index=int(item["string_index"])
   if index in merged and merged[index]["translation"]!=item["translation"]:
    raise IntegratedBuildError(f"shared payload translation conflict: {digest} index={index}")
   merged[index]=item; origins[index].append(item["iso_path"])
  result.append({"xso_sha256":digest,"mapping_status":mapping["status"],"standalone_paths":mapping["standalone_paths"],"runtime_key":mapping["runtime_keys"][0],"records":[{**merged[i],"origin_paths":sorted(set(origins[i]))} for i in sorted(merged)]})
 return result

def read_iso_file(iso:Path,internal_path:str)->tuple[bytes,object]:
 record=find_record(iso,internal_path)
 with iso.open("rb") as f:f.seek(record.extent_lba*SECTOR_SIZE);data=f.read(record.data_length)
 return data,record

def build_mapping(groups:list[dict],usage:dict,seed:list[dict])->list[dict]:
 text="".join(r["translation"] for g in groups for r in g["records"])
 hangul="".join(dict.fromkeys(c for c in text if "가"<=c<="힣"))
 return extend_mapping(usage,seed,hangul)

def rebuild_group(original:bytes,group:dict,mapping:list[dict],temp:Path)->tuple[bytes,dict,list[dict]]:
 source=temp/"source.xso";source.write_bytes(original);parsed=parse_xso(source); replacements={};rows=[]
 for record in group["records"]:
  index=int(record["string_index"])
  if not 0<=index<len(parsed.strings):raise IntegratedBuildError(f"string index out of range: {index}")
  entry=parsed.strings[index]
  if hashlib.sha256(bytes.fromhex(entry.raw_hex)).hexdigest().upper()!=record["source_sha256"]:raise IntegratedBuildError(f"source mismatch: {group['xso_sha256']} index={index}")
  encoded=encode_translation(record["translation"],mapping);replacements[index]=encoded
  rows.append({"xso_sha256":group["xso_sha256"],"runtime_key":group["runtime_key"],"string_index":index,"source_text":record["source_text"],"translation":record["translation"],"original_length":entry.byte_length,"replacement_length":len(encoded),"delta":len(encoded)-entry.byte_length,"origin_paths":" | ".join(record["origin_paths"])})
 _report,rebuilt=rebuild_xso(source,replacements,allow_length_change=True);check=temp/"check.xso";check.write_bytes(rebuilt);reparsed=parse_xso(check)
 for index,value in replacements.items():
  if bytes.fromhex(reparsed.strings[index].raw_hex)!=value:raise IntegratedBuildError(f"replacement verification failed: {index}")
 return rebuilt,{"original_size":len(original),"rebuilt_size":len(rebuilt),"original_sha256":sha256(original),"rebuilt_sha256":sha256(rebuilt),"replacement_count":len(replacements)},rows

def write_csv(path:Path,rows:list[dict],fields:list[str]):
 with path.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

def execute(args)->dict:
 iso=args.iso; workspace=json.loads(args.workspace.read_text(encoding="utf-8-sig"));catalog=json.loads(args.catalog.read_text(encoding="utf-8-sig"));runtime_map=json.loads(args.runtime_map.read_text(encoding="utf-8-sig"));usage=json.loads(args.font_usage.read_text(encoding="utf-8-sig"));seed=json.loads(args.seed_mapping.read_text(encoding="utf-8-sig"))["mappings"]
 if int(runtime_map.get("schema_version",0))<2:raise IntegratedBuildError("runtime map schema v2 or newer is required")
 if file_sha256(iso)!=EXPECTED_ISO_SHA256:raise IntegratedBuildError("original ISO SHA-256 mismatch")
 if file_sha256(args.original_eboot)!=EBOOT_ORIGINAL_SHA256:raise IntegratedBuildError("decrypted original EBOOT SHA-256 mismatch")
 selected=select_reviewed(workspace);groups=group_translations(selected,catalog,runtime_map); runtime={x["runtime_key"]:x for x in runtime_map["runtime_entries"]};mapping=build_mapping(groups,usage,seed)
 args.work.mkdir(parents=True,exist_ok=True);(args.work/"xso").mkdir(exist_ok=True);(args.work/"archives").mkdir(exist_ok=True)
 write_mapping(mapping,args.work/"mapping.json",args.work/"mapping.csv")
 eboot_data=args.original_eboot.read_bytes();overrides={"한":args.han_override};patched_eboot,glyph_report,atlas=build_font(eboot_data,mapping,args.font,12,overrides,horizontal_left_inset=args.horizontal_left_inset);(args.work/"EBOOT.BIN").write_bytes(patched_eboot);(args.work/"glyph-report.json").write_text(json.dumps({"visible_width":12,"horizontal_left_inset":args.horizontal_left_inset,"glyphs":glyph_report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8");atlas.resize((atlas.width*8,atlas.height*8)).save(args.work/"glyph-atlas.png")
 archive_cache={};archive_original={};xso_rows=[];translation_rows=[];overflow=[];rebuilt_containers={}
 with tempfile.TemporaryDirectory(dir=args.work) as td:
  temp=Path(td)
  for number,group in enumerate(groups):
   meta=runtime[group["runtime_key"]];arc_path=meta["archive_iso_path"]
   if arc_path not in archive_cache:
    data,_=read_iso_file(iso,arc_path);archive_cache[arc_path]=data;archive_original[arc_path]=data
   current=archive_cache[arc_path];entry=find_file(parse_archive(current),meta["entry_name"],index=int(meta["entry_index"]),flags=int(meta["flags_hex"],0));container=current[entry.offset:entry.offset+entry.size];valid,payload,error=verify_container_bytes(container)
   if not valid or payload is None or sha256(payload)!=group["xso_sha256"]:raise IntegratedBuildError(f"runtime payload mismatch: {group['runtime_key']} {error or ''}")
   group_temp=temp/f"g{number}";group_temp.mkdir();rebuilt,report,rows=rebuild_group(payload,group,mapping,group_temp);compressed=build_container(rebuilt,9);valid,roundtrip,error=verify_container_bytes(compressed)
   if not valid or roundtrip!=rebuilt:raise IntegratedBuildError(f"compression verification failed: {error}")
   remaining=entry.allocated_size-len(compressed)
   xso_path=args.work/"xso"/(group["xso_sha256"]+".xso");z_path=xso_path.with_suffix(".xso.z");xso_path.write_bytes(rebuilt);z_path.write_bytes(compressed)
   rebuilt_containers[group["xso_sha256"]]=(group,compressed)
   xso_rows.append({"xso_sha256":group["xso_sha256"],"runtime_key":group["runtime_key"],"entry_flags_hex":f"0x{entry.flags:08X}","entry_kind":meta.get("entry_kind","regular"),**report,"compressed_size":len(compressed),"allocated_size":entry.allocated_size,"remaining_slack":remaining,"mapping_status":group["mapping_status"]})
   translation_rows+=rows
   if remaining<0:overflow.append({"runtime_key":group["runtime_key"],"compressed_size":len(compressed),"allocated_size":entry.allocated_size,"overflow":-remaining})
   else:archive_cache[arc_path]=replace_file(current,entry,compressed)
 standalone_rows=[];standalone_replacements=[]
 for standalone_path in args.standalone_path:
  matches=[(group,container) for group,container in rebuilt_containers.values() if standalone_path in group["standalone_paths"]]
  if len(matches)!=1:raise IntegratedBuildError(f"standalone path is not uniquely associated with a rebuilt group: {standalone_path}")
  group,container=matches[0];original,record=read_iso_file(iso,standalone_path);valid,payload,error=verify_container_bytes(original)
  if not valid or payload is None or sha256(payload)!=group["xso_sha256"]:raise IntegratedBuildError(f"standalone payload mismatch: {standalone_path} {error or ''}")
  allocated=((record.data_length+SECTOR_SIZE-1)//SECTOR_SIZE)*SECTOR_SIZE;remaining=allocated-len(container)
  standalone_rows.append({"iso_path":standalone_path,"runtime_key":group["runtime_key"],"original_size":len(original),"compressed_size":len(container),"allocated_size":allocated,"remaining_slack":remaining,"original_sha256":sha256(original),"output_sha256":sha256(container)})
  if remaining<0:overflow.append({"runtime_key":standalone_path,"compressed_size":len(container),"allocated_size":allocated,"overflow":-remaining})
  else:standalone_replacements.append(Replacement(standalone_path,args.work/"xso"/(group["xso_sha256"]+".xso.z"),len(original),sha256(original)))
 if overflow:
  preflight={"valid":False,"reason":"allocation_overflow","overflow":overflow,"reviewed_count":len(selected),"xso_count":len(groups)};(args.work/"preflight-report.json").write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");raise IntegratedBuildError("allocation overflow: "+json.dumps(overflow,ensure_ascii=False))
 archive_rows=[];iso_replacements=[]
 for arc_path,data in sorted(archive_cache.items()):
  name=Path(arc_path).name;out=args.work/"archives"/name;out.write_bytes(data);original=archive_original[arc_path];archive_rows.append({"iso_path":arc_path,"original_sha256":sha256(original),"output_sha256":sha256(data),"size":len(data),"modified_xso_count":sum(x["runtime_key"].startswith(arc_path+"#") for x in xso_rows)})
  iso_replacements.append(Replacement(arc_path,out,len(original),sha256(original)))
 iso_replacements.extend(standalone_replacements)
 original_iso_eboot,eboot_record=read_iso_file(iso,EBOOT_PATH);iso_replacements.insert(0,Replacement(EBOOT_PATH,args.work/"EBOOT.BIN",len(original_iso_eboot),sha256(original_iso_eboot)))
 expected_replacement_count=1+len(archive_rows)+len(standalone_rows)
 if len(iso_replacements)!=expected_replacement_count:raise IntegratedBuildError(f"ISO replacement count mismatch: expected={expected_replacement_count}, actual={len(iso_replacements)}")
 preflight={"valid":True,"reviewed_count":len(selected),"xso_count":len(groups),"archive_count":len(archive_rows),"standalone_count":len(standalone_rows),"glyph_count":len(mapping),"overflow":[]};(args.work/"preflight-report.json").write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 write_csv(args.work/"translation-report.csv",translation_rows,["xso_sha256","runtime_key","string_index","source_text","translation","original_length","replacement_length","delta","origin_paths"]);write_csv(args.work/"xso-report.csv",xso_rows,["xso_sha256","runtime_key","entry_flags_hex","entry_kind","mapping_status","replacement_count","original_size","rebuilt_size","compressed_size","allocated_size","remaining_slack","original_sha256","rebuilt_sha256"]);write_csv(args.work/"archive-report.csv",archive_rows,["iso_path","size","modified_xso_count","original_sha256","output_sha256"])
 write_csv(args.work/"standalone-report.csv",standalone_rows,["iso_path","runtime_key","original_size","compressed_size","allocated_size","remaining_slack","original_sha256","output_sha256"])
 manifest={"schema_version":1,"mode":args.mode,"inputs":{"iso":str(iso),"iso_sha256":EXPECTED_ISO_SHA256,"workspace":str(args.workspace),"workspace_sha256":file_sha256(args.workspace),"catalog_sha256":file_sha256(args.catalog),"runtime_map_sha256":file_sha256(args.runtime_map),"original_eboot_sha256":file_sha256(args.original_eboot),"seed_mapping_sha256":file_sha256(args.seed_mapping)},"font":{"visible_width":12,"horizontal_left_inset":args.horizontal_left_inset},"summary":preflight,"eboot":{"sha256":sha256(patched_eboot)},"xso":xso_rows,"archives":archive_rows,"iso":None,"valid":True}
 if args.mode=="build":
  result=patch_atomic(iso,args.output_iso,iso_replacements,EXPECTED_ISO_SHA256,args.overwrite);manifest["iso"]={"path":str(args.output_iso),**result}
 (args.work/"build-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return manifest

def main(argv=None):
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=("preflight","build"));p.add_argument("--iso",type=Path,required=True);p.add_argument("--workspace",type=Path,required=True);p.add_argument("--catalog",type=Path,required=True);p.add_argument("--runtime-map",type=Path,required=True);p.add_argument("--font-usage",type=Path,required=True);p.add_argument("--seed-mapping",type=Path,required=True);p.add_argument("--original-eboot",type=Path,required=True);p.add_argument("--font",type=Path,required=True);p.add_argument("--han-override",type=Path,required=True);p.add_argument("--horizontal-left-inset",type=int);p.add_argument("--work",type=Path,required=True);p.add_argument("--standalone-path",action="append",default=[]);p.add_argument("--output-iso",type=Path);p.add_argument("--overwrite",action="store_true");a=p.parse_args(argv)
 if a.mode=="build" and a.output_iso is None:p.error("build requires --output-iso")
 try:result=execute(a);print(json.dumps(result["summary"],ensure_ascii=False,indent=2));return 0
 except (OSError,KeyError,ValueError,json.JSONDecodeError,IntegratedBuildError) as exc:print(f"통합 빌드 실패: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
