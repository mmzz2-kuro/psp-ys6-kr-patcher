#!/usr/bin/env python3
"""Probe Ys VI MIPS ELFs for PSP analog-axis access and controller imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

from iso9660_info import SECTOR_SIZE, find_record


CTRL_NIDS = {
    0x3A622550: "sceCtrlPeekBufferPositive",
    0x1F803938: "sceCtrlReadBufferPositive",
    0x1F4011E6: "sceCtrlSetSamplingMode",
    0x6A2774F3: "sceCtrlSetSamplingCycle",
    0xC152080A: "sceCtrlPeekBufferNegative",
    0x60B81F86: "sceCtrlReadBufferNegative",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def extract(iso: Path, internal_path: str) -> bytes:
    record = find_record(iso, internal_path)
    with iso.open("rb") as handle:
        handle.seek(record.extent_lba * SECTOR_SIZE); data = handle.read(record.data_length)
    return data


def elf_exec_ranges(data: bytes) -> list[tuple[int, int, int]]:
    if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
        raise ValueError("ELF32 little-endian 파일이 아닙니다")
    phoff = struct.unpack_from("<I", data, 0x1C)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 0x2A)
    ranges = []
    for index in range(phnum):
        off = phoff + index * phentsize
        p_type, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, p_flags, _p_align = struct.unpack_from("<IIIIIIII", data, off)
        if p_type == 1 and p_filesz and p_flags & 1:
            ranges.append((p_offset, p_offset + p_filesz, p_vaddr))
    return ranges


def elf_sections(data: bytes) -> list[dict[str, object]]:
    shoff=struct.unpack_from("<I",data,0x20)[0];shentsize,shnum,shstrndx=struct.unpack_from("<HHH",data,0x2E)
    headers=[struct.unpack_from("<IIIIIIIIII",data,shoff+i*shentsize) for i in range(shnum)]
    string_header=headers[shstrndx];strings=data[string_header[4]:string_header[4]+string_header[5]]
    result=[]
    for index,header in enumerate(headers):
        name_off=header[0];end=strings.find(b"\0",name_off);name=strings[name_off:end].decode("ascii","replace") if 0<=name_off<len(strings) else ""
        result.append({"index":index,"name":name,"type":header[1],"flags":header[2],"address":header[3],"offset":header[4],"size":header[5],"entry_size":header[9]})
    return result


def reg(index: int) -> str:
    names = ("zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
             "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra")
    return names[index]


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def decode(word: int, pc: int) -> str:
    op, rs, rt, rd, imm, funct = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31, word & 0xFFFF, word & 63
    if word == 0: return "nop"
    if op in (0x20, 0x24, 0x21, 0x25, 0x23, 0x28, 0x29, 0x2B):
        names = {0x20:"lb",0x24:"lbu",0x21:"lh",0x25:"lhu",0x23:"lw",0x28:"sb",0x29:"sh",0x2B:"sw"}
        return f"{names[op]} {reg(rt)},{signed16(imm)}({reg(rs)})"
    if op in (0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F):
        names={0x08:"addi",0x09:"addiu",0x0A:"slti",0x0B:"sltiu",0x0C:"andi",0x0D:"ori",0x0E:"xori",0x0F:"lui"}
        return f"{names[op]} {reg(rt)},{reg(rs)},{signed16(imm) if op not in (0x0C,0x0D,0x0E,0x0F) else imm:#x}"
    if op in (0x04,0x05): return f"{'beq' if op==4 else 'bne'} {reg(rs)},{reg(rt)},0x{pc+4+(signed16(imm)<<2):08X}"
    if op in (0x02,0x03): return f"{'j' if op==2 else 'jal'} 0x{((pc+4)&0xF0000000)|((word&0x03FFFFFF)<<2):08X}"
    if op == 0 and funct in (0x20,0x21,0x22,0x23,0x24,0x25,0x2A,0x2B):
        names={0x20:"add",0x21:"addu",0x22:"sub",0x23:"subu",0x24:"and",0x25:"or",0x2A:"slt",0x2B:"sltu"}
        return f"{names[funct]} {reg(rd)},{reg(rs)},{reg(rt)}"
    if op == 0 and funct == 0x08: return f"jr {reg(rs)}"
    return f".word 0x{word:08X}"


def dump_address_range(data: bytes, start: int, end: int) -> list[dict[str, object]]:
    text=next(section for section in elf_sections(data) if section["name"]==".text")
    delta=int(text["offset"])-int(text["address"]);rows=[]
    for address in range(start,end,4):
        offset=address+delta;word=struct.unpack_from("<I",data,offset)[0]
        rows.append({"file_offset":offset,"address":f"0x{address:08X}","word":f"0x{word:08X}","asm":decode(word,address)})
    return rows


def probe(data: bytes, output: Path) -> dict[str, object]:
    output.write_bytes(data)
    ranges = elf_exec_ranges(data)
    words: list[tuple[int,int,int]] = []
    for start, end, vaddr in ranges:
        for off in range(start, end - 3, 4):
            words.append((off, vaddr + off - start, struct.unpack_from("<I", data, off)[0]))
    hits = []
    for index, (off, pc, word) in enumerate(words):
        op, base, offset = word >> 26, (word >> 21) & 31, signed16(word & 0xFFFF)
        if op != 0x24 or offset not in (8, 9):
            continue
        nearby = []
        for candidate_index in range(max(0,index-12), min(len(words),index+13)):
            _o,_pc,w = words[candidate_index]
            if w >> 26 == 0x24 and ((w >> 21) & 31) == base and signed16(w & 0xFFFF) in (8,9):
                nearby.append(signed16(w & 0xFFFF))
        if set(nearby) != {8,9}:
            continue
        context=[]
        for _off,_pc,w in words[max(0,index-10):min(len(words),index+15)]:
            context.append({"file_offset":_off,"address":f"0x{_pc:08X}","word":f"0x{w:08X}","asm":decode(w,_pc)})
        hits.append({"file_offset":off,"address":f"0x{pc:08X}","base_register":reg(base),"axis_offset":offset,"context":context})
    # Collapse paired Lx/Ly hits that share the same short context.
    unique=[]; seen=set()
    for hit in hits:
        key=(hit["base_register"],tuple(row["file_offset"] for row in hit["context"]))
        if key not in seen:seen.add(key);unique.append(hit)
    sections=elf_sections(data);section_by_name={row["name"]:row for row in sections}
    nid_hits=[]
    for nid,name in CTRL_NIDS.items():
        needle=struct.pack("<I",nid);positions=[];start=0
        while (pos:=data.find(needle,start))>=0:positions.append(pos);start=pos+1
        if positions:
            details=[]
            nid_section=section_by_name.get(".rodata.sceNid");stub_section=section_by_name.get(".sceStub.text")
            for pos in positions:
                detail={"nid_file_offset":pos}
                if nid_section and stub_section and nid_section["offset"]<=pos<nid_section["offset"]+nid_section["size"]:
                    index=(pos-nid_section["offset"])//4;stub_off=stub_section["offset"]+index*8;stub_addr=stub_section["address"]+index*8
                    calls=[]
                    for word_off,pc,word in words:
                        if word>>26==0x03 and (((pc+4)&0xF0000000)|((word&0x03FFFFFF)<<2))==stub_addr:
                            context=[{"file_offset":o,"address":f"0x{p:08X}","word":f"0x{w:08X}","asm":decode(w,p)} for o,p,w in words[max(0,words.index((word_off,pc,word))-8):words.index((word_off,pc,word))+10]]
                            calls.append({"file_offset":word_off,"address":f"0x{pc:08X}","context":context})
                    detail.update({"global_index":index,"stub_file_offset":stub_off,"stub_address":f"0x{stub_addr:08X}","stub_hex":data[stub_off:stub_off+8].hex().upper(),"calls":calls})
                details.append(detail)
            nid_hits.append({"nid":f"0x{nid:08X}","name":name,"details":details})
    strings=[]
    for needle in (b"sceCtrl", b"sceController_Service"):
        start=0
        while (pos:=data.find(needle,start))>=0:
            end=data.find(b"\0",pos);strings.append({"offset":pos,"text":data[pos:end if end>=0 else pos+80].decode("ascii","replace")});start=pos+1
    return {"size":len(data),"sha256":sha(data),"exec_ranges":ranges,"sections":sections,"controller_nids":nid_hits,
            "controller_strings":strings,"axis_pair_candidate_count":len(unique),"axis_pair_candidates":unique}


def main() -> int:
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8",errors="backslashreplace")
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("first_iso",type=Path);parser.add_argument("second_iso",type=Path);parser.add_argument("output",type=Path);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    first_data=extract(args.first_iso,"PSP_GAME/SYSDIR/BOOT.BIN");second_data=extract(args.second_iso,"PSP_GAME/SYSDIR/BOOT.BIN")
    first=probe(first_data,args.output/"ULJM05009-BOOT.BIN");second=probe(second_data,args.output/"ULJM05155-BOOT.BIN")
    first["controller_read_function"]=dump_address_range(first_data,0x000E0B28,0x000E0BC0)
    second["controller_read_function"]=dump_address_range(second_data,0x00105C20,0x00105D44)
    report={"schema_version":1,"first":first,"second":second}
    (args.output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"first":{k:first[k] for k in ("size","sha256","controller_nids","controller_strings","axis_pair_candidate_count")},"second":{k:second[k] for k in ("size","sha256","controller_nids","controller_strings","axis_pair_candidate_count")}},ensure_ascii=False,indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
