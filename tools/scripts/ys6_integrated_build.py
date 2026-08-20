#!/usr/bin/env python3
"""Preflight and build approved Ys VI dialogue overrides across runtime archives."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys,tempfile
from collections import defaultdict
from pathlib import Path
from PIL import Image
try:
    from tools.scripts.iso9660_info import SECTOR_SIZE,find_record
    from tools.scripts.ys6_arc import find_file,parse_archive,replace_file
    from tools.scripts.ys6_castinfo import encode_game_name,patch_name
    from tools.scripts.ys6_cast_name_workspace import load_workspace as load_cast_workspace,reviewed_records as reviewed_cast_records,validate_workspace as validate_cast_workspace
    from tools.scripts.ys6_hangul_codec import encode_translation,extend_mapping,write_mapping
    from tools.scripts.ys6_hangul_font_build import build as build_font
    from tools.scripts.ys6_invinfo import parse as parse_invinfo,patch as patch_invinfo,sha256 as invinfo_sha256
    from tools.scripts.ys6_item_workspace import load_workspace as load_item_workspace,validate_workspace as validate_item_workspace
    from tools.scripts.ys6_system_message_workspace import load_workspace as load_system_workspace,patch_overrides as patch_system_messages,validate_workspace as validate_system_workspace
    from tools.scripts.ys6_iso_multi_patch import Replacement,patch_atomic
    from tools.scripts.ys6_option_menu_image import compose as compose_option_menu
    from tools.scripts.ys6_additional_image_patch import build_container as build_image_container,compose_collection_picture,compose_payload,edited_count
    from tools.scripts.ys6_translation_workspace import validate
    from tools.scripts.ys6_xso import parse_xso,rebuild_xso
    from tools.scripts.ys6_z import build_container,verify_container_bytes
except ModuleNotFoundError:
    try:
        from .iso9660_info import SECTOR_SIZE,find_record
        from .ys6_arc import find_file,parse_archive,replace_file
        from .ys6_castinfo import encode_game_name,patch_name
        from .ys6_cast_name_workspace import load_workspace as load_cast_workspace,reviewed_records as reviewed_cast_records,validate_workspace as validate_cast_workspace
        from .ys6_hangul_codec import encode_translation,extend_mapping,write_mapping
        from .ys6_hangul_font_build import build as build_font
        from .ys6_invinfo import parse as parse_invinfo,patch as patch_invinfo,sha256 as invinfo_sha256
        from .ys6_item_workspace import load_workspace as load_item_workspace,validate_workspace as validate_item_workspace
        from .ys6_system_message_workspace import load_workspace as load_system_workspace,patch_overrides as patch_system_messages,validate_workspace as validate_system_workspace
        from .ys6_iso_multi_patch import Replacement,patch_atomic
        from .ys6_option_menu_image import compose as compose_option_menu
        from .ys6_additional_image_patch import build_container as build_image_container,compose_collection_picture,compose_payload,edited_count
        from .ys6_translation_workspace import validate
        from .ys6_xso import parse_xso,rebuild_xso
        from .ys6_z import build_container,verify_container_bytes
    except ImportError:
        from iso9660_info import SECTOR_SIZE,find_record
        from ys6_arc import find_file,parse_archive,replace_file
        from ys6_castinfo import encode_game_name,patch_name
        from ys6_cast_name_workspace import load_workspace as load_cast_workspace,reviewed_records as reviewed_cast_records,validate_workspace as validate_cast_workspace
        from ys6_hangul_codec import encode_translation,extend_mapping,write_mapping
        from ys6_hangul_font_build import build as build_font
        from ys6_invinfo import parse as parse_invinfo,patch as patch_invinfo,sha256 as invinfo_sha256
        from ys6_item_workspace import load_workspace as load_item_workspace,validate_workspace as validate_item_workspace
        from ys6_system_message_workspace import load_workspace as load_system_workspace,patch_overrides as patch_system_messages,validate_workspace as validate_system_workspace
        from ys6_iso_multi_patch import Replacement,patch_atomic
        from ys6_option_menu_image import compose as compose_option_menu
        from ys6_additional_image_patch import build_container as build_image_container,compose_collection_picture,compose_payload,edited_count
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
 selected=[dict(x) for x in workspace["records"] if x["status"]=="override"]
 if not selected:raise IntegratedBuildError("override translation is empty")
 return selected

select_overrides=select_reviewed

def group_translations(records:list[dict],catalog:dict,runtime_map:dict)->list[dict]:
 files={x["iso_path"]:x for x in catalog["files"]}; mapping_by_hash={x["xso_sha256"]:x for x in runtime_map["mappings"]}; grouped=defaultdict(list)
 for record in records:
  source=files.get(record["iso_path"])
  if not source:raise IntegratedBuildError(f"catalog path missing: {record['iso_path']}")
  grouped[source["xso_sha256"]].append(record)
 result=[]
 for digest,items in sorted(grouped.items()):
  mapping=mapping_by_hash.get(digest)
  if not mapping or mapping["status"] not in {"exact_one_to_one","standalone_duplicate","standalone_only","many_to_many"}:
   raise IntegratedBuildError(f"unsupported runtime mapping: {digest}")
  if not mapping["runtime_keys"] and not mapping["standalone_paths"]:raise IntegratedBuildError(f"mapping has no patch target: {digest}")
  merged={}; origins=defaultdict(list)
  for item in items:
   index=int(item["string_index"])
   if index in merged and merged[index]["translation"]!=item["translation"]:
    raise IntegratedBuildError(f"shared payload translation conflict: {digest} index={index}")
   merged[index]=item; origins[index].append(item["iso_path"])
  result.append({"xso_sha256":digest,"mapping_status":mapping["status"],"standalone_paths":mapping["standalone_paths"],"runtime_keys":list(mapping["runtime_keys"]),"runtime_key":mapping["runtime_keys"][0] if mapping["runtime_keys"] else None,"records":[{**merged[i],"origin_paths":sorted(set(origins[i]))} for i in sorted(merged)]})
 return result

def read_iso_file(iso:Path,internal_path:str)->tuple[bytes,object]:
 record=find_record(iso,internal_path)
 with iso.open("rb") as f:f.seek(record.extent_lba*SECTOR_SIZE);data=f.read(record.data_length)
 return data,record

def sync_additional_runtime_copies(resource:dict,original_container:bytes,patched_container:bytes,archive_cache:dict,archive_original:dict,load_archive)->list[dict]:
 copies=resource.get("runtime_copies",[]);seen=set();reports=[]
 for meta in copies:
  arc_path=meta["archive_path"];index=int(meta["entry_index"]);name=meta.get("entry_name",Path(resource["iso_path"]).name);flags=int(meta["flags_hex"],0);identity=(arc_path,index,name.casefold(),flags)
  if identity in seen:raise IntegratedBuildError(f"duplicate additional-image runtime copy: {resource['id']}: {arc_path}#{index}")
  seen.add(identity)
  if arc_path not in archive_cache:
   data=load_archive(arc_path);archive_cache[arc_path]=data;archive_original[arc_path]=data
  try:
   source_archive=archive_original[arc_path];source_entry=find_file(parse_archive(source_archive),name,index=index,flags=flags)
  except Exception as exc:
   raise IntegratedBuildError(f"additional-image runtime copy lookup failed: {resource['id']}: {arc_path}#{index}: {exc}") from exc
  source_copy=source_archive[source_entry.offset:source_entry.offset+source_entry.size]
  if source_copy!=original_container:raise IntegratedBuildError(f"additional-image runtime copy source mismatch: {resource['id']}: {arc_path}#{index}")
  current=archive_cache[arc_path]
  try:
   entry=find_file(parse_archive(current),name,index=index,flags=flags)
   if len(patched_container)>entry.allocated_size:raise IntegratedBuildError(f"additional-image runtime copy allocation overflow: {resource['id']}: {arc_path}#{index}: {len(patched_container)} > {entry.allocated_size}")
   archive_cache[arc_path]=replace_file(current,entry,patched_container)
  except IntegratedBuildError:raise
  except Exception as exc:
   raise IntegratedBuildError(f"additional-image runtime copy replacement failed: {resource['id']}: {arc_path}#{index}: {exc}") from exc
  reports.append({"archive_path":arc_path,"entry_index":index,"entry_name":name,"entry_flags_hex":f"0x{flags:08X}","original_size":len(source_copy),"replacement_size":len(patched_container),"allocated_size":entry.allocated_size,"remaining_slack":entry.allocated_size-len(patched_container),"original_sha256":sha256(source_copy),"output_sha256":sha256(patched_container)})
 return reports

def build_mapping(groups:list[dict],usage:dict,seed:list[dict],extra_text:str="")->list[dict]:
 text="".join(r["translation"] for g in groups for r in g["records"])+extra_text
 additional="".join(dict.fromkeys(c for c in text if "가"<=c<="힣" or c in "「」"))
 return extend_mapping(usage,seed,additional)

def rebuild_group(original:bytes,group:dict,mapping:list[dict],temp:Path)->tuple[bytes,dict,list[dict]]:
 source=temp/"source.xso";source.write_bytes(original);parsed=parse_xso(source); replacements={};rows=[]
 for record in group["records"]:
  index=int(record["string_index"])
  if not 0<=index<len(parsed.strings):raise IntegratedBuildError(f"string index out of range: {index}")
  entry=parsed.strings[index]
  if hashlib.sha256(bytes.fromhex(entry.raw_hex)).hexdigest().upper()!=record["source_sha256"]:raise IntegratedBuildError(f"source mismatch: {group['xso_sha256']} index={index}")
  encoded=encode_translation(record["translation"],mapping);replacements[index]=encoded
  rows.append({"xso_sha256":group["xso_sha256"],"runtime_key":" | ".join(group["runtime_keys"]),"string_index":index,"source_text":record["source_text"],"translation":record["translation"],"original_length":entry.byte_length,"replacement_length":len(encoded),"delta":len(encoded)-entry.byte_length,"origin_paths":" | ".join(record["origin_paths"])})
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
 if args.castinfo_name is not None and args.cast_name_workspace is not None:raise IntegratedBuildError("--castinfo-name and --cast-name-workspace cannot be used together")
 cast_workspace=load_cast_workspace(args.cast_name_workspace) if args.cast_name_workspace else None
 cast_selected=reviewed_cast_records(cast_workspace) if cast_workspace else []
 cast_errors=validate_cast_workspace(cast_workspace) if cast_workspace else []
 if cast_errors:raise IntegratedBuildError("invalid cast-name workspace: "+"; ".join(cast_errors))
 item_workspace=load_item_workspace(args.item_workspace) if getattr(args,"item_workspace",None) else None
 item_errors=validate_item_workspace(item_workspace) if item_workspace else []
 if item_errors:raise IntegratedBuildError("invalid item workspace: "+"; ".join(item_errors))
 item_selected=[x for x in item_workspace.get("records",[]) if x.get("status")=="override"] if item_workspace else []
 item_text="".join(x.get("translation_name","")+x.get("translation_description","") for x in item_selected)
 system_workspace=load_system_workspace(args.system_message_workspace) if getattr(args,"system_message_workspace",None) else None
 system_errors=validate_system_workspace(system_workspace) if system_workspace else []
 if system_errors:raise IntegratedBuildError("invalid system-message workspace: "+"; ".join(system_errors))
 system_selected=[x for x in system_workspace.get("records",[]) if x.get("status")=="override"] if system_workspace else []
 system_text="".join(x.get("translation","") for x in system_selected)
 selected=select_overrides(workspace);groups=group_translations(selected,catalog,runtime_map); runtime={x["runtime_key"]:x for x in runtime_map["runtime_entries"]};mapping=build_mapping(groups,usage,seed,"".join(x["translation"] for x in cast_selected)+item_text+system_text)
 args.work.mkdir(parents=True,exist_ok=True);(args.work/"xso").mkdir(exist_ok=True);(args.work/"archives").mkdir(exist_ok=True)
 write_mapping(mapping,args.work/"mapping.json",args.work/"mapping.csv")
 eboot_data=args.original_eboot.read_bytes();system_rows=[]
 if system_workspace:
  try:eboot_data,system_rows=patch_system_messages(eboot_data,system_workspace,mapping)
  except ValueError as exc:raise IntegratedBuildError(f"system-message patch failed: {exc}") from exc
 overrides={"한":args.han_override};patched_eboot,glyph_report,atlas=build_font(eboot_data,mapping,args.font,12,overrides,horizontal_left_inset=args.horizontal_left_inset)
 (args.work/"EBOOT.BIN").write_bytes(patched_eboot);(args.work/"glyph-report.json").write_text(json.dumps({"visible_width":12,"horizontal_left_inset":args.horizontal_left_inset,"glyphs":glyph_report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8");atlas.resize((atlas.width*8,atlas.height*8),Image.Resampling.NEAREST).save(args.work/"glyph-atlas.png")
 archive_cache={};archive_original={};xso_rows=[];translation_rows=[];overflow=[];rebuilt_containers={}
 castinfo_rows=[];item_rows=[];extra_replacements=[];init_original=None;patched_init=None;option_menu_report=None;additional_image_reports=[]
 if args.castinfo_name is not None or cast_selected:
  cast_path="PSP_GAME/USRDIR/data/misc/castinfo.dat";init_path="PSP_GAME/USRDIR/data/arc/init.bin"
  standalone_cast,cast_record=read_iso_file(iso,cast_path);init_data,_=read_iso_file(iso,init_path);init_original=init_data;patched_init=init_data;init_entry=find_file(parse_archive(init_data),"castinfo.dat",index=8,flags=0x01000000);embedded_cast=init_data[init_entry.offset:init_entry.offset+init_entry.size]
  if standalone_cast!=embedded_cast:raise IntegratedBuildError("castinfo standalone and init.bin copies differ")
  patched_cast=standalone_cast
  patch_items=cast_selected if cast_selected else [{"identifier":args.castinfo_identifier,"translation":args.castinfo_name,"source":args.castinfo_expected_name}]
  for item in patch_items:
   before=patched_cast;patched_cast,cast_report=patch_name(patched_cast,item["identifier"],encode_game_name(item["translation"],mapping),item.get("source"))
   castinfo_rows.append({"identifier":item["identifier"],"name":item["translation"],"source":item.get("source", ""),"standalone_path":cast_path,"archive_path":init_path,"entry_index":init_entry.index,"entry_flags_hex":f"0x{init_entry.flags:08X}","original_sha256":sha256(before),"output_sha256":sha256(patched_cast),"size":len(patched_cast),"changed_byte_count":cast_report["changed_byte_count"],"encoded_name_hex":cast_report["encoded_name_hex"]})
  patched_init=replace_file(patched_init,init_entry,patched_cast);cast_dir=args.work/"castinfo";cast_dir.mkdir(exist_ok=True);cast_file=cast_dir/"castinfo.dat";cast_file.write_bytes(patched_cast)
  extra_replacements.append(Replacement(cast_path,cast_file,len(standalone_cast),sha256(standalone_cast)))
 if item_selected:
  item_path="PSP_GAME/USRDIR/data/misc/invinfo.dat";init_path="PSP_GAME/USRDIR/data/arc/init.bin"
  standalone_item,item_record=read_iso_file(iso,item_path)
  if invinfo_sha256(standalone_item)!=item_workspace.get("source_sha256"):raise IntegratedBuildError("invinfo workspace source mismatch")
  if init_original is None:
   init_original,_=read_iso_file(iso,init_path);patched_init=init_original
  item_entry=find_file(parse_archive(init_original),"invinfo.dat",index=10,flags=0x01000000);embedded_item=init_original[item_entry.offset:item_entry.offset+item_entry.size]
  if standalone_item!=embedded_item:raise IntegratedBuildError("invinfo standalone and init.bin copies differ")
  parsed_items=parse_invinfo(standalone_item);replacements={}
  for item in item_selected:
   index=int(item["index"]);source=parsed_items[index]
   source_bytes=standalone_item[source.offset:source.offset+184]
   if sha256(source_bytes)!=item.get("source_record_sha256"):raise IntegratedBuildError(f"item source mismatch: {index}")
   name=encode_translation(item["translation_name"],mapping)
   description=encode_translation(item.get("translation_description","").replace("\r\n","\n").replace("\r","\n").replace("\n","\r\n"),mapping)
   replacements[index]=(name,description)
  patched_item,reports=patch_invinfo(standalone_item,replacements)
  for report in reports:
   item=next(x for x in item_selected if int(x["index"])==report["index"])
   item_rows.append({**report,"source_name":item["source_name"],"translation_name":item["translation_name"],"translation_description":item.get("translation_description","")})
  patched_init=replace_file(patched_init,item_entry,patched_item);item_dir=args.work/"items";item_dir.mkdir(exist_ok=True);item_file=item_dir/"invinfo.dat";item_file.write_bytes(patched_item)
  extra_replacements.append(Replacement(item_path,item_file,len(standalone_item),sha256(standalone_item)))
 option_workspace=getattr(args,"option_menu_workspace",None);option_source=getattr(args,"option_menu_source",None)
 option_edited=option_workspace/"edited_buttons" if option_workspace else None
 option_files=sorted(option_edited.glob("*.png")) if option_edited and option_edited.exists() else []
 if option_files:
  init_path="PSP_GAME/USRDIR/data/arc/init.bin";standalone_option_path="PSP_GAME/USRDIR/data/image/static_tex.dds.z"
  if init_original is None:init_original,_=read_iso_file(iso,init_path);patched_init=init_original
  option_entry=find_file(parse_archive(init_original),"static_tex.dds.z",index=29,flags=0x01000000)
  embedded_container=init_original[option_entry.offset:option_entry.offset+option_entry.size]
  valid,embedded_payload,error=verify_container_bytes(embedded_container)
  if not valid or embedded_payload is None:raise IntegratedBuildError(f"option-menu embedded container invalid: {error or ''}")
  source_payload=option_source.read_bytes()
  if embedded_payload!=source_payload:raise IntegratedBuildError("option-menu source payload does not match init.bin")
  option_dir=args.work/"option-menu";option_dir.mkdir(exist_ok=True)
  option_payload_file=option_dir/"static_tex.dds";option_container_file=option_dir/"static_tex.dds.z"
  try:option_menu_report=compose_option_menu(option_source,option_workspace,option_payload_file,option_container_file,option_entry.allocated_size)
  except ValueError as exc:raise IntegratedBuildError(f"option-menu image patch failed: {exc}") from exc
  option_container=option_container_file.read_bytes();patched_init=replace_file(patched_init,option_entry,option_container)
  standalone_option,standalone_option_record=read_iso_file(iso,standalone_option_path)
  valid,standalone_payload,error=verify_container_bytes(standalone_option)
  if not valid or standalone_payload!=source_payload:raise IntegratedBuildError(f"option-menu standalone payload mismatch: {error or ''}")
  standalone_allocated=((standalone_option_record.data_length+SECTOR_SIZE-1)//SECTOR_SIZE)*SECTOR_SIZE
  if len(option_container)>standalone_allocated:raise IntegratedBuildError(f"option-menu standalone allocation overflow: {len(option_container)} > {standalone_allocated}")
  extra_replacements.append(Replacement(standalone_option_path,option_container_file,len(standalone_option),sha256(standalone_option)))
 additional_workspace=getattr(args,"additional_image_workspace",None)
 additional_count,_additional_files=edited_count(additional_workspace) if additional_workspace else (0,[])
 if additional_count:
  additional_manifest=json.loads((additional_workspace/"manifest.json").read_text(encoding="utf-8-sig"))
  additional_dir=args.work/"additional-images";additional_dir.mkdir(exist_ok=True)
  embedded_resources=[r for r in additional_manifest["resources"] if r.get("embedded_runtime") or r.get("embedded_picture_index")]
  static_payload=None;static_entry=None;static_original_container=None
  if embedded_resources:
   init_path="PSP_GAME/USRDIR/data/arc/init.bin"
   if init_original is None:init_original,_=read_iso_file(iso,init_path);patched_init=init_original
   static_entry=find_file(parse_archive(patched_init),"static_tex.dds.z",index=29,flags=0x01000000)
   static_original_container=patched_init[static_entry.offset:static_entry.offset+static_entry.size]
   valid,static_payload,error=verify_container_bytes(static_original_container)
   if not valid or static_payload is None:raise IntegratedBuildError(f"additional-image static_tex invalid: {error or ''}")
  for resource in additional_manifest["resources"]:
   resource_edit_dir=additional_workspace/"edited_parts"/resource["id"]
   if not resource_edit_dir.exists() or not any(resource_edit_dir.glob("*.png")):continue
   iso_path=resource["iso_path"];original_container,record=read_iso_file(iso,iso_path)
   valid,source_payload,error=verify_container_bytes(original_container)
   if not valid or source_payload is None:raise IntegratedBuildError(f"additional image container invalid: {iso_path}: {error or ''}")
   try:
    patched_payload,report=compose_payload(source_payload,resource,additional_workspace)
    allocated=((record.data_length+SECTOR_SIZE-1)//SECTOR_SIZE)*SECTOR_SIZE
    patched_container,container_report=build_image_container(patched_payload,allocated)
   except ValueError as exc:raise IntegratedBuildError(f"additional image patch failed: {resource['id']}: {exc}") from exc
   output=additional_dir/(resource["id"]+".dds.z");output.write_bytes(patched_container)
   report.update(container_report);report["iso_path"]=iso_path;additional_image_reports.append(report)
   extra_replacements.append(Replacement(iso_path,output,len(original_container),sha256(original_container)))
   runtime_copy_reports=sync_additional_runtime_copies(resource,original_container,patched_container,archive_cache,archive_original,lambda path:read_iso_file(iso,path)[0])
   report["runtime_copy_count"]=len(resource.get("runtime_copies",[]));report["runtime_copy_replaced_count"]=len(runtime_copy_reports);report["runtime_copies"]=runtime_copy_reports
   embedded=resource.get("embedded_runtime")
   picture_index=embedded.get("picture_index") if embedded else resource.get("embedded_picture_index")
   if picture_index is not None:
    try:static_payload,embedded_report=compose_collection_picture(static_payload,int(picture_index),resource,additional_workspace)
    except ValueError as exc:raise IntegratedBuildError(f"additional embedded image patch failed: {resource['id']}: {exc}") from exc
    report["embedded_picture_index"]=int(picture_index);report["embedded_changed_block_count"]=embedded_report["changed_block_count"]
  if static_payload is not None and any(r.get("embedded_picture_index") is not None or r.get("embedded_runtime") for r in additional_manifest["resources"] if (additional_workspace/"edited_parts"/r["id"]).exists() and any((additional_workspace/"edited_parts"/r["id"]).glob("*.png"))):
   static_container,static_container_report=build_image_container(static_payload,static_entry.allocated_size)
   patched_init=replace_file(patched_init,static_entry,static_container)
   (additional_dir/"static_tex.dds.z").write_bytes(static_container)
 if init_original is not None:
  misc_dir=args.work/"misc";misc_dir.mkdir(exist_ok=True);init_file=misc_dir/"init.bin";init_file.write_bytes(patched_init)
  extra_replacements.append(Replacement("PSP_GAME/USRDIR/data/arc/init.bin",init_file,len(init_original),sha256(init_original)))
 with tempfile.TemporaryDirectory(dir=args.work) as td:
  temp=Path(td)
  for number,group in enumerate(groups):
   runtime_targets=[]
   for runtime_key in group["runtime_keys"]:
    meta=runtime[runtime_key];arc_path=meta["archive_iso_path"]
    if arc_path not in archive_cache:
     data,_=read_iso_file(iso,arc_path);archive_cache[arc_path]=data;archive_original[arc_path]=data
    current=archive_cache[arc_path];entry=find_file(parse_archive(current),meta["entry_name"],index=int(meta["entry_index"]),flags=int(meta["flags_hex"],0));container=current[entry.offset:entry.offset+entry.size]
    valid,payload,error=verify_container_bytes(container)
    if not valid or payload is None or sha256(payload)!=group["xso_sha256"]:raise IntegratedBuildError(f"runtime payload mismatch: {runtime_key} {error or ''}")
    runtime_targets.append((runtime_key,meta,arc_path,entry,payload))
   if runtime_targets:
    container_payload=runtime_targets[0][4]
   else:
    container,_=read_iso_file(iso,group["standalone_paths"][0]);valid,container_payload,error=verify_container_bytes(container)
    if not valid or container_payload is None or sha256(container_payload)!=group["xso_sha256"]:raise IntegratedBuildError(f"runtime payload mismatch: {group['standalone_paths'][0]} {error or ''}")
   group_temp=temp/f"g{number}";group_temp.mkdir();rebuilt,report,rows=rebuild_group(container_payload,group,mapping,group_temp);compressed=build_container(rebuilt,9);valid,roundtrip,error=verify_container_bytes(compressed)
   if not valid or roundtrip!=rebuilt:raise IntegratedBuildError(f"compression verification failed: {error}")
   xso_path=args.work/"xso"/(group["xso_sha256"]+".xso");z_path=xso_path.with_suffix(".xso.z");xso_path.write_bytes(rebuilt);z_path.write_bytes(compressed)
   rebuilt_containers[group["xso_sha256"]]=(group,compressed)
   translation_rows+=rows
   if runtime_targets:
    for runtime_key,meta,arc_path,_original_entry,_payload in runtime_targets:
     current=archive_cache[arc_path];entry=find_file(parse_archive(current),meta["entry_name"],index=int(meta["entry_index"]),flags=int(meta["flags_hex"],0));remaining=entry.allocated_size-len(compressed)
     xso_rows.append({"xso_sha256":group["xso_sha256"],"runtime_key":runtime_key,"runtime_target_count":len(group["runtime_keys"]),"entry_flags_hex":f"0x{entry.flags:08X}","entry_kind":meta.get("entry_kind","regular"),**report,"compressed_size":len(compressed),"allocated_size":entry.allocated_size,"remaining_slack":remaining,"mapping_status":group["mapping_status"]})
     if remaining<0:overflow.append({"runtime_key":runtime_key,"compressed_size":len(compressed),"allocated_size":entry.allocated_size,"overflow":-remaining})
     else:archive_cache[arc_path]=replace_file(current,entry,compressed)
   else:
    xso_rows.append({"xso_sha256":group["xso_sha256"],"runtime_key":group["standalone_paths"][0],"runtime_target_count":0,"entry_flags_hex":"","entry_kind":"standalone",**report,"compressed_size":len(compressed),"allocated_size":"","remaining_slack":"","mapping_status":group["mapping_status"]})
 standalone_rows=[];standalone_replacements=[]
 standalone_targets=set(args.standalone_path)
 for group in groups:
  if group["runtime_key"] is None or group["mapping_status"]=="many_to_many":standalone_targets.update(group["standalone_paths"])
 for standalone_path in sorted(standalone_targets):
  matches=[(group,container) for group,container in rebuilt_containers.values() if standalone_path in group["standalone_paths"]]
  if len(matches)!=1:raise IntegratedBuildError(f"standalone path is not uniquely associated with a rebuilt group: {standalone_path}")
  group,container=matches[0];original,record=read_iso_file(iso,standalone_path);valid,payload,error=verify_container_bytes(original)
  if not valid or payload is None or sha256(payload)!=group["xso_sha256"]:raise IntegratedBuildError(f"standalone payload mismatch: {standalone_path} {error or ''}")
  allocated=((record.data_length+SECTOR_SIZE-1)//SECTOR_SIZE)*SECTOR_SIZE;remaining=allocated-len(container)
  standalone_rows.append({"iso_path":standalone_path,"runtime_key":" | ".join(group["runtime_keys"]),"original_size":len(original),"compressed_size":len(container),"allocated_size":allocated,"remaining_slack":remaining,"original_sha256":sha256(original),"output_sha256":sha256(container)})
  if remaining<0:overflow.append({"runtime_key":standalone_path,"compressed_size":len(container),"allocated_size":allocated,"overflow":-remaining})
  else:standalone_replacements.append(Replacement(standalone_path,args.work/"xso"/(group["xso_sha256"]+".xso.z"),len(original),sha256(original)))
 if overflow:
  preflight={"valid":False,"reason":"allocation_overflow","overflow":overflow,"reviewed_count":len(selected),"xso_count":len(groups)};(args.work/"preflight-report.json").write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");raise IntegratedBuildError("allocation overflow: "+json.dumps(overflow,ensure_ascii=False))
 archive_rows=[];iso_replacements=[]
 for arc_path,data in sorted(archive_cache.items()):
  name=Path(arc_path).name;out=args.work/"archives"/name;out.write_bytes(data);original=archive_original[arc_path];archive_rows.append({"iso_path":arc_path,"original_sha256":sha256(original),"output_sha256":sha256(data),"size":len(data),"modified_xso_count":sum(str(x["runtime_key"]).startswith(arc_path+"#") for x in xso_rows),"modified_additional_image_count":sum(copy["archive_path"]==arc_path for report in additional_image_reports for copy in report.get("runtime_copies",[]))})
  iso_replacements.append(Replacement(arc_path,out,len(original),sha256(original)))
 iso_replacements.extend(standalone_replacements)
 iso_replacements.extend(extra_replacements)
 original_iso_eboot,eboot_record=read_iso_file(iso,EBOOT_PATH);iso_replacements.insert(0,Replacement(EBOOT_PATH,args.work/"EBOOT.BIN",len(original_iso_eboot),sha256(original_iso_eboot)))
 expected_replacement_count=1+len(archive_rows)+len(standalone_rows)+len(extra_replacements)
 if len(iso_replacements)!=expected_replacement_count:raise IntegratedBuildError(f"ISO replacement count mismatch: expected={expected_replacement_count}, actual={len(iso_replacements)}")
 preflight={"valid":True,"override_count":len(selected),"reviewed_count":len(selected),"xso_count":len(groups),"archive_count":len(archive_rows),"standalone_count":len(standalone_rows),"castinfo_count":len(castinfo_rows),"item_count":len(item_rows),"system_message_count":len(system_rows),"option_menu_image_count":len(option_files),"option_menu_changed_block_count":option_menu_report["changed_dxt1_block_count"] if option_menu_report else 0,"additional_image_count":additional_count,"additional_image_resource_count":len(additional_image_reports),"additional_image_changed_block_count":sum(x["changed_block_count"] for x in additional_image_reports),"additional_image_runtime_copy_count":sum(x.get("runtime_copy_count",0) for x in additional_image_reports),"additional_image_runtime_copy_replaced_count":sum(x.get("runtime_copy_replaced_count",0) for x in additional_image_reports),"glyph_count":len(mapping),"overflow":[]};(args.work/"preflight-report.json").write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 write_csv(args.work/"translation-report.csv",translation_rows,["xso_sha256","runtime_key","string_index","source_text","translation","original_length","replacement_length","delta","origin_paths"]);write_csv(args.work/"xso-report.csv",xso_rows,["xso_sha256","runtime_key","entry_flags_hex","entry_kind","mapping_status","replacement_count","original_size","rebuilt_size","compressed_size","allocated_size","remaining_slack","original_sha256","rebuilt_sha256"]);write_csv(args.work/"archive-report.csv",archive_rows,["iso_path","size","modified_xso_count","modified_additional_image_count","original_sha256","output_sha256"])
 write_csv(args.work/"standalone-report.csv",standalone_rows,["iso_path","runtime_key","original_size","compressed_size","allocated_size","remaining_slack","original_sha256","output_sha256"])
 write_csv(args.work/"castinfo-report.csv",castinfo_rows,["identifier","source","name","encoded_name_hex","standalone_path","archive_path","entry_index","entry_flags_hex","size","changed_byte_count","original_sha256","output_sha256"])
 write_csv(args.work/"item-report.csv",item_rows,["index","resource_id","source_name","translation_name","translation_description","name_length","description_length"])
 write_csv(args.work/"system-message-report.csv",system_rows,["identifier","offset_hex","source","translation","allocated_size","encoded_length","encoded_hex"])
 manifest={"schema_version":1,"mode":args.mode,"inputs":{"iso":str(iso),"iso_sha256":EXPECTED_ISO_SHA256,"workspace":str(args.workspace),"workspace_sha256":file_sha256(args.workspace),"cast_name_workspace":str(args.cast_name_workspace) if args.cast_name_workspace else None,"cast_name_workspace_sha256":file_sha256(args.cast_name_workspace) if args.cast_name_workspace else None,"item_workspace":str(args.item_workspace) if getattr(args,"item_workspace",None) else None,"item_workspace_sha256":file_sha256(args.item_workspace) if getattr(args,"item_workspace",None) else None,"system_message_workspace":str(args.system_message_workspace) if getattr(args,"system_message_workspace",None) else None,"system_message_workspace_sha256":file_sha256(args.system_message_workspace) if getattr(args,"system_message_workspace",None) else None,"catalog_sha256":file_sha256(args.catalog),"runtime_map_sha256":file_sha256(args.runtime_map),"original_eboot_sha256":file_sha256(args.original_eboot),"seed_mapping_sha256":file_sha256(args.seed_mapping)},"font":{"visible_width":12,"horizontal_left_inset":args.horizontal_left_inset},"summary":preflight,"eboot":{"sha256":sha256(patched_eboot)},"xso":xso_rows,"archives":archive_rows,"castinfo":castinfo_rows,"items":item_rows,"system_messages":system_rows,"option_menu":option_menu_report,"additional_images":additional_image_reports,"iso":None,"valid":True}
 if args.mode=="build":
  result=patch_atomic(iso,args.output_iso,iso_replacements,EXPECTED_ISO_SHA256,args.overwrite);manifest["iso"]={"path":str(args.output_iso),**result}
 (args.work/"build-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return manifest

def main(argv=None):
 for s in (sys.stdout,sys.stderr):
  if hasattr(s,"reconfigure"):s.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=("preflight","build"));p.add_argument("--iso",type=Path,required=True);p.add_argument("--workspace",type=Path,required=True);p.add_argument("--catalog",type=Path,required=True);p.add_argument("--runtime-map",type=Path,required=True);p.add_argument("--font-usage",type=Path,required=True);p.add_argument("--seed-mapping",type=Path,required=True);p.add_argument("--original-eboot",type=Path,required=True);p.add_argument("--font",type=Path,required=True);p.add_argument("--han-override",type=Path,required=True);p.add_argument("--horizontal-left-inset",type=int);p.add_argument("--cast-name-workspace",type=Path);p.add_argument("--item-workspace",type=Path);p.add_argument("--system-message-workspace",type=Path);p.add_argument("--option-menu-workspace",type=Path);p.add_argument("--option-menu-source",type=Path);p.add_argument("--additional-image-workspace",type=Path);p.add_argument("--castinfo-name");p.add_argument("--castinfo-identifier",default="CAST_C240");p.add_argument("--castinfo-expected-name",default="イーシャ");p.add_argument("--work",type=Path,required=True);p.add_argument("--standalone-path",action="append",default=[]);p.add_argument("--output-iso",type=Path);p.add_argument("--overwrite",action="store_true");a=p.parse_args(argv)
 if a.mode=="build" and a.output_iso is None:p.error("build requires --output-iso")
 try:result=execute(a);print(json.dumps(result["summary"],ensure_ascii=False,indent=2));return 0
 except (OSError,KeyError,ValueError,json.JSONDecodeError,IntegratedBuildError) as exc:print(f"통합 빌드 실패: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
