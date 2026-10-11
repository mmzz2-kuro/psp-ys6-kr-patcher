#!/usr/bin/env python3
"""Incrementally apply resolved IDM translations to the verified issue-106 ISO."""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from collections import defaultdict
from pathlib import Path
from PIL import Image
try:
 from tools.scripts.iso9660_info import SECTOR_SIZE,find_record
 from tools.scripts.ys6_arc import parse_archive,replace_file
 from tools.scripts.ys6_hangul_codec import encode_translation
 from tools.scripts.ys6_idm import parse_idm,rebuild_idm,sha256
 from tools.scripts.ys6_iso_multi_patch import Replacement,patch_atomic
 from tools.scripts.ys6_special_font_proof import FONT_OFFSET,RECORD_SIZE,GLYPH_SIZE,render_glyph
except ModuleNotFoundError:
 from iso9660_info import SECTOR_SIZE,find_record
 from ys6_arc import parse_archive,replace_file
 from ys6_hangul_codec import encode_translation
 from ys6_idm import parse_idm,rebuild_idm,sha256
 from ys6_iso_multi_patch import Replacement,patch_atomic
 from ys6_special_font_proof import FONT_OFFSET,RECORD_SIZE,GLYPH_SIZE,render_glyph

BASE_ISO_SHA256="B36AF70925EF93E096F4F2453A06220587E01F68E5C19D53B8157DA517B5F8CD"
def file_sha(path):
 d=hashlib.sha256()
 with path.open("rb") as f:
  while c:=f.read(1024*1024):d.update(c)
 return d.hexdigest().upper()
def read_iso(iso,path):
 record=find_record(iso,path)
 with iso.open("rb") as f:f.seek(record.extent_lba*SECTOR_SIZE);return f.read(record.data_length),record
