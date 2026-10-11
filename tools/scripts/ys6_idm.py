#!/usr/bin/env python3
"""Parse and rebuild Ys VI SPECIAL VERSION IDM dialogue resources."""
from __future__ import annotations
import hashlib,struct

def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest().upper()

def parse_idm(data:bytes)->dict:
 if not data:return {"count":0,"version":1,"records":[],"strings":[],"size":0,"sha256":sha256(data),"empty":True}
 if len(data)<0x10:raise ValueError("IDM header truncated")
 count,version,zero1,zero2=struct.unpack_from("<IIII",data,0)
 if version!=1 or zero1 or zero2:raise ValueError("unsupported IDM header")
 pos=0x10;records=[];strings=[]
 for record_index in range(count):
  if pos+12>len(data):raise ValueError(f"IDM record header truncated: {record_index}")
  record_id,string_count,argument_count=struct.unpack_from("<III",data,pos);pos+=12
  if string_count>256 or argument_count>1024:raise ValueError(f"IDM unreasonable record counts: {record_index}")
  if pos+argument_count*4>len(data):raise ValueError(f"IDM arguments truncated: {record_index}")
  arguments=list(struct.unpack_from("<"+"I"*argument_count,data,pos)) if argument_count else [];pos+=argument_count*4;values=[]
  for string_index in range(string_count):
   if pos+4>len(data):raise ValueError(f"IDM string length truncated: {record_index}:{string_index}")
   length=struct.unpack_from("<I",data,pos)[0];pos+=4
   if pos+length>len(data):raise ValueError(f"IDM string truncated: {record_index}:{string_index}")
   raw=data[pos:pos+length];pos+=length
   try:text=raw.decode("cp932")
   except UnicodeDecodeError as exc:raise ValueError(f"IDM CP932 decode failed: {record_index}:{string_index}: {exc}") from exc
   strings.append({"flat_index":len(strings),"record_index":record_index,"record_id":record_id,"string_index":string_index,"raw":raw,"raw_hex":raw.hex().upper(),"text":text,"sha256":sha256(raw)});values.append(raw)
  records.append({"record_id":record_id,"arguments":arguments,"strings":values})
 if pos!=len(data):raise ValueError(f"IDM trailing bytes: {len(data)-pos}")
 return {"count":count,"version":version,"records":records,"strings":strings,"size":len(data),"sha256":sha256(data)}

def rebuild_idm(parsed:dict,replacements:dict[int,bytes]|None=None)->bytes:
 if parsed.get("empty"):
  if replacements:raise ValueError("cannot replace strings in empty IDM")
  return b""
 replacements=replacements or {};out=bytearray(struct.pack("<IIII",parsed["count"],1,0,0));flat=0
 for record in parsed["records"]:
  values=[]
  for raw in record["strings"]:values.append(replacements.get(flat,raw));flat+=1
  out.extend(struct.pack("<III",record["record_id"],len(values),len(record["arguments"])))
  if record["arguments"]:out.extend(struct.pack("<"+"I"*len(record["arguments"]),*record["arguments"]))
  for raw in values:out.extend(struct.pack("<I",len(raw)));out.extend(raw)
 result=bytes(out);check=parse_idm(result)
 if check["count"]!=parsed["count"] or len(check["strings"])!=len(parsed["strings"]):raise ValueError("IDM rebuild verification failed")
 return result
