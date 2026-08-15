#!/usr/bin/env python3
"""Read-only search for byte patterns in a running PPSSPP process on Windows."""
from __future__ import annotations
import argparse,ctypes,ctypes.wintypes as wt,json,sys
from pathlib import Path

PROCESS_QUERY_INFORMATION=0x0400;PROCESS_VM_READ=0x0010;MEM_COMMIT=0x1000
PAGE_GUARD=0x100;PAGE_NOACCESS=0x01
READABLE={0x02,0x04,0x08,0x20,0x40,0x80}
kernel32=ctypes.WinDLL("kernel32",use_last_error=True)

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
 _fields_=[("BaseAddress",ctypes.c_void_p),("AllocationBase",ctypes.c_void_p),("AllocationProtect",wt.DWORD),("PartitionId",wt.WORD),("RegionSize",ctypes.c_size_t),("State",wt.DWORD),("Protect",wt.DWORD),("Type",wt.DWORD)]

def find_all(data:bytes,needle:bytes):
 start=0
 while True:
  pos=data.find(needle,start)
  if pos<0:return
  yield pos;start=pos+1

def search(pid:int,patterns:list[tuple[str,bytes]],list_regions:bool=False,min_region_size:int=0)->dict:
 handle=kernel32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,False,pid)
 if not handle:raise OSError(ctypes.get_last_error(),"OpenProcess failed")
 hits={name:[] for name,_ in patterns};regions=0;read_bytes=0;address=0;mbi=MEMORY_BASIC_INFORMATION();region_list=[]
 try:
  while kernel32.VirtualQueryEx(handle,ctypes.c_void_p(address),ctypes.byref(mbi),ctypes.sizeof(mbi)):
   base=int(mbi.BaseAddress or 0);size=int(mbi.RegionSize);protect=int(mbi.Protect)
   if mbi.State==MEM_COMMIT and not protect&PAGE_GUARD and not protect&PAGE_NOACCESS and protect&0xFF in READABLE and size<=512*1024*1024:
    if list_regions and size>=min_region_size:region_list.append({"base":f"0x{base:016X}","size":size,"protect":f"0x{protect:X}"})
    buffer=ctypes.create_string_buffer(size);read=ctypes.c_size_t()
    if kernel32.ReadProcessMemory(handle,ctypes.c_void_p(base),buffer,size,ctypes.byref(read)) and read.value:
     data=buffer.raw[:read.value];regions+=1;read_bytes+=read.value
     for name,needle in patterns:
      for offset in find_all(data,needle):hits[name].append({"host_address":f"0x{base+offset:016X}","region_base":f"0x{base:016X}","region_size":size,"offset":offset})
   next_address=base+size
   if next_address<=address:break
   address=next_address
  return {"pid":pid,"regions_read":regions,"bytes_read":read_bytes,"readable_regions":region_list,"patterns":[{"name":name,"size":len(data),"hits":hits[name]} for name,data in patterns]}
 finally:kernel32.CloseHandle(handle)

def main(argv=None):
 if sys.platform!="win32":raise SystemExit("Windows only")
 if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("pid",type=int);p.add_argument("--pattern",action="append",default=[],help="NAME=FILE");p.add_argument("--slice-pattern",action="append",default=[],help="NAME=FILE:OFFSET:LENGTH");p.add_argument("--hex-pattern",action="append",default=[],help="NAME=HEX");p.add_argument("--list-regions",action="store_true");p.add_argument("--min-region-size",type=lambda value:int(value,0),default=0);p.add_argument("--output",type=Path);a=p.parse_args(argv)
 patterns=[]
 for value in a.pattern:
  name,sep,path=value.partition("=")
  if not sep:raise ValueError(f"invalid pattern: {value}")
  patterns.append((name,Path(path).read_bytes()))
 for value in a.slice_pattern:
  name,sep,spec=value.partition("=")
  if not sep:raise ValueError(f"invalid slice pattern: {value}")
  path_text,offset_text,length_text=spec.rsplit(":",2)
  raw=Path(path_text).read_bytes();offset=int(offset_text,0);length=int(length_text,0)
  patterns.append((name,raw[offset:offset+length]))
 for value in a.hex_pattern:
  name,sep,raw_hex=value.partition("=")
  if not sep:raise ValueError(f"invalid hex pattern: {value}")
  patterns.append((name,bytes.fromhex(raw_hex)))
 if not patterns and not a.list_regions:raise ValueError("at least one pattern or --list-regions is required")
 result=search(a.pid,patterns,a.list_regions,a.min_region_size);rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8")
 print(rendered,end="");return 0
if __name__=="__main__":raise SystemExit(main())