def build(args):
 if file_sha(args.iso)!=BASE_ISO_SHA256:raise ValueError("issue-106 base ISO SHA-256 mismatch")
 args.work.mkdir(parents=True,exist_ok=True);workspace=json.loads(args.workspace.read_text(encoding="utf-8-sig"));runtime=json.loads(args.runtime_map.read_text(encoding="utf-8-sig"));mapping_doc=json.loads(args.mapping.read_text(encoding="utf-8-sig"));mapping=[dict(r) for r in mapping_doc["mappings"]];usage=json.loads(args.font_usage.read_text(encoding="utf-8-sig"))
 mapped={r["character"] for r in mapping};needed=sorted({c for r in workspace["records"] for c in r["translation"] if "가"<=c<="힣" and c not in mapped},key=ord);available=[r for r in usage["safe_slots"] if not r["assigned_character"]]
 if len(needed)>len(available):raise ValueError(f"safe glyph capacity exceeded: need={len(needed)}, have={len(available)}")
 added=[]
 for ch,slot in zip(needed,available):
  row={"unicode":f"U+{ord(ch):04X}","character":ch,"game_code":slot["game_code"],"font_index":int(slot["font_index"]),"original_character":slot["original_character"],"original_usage_count":0,"status":"special_109_safe_append"};mapping.append(row);added.append(row)
 boot,boot_record=read_iso(args.iso,"PSP_GAME/SYSDIR/BOOT.BIN");eboot,eboot_record=read_iso(args.iso,"PSP_GAME/SYSDIR/EBOOT.BIN");patched_boot=bytearray(boot);previews=[]
 for row in added:
  bitmap,preview=render_glyph(row["character"],args.font);off=FONT_OFFSET+int(row["font_index"])*RECORD_SIZE+2;patched_boot[off:off+GLYPH_SIZE]=bitmap;previews.append(preview)
 patched_boot=bytes(patched_boot);patched_eboot=patched_boot+eboot[len(patched_boot):];(args.work/"BOOT.BIN").write_bytes(patched_boot);(args.work/"EBOOT.BIN").write_bytes(patched_eboot)
 mapping_doc={"schema_version":1,"profile":"ULJM-05155","mapping_revision":int(mapping_doc.get("mapping_revision",2))+1,"mappings":mapping};(args.work/"hangul-mapping.json").write_text(json.dumps(mapping_doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 atlas=Image.new("L",(16*min(32,max(1,len(previews))),14*math.ceil(max(1,len(previews))/32)),0)
 for i,img in enumerate(previews):atlas.paste(img,((i%32)*16,(i//32)*14))
 atlas.resize((atlas.width*4,atlas.height*4),Image.Resampling.NEAREST).save(args.work/"added-glyph-atlas.png")
 grouped=defaultdict(list)
 for row in workspace["records"]:grouped[row["target_iso_path"]].append(row)
 runtime_by_path={r["iso_path"]:r for r in runtime["resources"]};archives={};archive_original={};replacements=[];reports=[]
 for resource_index,(path,rows) in enumerate(sorted(grouped.items())):
  original,record=read_iso(args.iso,path);parsed=parse_idm(original);changes={}
  for row in rows:
   flat=int(row["target_flat_index"]);encoded=encode_translation(row["translation"],mapping)
   if flat in changes and changes[flat]!=encoded:raise ValueError(f"translation conflict: {path}#{flat}")
   changes[flat]=encoded
  output=rebuild_idm(parsed,changes);allocated=math.ceil(len(original)/SECTOR_SIZE)*SECTOR_SIZE
  if len(output)>allocated:raise ValueError(f"standalone IDM allocation overflow: {path}: {len(output)}>{allocated}")
  out=args.work/"idm"/(Path(path).parent.name+"-s_scene.idm");out.parent.mkdir(exist_ok=True);out.write_bytes(output);replacements.append(Replacement(path,out,len(original),sha256(original)))
  copies=runtime_by_path[path]["copies"]
  for copy in copies:
   arc_path=copy["archive_path"]
   if arc_path not in archives:archives[arc_path],_=read_iso(args.iso,arc_path);archive_original[arc_path]=archives[arc_path]
   arc=archives[arc_path];entries=parse_archive(arc);entry=next(e for e in entries if e.index==int(copy["entry_index"]) and e.name==copy["entry_name"]);data_entries=sorted((e for e in entries if e.offset and e.size),key=lambda e:e.offset);pos=data_entries.index(entry);entry_alloc=(data_entries[pos+1].offset if pos+1<len(data_entries) else len(arc))-entry.offset
   current=arc[entry.offset:entry.offset+entry.size]
   if current!=original:raise ValueError(f"runtime IDM source mismatch: {arc_path}#{entry.index}")
   if len(output)>entry_alloc:raise ValueError(f"archive IDM allocation overflow: {arc_path}#{entry.index}")
   archives[arc_path]=replace_file(arc,entry,output)
  reports.append({"iso_path":path,"translation_count":len(changes),"runtime_copy_count":len(copies),"original_size":len(original),"output_size":len(output),"allocated_size":allocated,"output_sha256":sha256(output)})
 for path,data in sorted(archives.items()):
  out=args.work/"archives"/Path(path).name;out.parent.mkdir(exist_ok=True);out.write_bytes(data);replacements.append(Replacement(path,out,len(archive_original[path]),sha256(archive_original[path])))
 replacements.insert(0,Replacement("PSP_GAME/SYSDIR/EBOOT.BIN",args.work/"EBOOT.BIN",len(eboot),sha256(eboot)));replacements.insert(0,Replacement("PSP_GAME/SYSDIR/BOOT.BIN",args.work/"BOOT.BIN",len(boot),sha256(boot)))
 iso_report=patch_atomic(args.iso,args.output,replacements,BASE_ISO_SHA256,args.overwrite);report={"valid":True,"base_iso_sha256":BASE_ISO_SHA256,"mapping_revision":mapping_doc["mapping_revision"],"mapping_count":len(mapping),"added_glyph_count":len(added),"idm_resource_count":len(reports),"idm_translation_count":sum(r["translation_count"] for r in reports),"runtime_copy_count":sum(r["runtime_copy_count"] for r in reports),"iso":iso_report,"resources":reports};(args.work/"build-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return report
def main():
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser();p.add_argument("iso",type=Path);p.add_argument("workspace",type=Path);p.add_argument("runtime_map",type=Path);p.add_argument("mapping",type=Path);p.add_argument("font_usage",type=Path);p.add_argument("work",type=Path);p.add_argument("output",type=Path);p.add_argument("--font",type=Path,required=True);p.add_argument("--overwrite",action="store_true");a=p.parse_args()
 try:print(json.dumps(build(a),ensure_ascii=False,indent=2));return 0
 except Exception as exc:print(f"SPECIAL VERSION IDM 적용 실패: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
