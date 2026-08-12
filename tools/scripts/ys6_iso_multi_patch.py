#!/usr/bin/env python3
"""Atomically replace multiple fixed-extent files in a Ys VI ISO copy."""
from __future__ import annotations
import argparse, hashlib, json, math, os, shutil, struct, sys
from dataclasses import dataclass
from pathlib import Path
try:
    from tools.scripts.iso9660_info import DirectoryRecord, SECTOR_SIZE, find_record
    from tools.scripts.ys6_iso_patch import IsoPatchError, collect_difference_ranges, range_is_allowed, read_and_verify_record, sha256_file
except ModuleNotFoundError:
    from iso9660_info import DirectoryRecord, SECTOR_SIZE, find_record
    from ys6_iso_patch import IsoPatchError, collect_difference_ranges, range_is_allowed, read_and_verify_record, sha256_file

@dataclass(frozen=True)
class Replacement:
    internal_path: str
    source_file: Path
    expected_size: int
    expected_sha256: str

def sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest().upper()

def validate_targets(records: list[tuple[Replacement, DirectoryRecord, bytes]]) -> None:
    ranges=[]
    for replacement, record, data in records:
        if record.is_directory: raise IsoPatchError(f"대상이 디렉터리입니다: {replacement.internal_path}")
        allocated=math.ceil(record.data_length/SECTOR_SIZE)*SECTOR_SIZE
        if len(data)>allocated: raise IsoPatchError(f"교체 파일이 기존 할당 공간을 초과합니다: {replacement.internal_path}")
        ranges.append((record.extent_lba*SECTOR_SIZE,record.extent_lba*SECTOR_SIZE+allocated,replacement.internal_path))
    ranges.sort()
    for left,right in zip(ranges,ranges[1:]):
        if left[1]>right[0]: raise IsoPatchError(f"교체 extent가 중첩됩니다: {left[2]} / {right[2]}")

def apply_records(source: Path, output: Path, records: list[tuple[Replacement, DirectoryRecord, bytes]], overwrite: bool) -> None:
    if source.resolve()==output.resolve(): raise IsoPatchError("원본 ISO와 출력 ISO 경로가 같습니다")
    if output.exists() and not overwrite: raise IsoPatchError(f"출력 ISO가 이미 존재합니다: {output}")
    validate_targets(records); output.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,output)
    with output.open("r+b") as handle:
        for _replacement,record,data in records:
            allocated=math.ceil(record.data_length/SECTOR_SIZE)*SECTOR_SIZE
            handle.seek(record.extent_lba*SECTOR_SIZE); handle.write(data); handle.write(bytes(allocated-len(data)))
            handle.seek(record.record_byte_offset+10); handle.write(struct.pack("<I",len(data)))
            handle.seek(record.record_byte_offset+14); handle.write(struct.pack(">I",len(data)))
        handle.flush()

def patch_atomic(source: Path, output: Path, replacements: list[Replacement], expected_iso_sha256: str, overwrite: bool) -> dict:
    actual=sha256_file(source)
    if actual!=expected_iso_sha256.upper(): raise IsoPatchError(f"원본 ISO SHA-256 불일치: expected={expected_iso_sha256.upper()}, actual={actual}")
    prepared=[]
    with source.open("rb") as handle:
        for item in replacements:
            record=find_record(source,item.internal_path); read_and_verify_record(handle,record)
            handle.seek(record.extent_lba*SECTOR_SIZE); original=handle.read(record.data_length)
            if record.data_length!=item.expected_size or sha256(original)!=item.expected_sha256.upper():
                raise IsoPatchError(f"원본 내부 파일 검증 실패: {item.internal_path}")
            prepared.append((item,record,item.source_file.read_bytes()))
    temporary=output.with_name(output.name+".partial")
    if temporary.exists(): temporary.unlink()
    try:
        apply_records(source,temporary,prepared,False)
        allowed=[]; entries=[]
        for item,record,data in prepared:
            patched=find_record(temporary,item.internal_path)
            with temporary.open("rb") as handle:
                read_and_verify_record(handle,patched); handle.seek(patched.extent_lba*SECTOR_SIZE); reread=handle.read(patched.data_length)
            if reread!=data or patched.extent_lba!=record.extent_lba: raise IsoPatchError(f"패치 후 검증 실패: {item.internal_path}")
            allocated=math.ceil(record.data_length/SECTOR_SIZE)*SECTOR_SIZE
            allowed += [(record.record_byte_offset+10,record.record_byte_offset+14),(record.record_byte_offset+14,record.record_byte_offset+18),(record.extent_lba*SECTOR_SIZE,record.extent_lba*SECTOR_SIZE+allocated)]
            entries.append({"internal_path":item.internal_path,"size":len(data),"sha256":sha256(data),"extent_lba":record.extent_lba})
        differences=collect_difference_ranges(source,temporary); outside=[vars(x) for x in differences if not range_is_allowed(x,allowed)]
        if outside: raise IsoPatchError(f"허용 범위 밖 변경이 있습니다: {outside}")
        if output.exists():
            if not overwrite: raise IsoPatchError(f"출력 ISO가 이미 존재합니다: {output}")
        os.replace(temporary,output)
        return {"source_iso_sha256":actual,"output_iso_sha256":sha256_file(output),"iso_size":output.stat().st_size,"replacement_count":len(entries),"entries":entries,"difference_range_count":len(differences),"outside_allowed_ranges":[],"valid":True}
    finally:
        temporary.unlink(missing_ok=True)

def main(argv=None):
    for s in (sys.stdout,sys.stderr):
        if hasattr(s,"reconfigure"): s.reconfigure(encoding="utf-8",errors="backslashreplace")
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("source",type=Path); p.add_argument("manifest",type=Path); p.add_argument("output",type=Path); p.add_argument("--expected-iso-sha256",required=True); p.add_argument("--overwrite",action="store_true"); a=p.parse_args(argv)
    try:
        doc=json.loads(a.manifest.read_text(encoding="utf-8-sig")); replacements=[Replacement(x["internal_path"],Path(x["source_file"]),int(x["expected_size"]),x["expected_sha256"]) for x in doc["replacements"]]
        result=patch_atomic(a.source,a.output,replacements,a.expected_iso_sha256,a.overwrite); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except (OSError,KeyError,ValueError,json.JSONDecodeError,IsoPatchError) as exc: print(f"다중 ISO 패치 실패: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
