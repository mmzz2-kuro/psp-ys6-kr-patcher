#!/usr/bin/env python3
"""Build the first safe Hangul dialogue port for Ys VI SPECIAL VERSION."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,struct,sys,tempfile
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image
try:
 from tools.scripts.iso9660_info import SECTOR_SIZE,find_record
 from tools.scripts.ys6_arc import DATA_FLAGS,parse_archive,replace_file
 from tools.scripts.ys6_hangul_codec import encode_translation
 from tools.scripts.ys6_iso_multi_patch import Replacement,patch_atomic
 from tools.scripts.ys6_special_font_proof import BOOT_SHA256,EBOOT_SHA256,FONT_OFFSET,FONT_COUNT,RECORD_SIZE,GLYPH_SIZE,render_glyph
 from tools.scripts.ys6_xso import parse_xso,rebuild_xso
 from tools.scripts.ys6_z import build_container,verify_container_bytes
except ModuleNotFoundError:
 from iso9660_info import SECTOR_SIZE,find_record
 from ys6_arc import DATA_FLAGS,parse_archive,replace_file
 from ys6_hangul_codec import encode_translation
 from ys6_iso_multi_patch import Replacement,patch_atomic
 from ys6_special_font_proof import BOOT_SHA256,EBOOT_SHA256,FONT_OFFSET,FONT_COUNT,RECORD_SIZE,GLYPH_SIZE,render_glyph
 from ys6_xso import parse_xso,rebuild_xso
 from ys6_z import build_container,verify_container_bytes

ISO_SHA256="C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9"
PROFILE="ULJM-05155"
EARLY_SOURCE_PATH="PSP_GAME/USRDIR/data/map/s_05/s_0551/s_0551.xso.z"
EARLY_IDM_PATH="PSP_GAME/USRDIR/data/idm/s_05/s_0551/s_scene.idm"
EARLY_ARCHIVE_PATH="PSP_GAME/USRDIR/data/arc/s_0551.bin"
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def file_sha(path):
 d=hashlib.sha256()
 with path.open("rb") as f:
  while c:=f.read(1024*1024):d.update(c)
 return d.hexdigest().upper()
def read_iso(iso,path):
 r=find_record(iso,path)
 with iso.open("rb") as f:f.seek(r.extent_lba*SECTOR_SIZE);return f.read(r.data_length),r
def inventory_rows(path):
 with path.open("r",encoding="utf-8-sig",newline="") as f:return {r["path"].casefold():r for r in csv.DictReader(f)}
def xso_meta(payload):
 if len(payload)<0x24 or payload[:4]!=b"XSR\0":return None
 words,count=struct.unpack_from("<II",payload,0x1C);code_end=0x24+words*4;pool_start=code_end+count*4
 if pool_start>len(payload):return None
 offsets=[struct.unpack_from("<I",payload,code_end+i*4)[0] for i in range(count)];pool=payload[pool_start:];raw=[]
 for i,start in enumerate(offsets):
  end=offsets[i+1] if i+1<count else len(pool)
  if not 0<=start<end<=len(pool):return None
  value=pool[start:end];nul=value.find(b"\0")
  if nul<0:return None
  try:value[:nul].decode("cp932")
  except UnicodeDecodeError:return None
  raw.append(value[:nul])
 return {"payload_sha256":sha(payload),"code_sha256":sha(payload[0x24:code_end]),"string_count":count,"raw":raw}
def collect_candidates(iso,rows):
 out=[];archive_sources={}
 with iso.open("rb") as f:
  for row in rows.values():
   path=row["path"];size=int(row["second_size"] or 0);lba=int(row["second_lba"] or 0)
   if not size:continue
   if path.lower().endswith(".xso.z"):
    f.seek(lba*SECTOR_SIZE);container=f.read(size);valid,payload,_=verify_container_bytes(container);meta=xso_meta(payload) if valid else None
    if meta:out.append({"location":path,"kind":"standalone","iso_path":path,"container":container,"allocated":math.ceil(size/SECTOR_SIZE)*SECTOR_SIZE,**meta})
   if path.lower().startswith("psp_game/usrdir/data/arc/") and path.lower().endswith(".bin"):
    f.seek(lba*SECTOR_SIZE);arc=f.read(size)
    try:entries=parse_archive(arc)
    except Exception:continue
    archive_sources[path]=arc;data_entries=sorted((e for e in entries if e.flags in DATA_FLAGS and e.offset and e.size),key=lambda e:e.offset)
    next_offsets={e.index:(data_entries[i+1].offset if i+1<len(data_entries) else len(arc)) for i,e in enumerate(data_entries)}
    for e in data_entries:
     if not e.name.lower().endswith(".xso.z"):continue
     container=arc[e.offset:e.offset+e.size];valid,payload,_=verify_container_bytes(container);meta=xso_meta(payload) if valid else None
     if meta:out.append({"location":f"{path}#{e.index}:{e.name}","kind":"archive","iso_path":path,"entry_index":e.index,"entry_name":e.name,"entry_flags":e.flags,"container":container,"allocated":next_offsets[e.index]-e.offset,**meta})
 return out,archive_sources
def select_ports(candidates,mapping_csv,catalog,workspace):
 by_location={c["location"]:c for c in candidates}
 old_files={x["iso_path"]:x for x in catalog["files"]};rows=[]
 with mapping_csv.open("r",encoding="utf-8-sig",newline="") as f:mapping_rows={r["iso_path"]:r for r in csv.DictReader(f)}
 targets=defaultdict(dict);excluded=Counter()
 for r in workspace["records"]:
  if r.get("status")!="override":continue
  old=old_files.get(r["iso_path"]);mapping_row=mapping_rows.get(r["iso_path"]);kind=mapping_row["status"] if mapping_row else None
  if not old or kind not in {"exact_payload","same_code_and_string_count"}:excluded["not_structural_candidate"]+=1;continue
  pool=[by_location[x] for x in mapping_row.get("matches","").split(" | ") if x in by_location]
  if not pool:excluded["mapped_runtime_missing"]+=1;continue
  matched=0
  for c in pool:
   i=int(r["string_index"])
   if i>=len(c["raw"]) or c["raw"][i].hex().upper()!=r["source_raw_hex"].upper():continue
   existing=targets[c["location"]].get(i)
   if existing and existing["translation"]!=r["translation"]:
    excluded["shared_translation_conflict"]+=1;continue
   targets[c["location"]][i]=r;matched+=1
  if matched:rows.append({"source_iso_path":r["iso_path"],"string_index":int(r["string_index"]),"translation":r["translation"],"target_count":matched,"match_kind":kind})
  else:excluded["source_or_index_mismatch"]+=1
 return targets,rows,dict(excluded)
def font_records(boot):
 result=[]
 for i in range(FONT_COUNT):
  off=FONT_OFFSET+i*RECORD_SIZE;code=struct.unpack_from("<H",boot,off)[0];raw=code.to_bytes(2,"big")
  try:character=raw.decode("cp932")
  except UnicodeDecodeError:character=""
  result.append({"game_code":code,"font_index":i,"record_offset":off,"character":character})
 return result
def parse_idm(data):
 if len(data)<0x10:raise ValueError("IDM header truncated")
 count,version,zero1,zero2=struct.unpack_from("<IIII",data,0)
 if version!=1 or zero1 or zero2:raise ValueError("unsupported IDM header")
 pos=0x10;records=[];strings=[]
 for record_index in range(count):
  if pos+12>len(data):raise ValueError(f"IDM record header truncated: {record_index}")
  record_id,string_count,argument_count=struct.unpack_from("<III",data,pos);pos+=12
  if string_count>32 or argument_count>32:raise ValueError(f"IDM unreasonable record counts: {record_index}")
  if pos+argument_count*4>len(data):raise ValueError(f"IDM arguments truncated: {record_index}")
  arguments=list(struct.unpack_from("<"+"I"*argument_count,data,pos)) if argument_count else [];pos+=argument_count*4
  values=[]
  for string_index in range(string_count):
   if pos+4>len(data):raise ValueError(f"IDM string length truncated: {record_index}:{string_index}")
   length=struct.unpack_from("<I",data,pos)[0];pos+=4
   if pos+length>len(data):raise ValueError(f"IDM string truncated: {record_index}:{string_index}")
   raw=data[pos:pos+length];pos+=length
   try:raw.decode("cp932")
   except UnicodeDecodeError as exc:raise ValueError(f"IDM CP932 decode failed: {record_index}:{string_index}: {exc}") from exc
   strings.append({"flat_index":len(strings),"record_index":record_index,"record_id":record_id,"string_index":string_index,"raw":raw});values.append(raw)
  records.append({"record_id":record_id,"arguments":arguments,"strings":values})
 if pos!=len(data):raise ValueError(f"IDM trailing bytes: {len(data)-pos}")
 return {"count":count,"records":records,"strings":strings}
def rebuild_idm(parsed,replacements):
 out=bytearray(struct.pack("<IIII",parsed["count"],1,0,0));flat=0
 for record in parsed["records"]:
  values=[]
  for raw in record["strings"]:values.append(replacements.get(flat,raw));flat+=1
  out.extend(struct.pack("<III",record["record_id"],len(values),len(record["arguments"])))
  if record["arguments"]:out.extend(struct.pack("<"+"I"*len(record["arguments"]),*record["arguments"]))
  for raw in values:out.extend(struct.pack("<I",len(raw)));out.extend(raw)
 result=bytes(out);check=parse_idm(result)
 if check["count"]!=parsed["count"] or len(check["strings"])!=len(parsed["strings"]):raise ValueError("IDM rebuild verification failed")
 return result
def early_idm_rows(workspace):
 return [r for r in workspace["records"] if r["iso_path"]==EARLY_SOURCE_PATH and 35<=int(r["string_index"])<=45 and r.get("status")=="override"]
def allocate_mapping(boot,candidates,text,existing=None):
 needed=sorted({c for c in text if "가"<=c<="힣"},key=ord);table_end=FONT_OFFSET+FONT_COUNT*RECORD_SIZE
 used=Counter()
 for c in candidates:
  for raw in c["raw"]:
   for i in range(len(raw)-1):used[int.from_bytes(raw[i:i+2],"big")]+=1
 outside=boot[:FONT_OFFSET]+boot[table_end:]
 safe=[]
 for r in reversed(font_records(boot)):
  code=r["game_code"]
  if r["character"] and used[code]==0 and outside.count(code.to_bytes(2,"big"))==0:safe.append(r)
 existing=[dict(row) for row in (existing or [])];by_character={r["character"]:r for r in existing};assigned_indices={int(r["font_index"]) for r in existing}
 available=[r for r in safe if r["font_index"] not in assigned_indices];missing=[ch for ch in needed if ch not in by_character]
 if len(available)<len(missing):raise ValueError(f"SPECIAL VERSION safe font slots 부족: need={len(missing)}, have={len(available)}")
 added=[{"unicode":f"U+{ord(ch):04X}","character":ch,"game_code":f"0x{r['game_code']:04X}","font_index":r["font_index"],"original_character":r["character"],"original_usage_count":used[r["game_code"]],"status":"special_106_safe_append"} for ch,r in zip(missing,available)]
 mapping=existing+added;assigned={int(r["font_index"]):r["character"] for r in mapping}
 safe_rows=[{"game_code":f"0x{r['game_code']:04X}","font_index":r["font_index"],"original_character":r["character"],"xso_usage_count":used[r["game_code"]],"assigned_character":assigned.get(r["font_index"],"")} for r in safe]
 return mapping,safe_rows
def patch_font(boot,mapping,font,work):
 out=bytearray(boot);previews=[];glyphs=[]
 for row in mapping:
  bitmap,preview=render_glyph(row["character"],font);off=FONT_OFFSET+int(row["font_index"])*RECORD_SIZE+2
  out[off:off+GLYPH_SIZE]=bitmap;previews.append(preview);glyphs.append({**row,"bitmap_offset":f"0x{off:X}","bitmap_sha256":sha(bitmap)})
 cols=32;atlas=Image.new("L",(cols*16,math.ceil(len(previews)/cols)*14),0)
 for i,img in enumerate(previews):atlas.paste(img,((i%cols)*16,(i//cols)*14))
 atlas.resize((atlas.width*4,atlas.height*4),Image.Resampling.NEAREST).save(work/"hangul-atlas.png")
 return bytes(out),glyphs
def build(args):
 if file_sha(args.iso)!=ISO_SHA256:raise ValueError("SPECIAL VERSION ISO SHA-256 mismatch")
 work=args.work;work.mkdir(parents=True,exist_ok=True);rows=inventory_rows(args.inventory);candidates,archive_sources=collect_candidates(args.iso,rows)
 catalog=json.loads(args.catalog.read_text(encoding="utf-8-sig"));workspace=json.loads(args.workspace.read_text(encoding="utf-8-sig"));targets,ports,excluded=select_ports(candidates,args.mapping,catalog,workspace);early_rows=early_idm_rows(workspace)
 by_location={c["location"]:c for c in candidates};translation_text="".join(r["translation"] for values in targets.values() for r in values.values())+"".join(r["translation"] for r in early_rows)
 boot,boot_rec=read_iso(args.iso,"PSP_GAME/SYSDIR/BOOT.BIN");eboot,eboot_rec=read_iso(args.iso,"PSP_GAME/SYSDIR/EBOOT.BIN")
 if sha(boot)!=BOOT_SHA256 or sha(eboot)!=EBOOT_SHA256:raise ValueError("SPECIAL VERSION executable hash mismatch")
 previous_mapping=[]
 if (work/"hangul-mapping.json").exists():previous_mapping=json.loads((work/"hangul-mapping.json").read_text(encoding="utf-8-sig"))["mappings"]
 mapping,safe_rows=allocate_mapping(boot,candidates,translation_text,previous_mapping);safe_count=len(safe_rows);patched_boot,glyphs=patch_font(boot,mapping,args.font,work);patched_eboot=patched_boot+eboot[len(patched_boot):]
 previous_revision=0
 if previous_mapping:previous_revision=int(json.loads((work/"hangul-mapping.json").read_text(encoding="utf-8-sig")).get("mapping_revision",1))
 mapping_revision=previous_revision+(1 if len(mapping)>len(previous_mapping) else 0)
 (work/"BOOT.BIN").write_bytes(patched_boot);(work/"EBOOT.BIN").write_bytes(patched_eboot);mapdoc={"schema_version":1,"profile":PROFILE,"mapping_revision":mapping_revision,"mappings":mapping};(work/"hangul-mapping.json").write_text(json.dumps(mapdoc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (work/"font-usage.json").write_text(json.dumps({"schema_version":1,"profile":PROFILE,"font_count":FONT_COUNT,"safe_slot_count":safe_count,"assigned_count":len(mapping),"safe_slots":safe_rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 with (work/"port-records.csv").open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=("source_iso_path","string_index","translation","target_count","match_kind"));writer.writeheader();writer.writerows(ports)
 replacements=[];reports=[];archive_patched=dict(archive_sources);overflow=[];idm_report=None
 with tempfile.TemporaryDirectory(dir=work) as td:
  temp=Path(td)
  for n,(location,values) in enumerate(sorted(targets.items())):
   c=by_location[location];source=temp/f"{n}.xso";valid,payload,error=verify_container_bytes(c["container"])
   if not valid or payload is None:raise ValueError(f"invalid XSO container: {location}: {error}")
   source.write_bytes(payload);encoded={i:encode_translation(r["translation"],mapping) for i,r in values.items()};_parsed,rebuilt=rebuild_xso(source,encoded,allow_length_change=True);container=build_container(rebuilt)
   if len(container)>c["allocated"]:overflow.append({"location":location,"size":len(container),"allocated":c["allocated"]});continue
   if c["kind"]=="archive":
    arc=archive_patched[c["iso_path"]];entry=next(e for e in parse_archive(arc) if e.index==c["entry_index"]);archive_patched[c["iso_path"]]=replace_file(arc,entry,container)
   else:
    out=work/"xso"/(sha(location.encode())+".xso.z");out.parent.mkdir(exist_ok=True);out.write_bytes(container);replacements.append(Replacement(c["iso_path"],out,len(c["container"]),sha(c["container"])))
   reports.append({"location":location,"translation_count":len(values),"original_size":len(c["container"]),"output_size":len(container),"allocated_size":c["allocated"],"output_sha256":sha(container)})
 if overflow:raise ValueError("XSO allocation overflow: "+json.dumps(overflow,ensure_ascii=False))
 idm_original,idm_record=read_iso(args.iso,EARLY_IDM_PATH);parsed_idm=parse_idm(idm_original)
 idm_replacements={};matched=[]
 for row in early_rows:
  source=bytes.fromhex(row["source_raw_hex"]);hits=[s for s in parsed_idm["strings"] if s["raw"]==source]
  if len(hits)!=1:raise ValueError(f"early IDM source match count: XSO index={row['string_index']}, hits={len(hits)}")
  hit=hits[0];idm_replacements[hit["flat_index"]]=encode_translation(row["translation"],mapping);matched.append({"xso_string_index":int(row["string_index"]),"idm_flat_index":hit["flat_index"],"idm_record_index":hit["record_index"],"idm_record_id":hit["record_id"],"source":row["source_text"],"translation":row["translation"]})
 idm_output=rebuild_idm(parsed_idm,idm_replacements);idm_path=work/"s_scene.idm";idm_path.write_bytes(idm_output)
 if len(idm_output)>math.ceil(len(idm_original)/SECTOR_SIZE)*SECTOR_SIZE:raise ValueError("standalone early IDM allocation overflow")
 replacements.append(Replacement(EARLY_IDM_PATH,idm_path,len(idm_original),sha(idm_original)))
 arc=archive_patched[EARLY_ARCHIVE_PATH];entries=parse_archive(arc);entry=next(e for e in entries if e.index==6 and e.name=="s_scene.idm");data_entries=sorted((e for e in entries if e.offset and e.size),key=lambda e:e.offset);position=data_entries.index(entry);allocated=(data_entries[position+1].offset if position+1<len(data_entries) else len(arc))-entry.offset
 if arc[entry.offset:entry.offset+entry.size]!=idm_original:raise ValueError("early IDM runtime copy source mismatch")
 if len(idm_output)>allocated:raise ValueError("archive early IDM allocation overflow")
 archive_patched[EARLY_ARCHIVE_PATH]=replace_file(arc,entry,idm_output);idm_report={"record_count":parsed_idm["count"],"string_count":len(parsed_idm["strings"]),"translation_count":len(matched),"original_size":len(idm_original),"output_size":len(idm_output),"standalone_allocated_size":math.ceil(len(idm_original)/SECTOR_SIZE)*SECTOR_SIZE,"archive_allocated_size":allocated,"original_sha256":sha(idm_original),"output_sha256":sha(idm_output),"records":matched}
 for path,data in sorted(archive_patched.items()):
  if data==archive_sources[path]:continue
  out=work/"archives"/Path(path).name;out.parent.mkdir(exist_ok=True);out.write_bytes(data);replacements.append(Replacement(path,out,len(archive_sources[path]),sha(archive_sources[path])))
 replacements.insert(0,Replacement("PSP_GAME/SYSDIR/EBOOT.BIN",work/"EBOOT.BIN",len(eboot),sha(eboot)));replacements.insert(0,Replacement("PSP_GAME/SYSDIR/BOOT.BIN",work/"BOOT.BIN",len(boot),sha(boot)))
 iso_result=patch_atomic(args.iso,args.output,replacements,ISO_SHA256,args.overwrite)
 special_catalog={"schema_version":1,"profile":PROFILE,"files":[{"location":c["location"],"kind":c["kind"],"payload_sha256":c["payload_sha256"],"code_sha256":c["code_sha256"],"string_count":c["string_count"]} for c in candidates]};(work/"dialogue-catalog.json").write_text(json.dumps(special_catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 runtime=defaultdict(list)
 for c in candidates:runtime[c["payload_sha256"]].append(c["location"])
 (work/"runtime-map.json").write_text(json.dumps({"schema_version":1,"profile":PROFILE,"payloads":[{"payload_sha256":k,"locations":v} for k,v in sorted(runtime.items())]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 report={"valid":True,"profile":PROFILE,"source_iso_sha256":ISO_SHA256,"candidate_xso_count":len(candidates),"candidate_translation_record_count":1169,"ported_source_record_count":len(ports),"ported_match_kind_counts":dict(Counter(r["match_kind"] for r in ports)),"patched_runtime_xso_count":len(reports),"early_idm":idm_report,"excluded":excluded,"mapping_revision":mapping_revision,"unique_hangul_count":len(mapping),"safe_slot_count":safe_count,"remaining_safe_slot_count":safe_count-len(mapping),"glyph_count":len(glyphs),"archive_replacement_count":sum(r.internal_path.lower().endswith(".bin") for r in replacements),"standalone_replacement_count":sum(r.internal_path.lower().endswith(".xso.z") for r in replacements),"boot_sha256":sha(patched_boot),"eboot_sha256":sha(patched_eboot),"iso":iso_result,"xso":reports}
 (work/"port-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return report
def main():
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser();p.add_argument("iso",type=Path);p.add_argument("inventory",type=Path);p.add_argument("mapping",type=Path);p.add_argument("catalog",type=Path);p.add_argument("workspace",type=Path);p.add_argument("work",type=Path);p.add_argument("output",type=Path);p.add_argument("--font",type=Path,required=True);p.add_argument("--overwrite",action="store_true");a=p.parse_args()
 try:print(json.dumps(build(a),ensure_ascii=False,indent=2));return 0
 except Exception as e:print(f"SPECIAL VERSION 이식 실패: {e}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
