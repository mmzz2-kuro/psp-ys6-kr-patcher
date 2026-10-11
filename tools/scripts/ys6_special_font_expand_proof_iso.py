#!/usr/bin/env python3
"""Build the issue-110 expanded-font proof ISO from the verified issue-109 ISO."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record
    from tools.scripts.ys6_arc import parse_archive, replace_file
    from tools.scripts.ys6_hangul_codec import encode_translation
    from tools.scripts.ys6_idm import parse_idm, rebuild_idm, sha256
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, find_record
    from ys6_arc import parse_archive, replace_file
    from ys6_hangul_codec import encode_translation
    from ys6_idm import parse_idm, rebuild_idm, sha256


BASE_ISO_SHA256 = "B610AF62DCFC476DD27D57ACDC0201B3E5E96DE166ED9722EC5F74D8E447B092"
IDM_PATH = "PSP_GAME/USRDIR/data/idm/s_05/s_0551/s_scene.idm"
PROOF_TRANSLATIONS = {
    0: "무슨 일이 생겼니, 이샤?",
    2: "어쩐지……\n바람이 술렁이는 느낌이 들어서……",
}


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_iso(path: Path, internal_path: str) -> tuple[bytes, object]:
    record = find_record(path, internal_path)
    with path.open("rb") as stream:
        stream.seek(record.extent_lba * SECTOR_SIZE)
        data = stream.read(record.data_length)
    if len(data) != record.data_length:
        raise OSError(f"short ISO read: {internal_path}")
    return data, record


def write_fixed(handle, record, data: bytes) -> None:
    allocated = math.ceil(record.data_length / SECTOR_SIZE) * SECTOR_SIZE
    if len(data) > allocated:
        raise ValueError(f"fixed extent overflow: {len(data)} > {allocated}")
    handle.seek(record.extent_lba * SECTOR_SIZE); handle.write(data); handle.write(bytes(allocated - len(data)))
    handle.seek(record.record_byte_offset + 10); handle.write(struct.pack("<I", len(data)))
    handle.seek(record.record_byte_offset + 14); handle.write(struct.pack(">I", len(data)))


def append_extent(handle, record, data: bytes) -> dict:
    handle.seek(0, 2); end = handle.tell(); aligned = math.ceil(end / SECTOR_SIZE) * SECTOR_SIZE
    handle.write(bytes(aligned - end)); lba = aligned // SECTOR_SIZE; handle.write(data)
    handle.write(bytes(math.ceil(len(data) / SECTOR_SIZE) * SECTOR_SIZE - len(data)))
    handle.seek(record.record_byte_offset + 2); handle.write(struct.pack("<I", lba))
    handle.seek(record.record_byte_offset + 6); handle.write(struct.pack(">I", lba))
    handle.seek(record.record_byte_offset + 10); handle.write(struct.pack("<I", len(data)))
    handle.seek(record.record_byte_offset + 14); handle.write(struct.pack(">I", len(data)))
    return {"extent_lba": lba, "size": len(data), "sha256": sha256(data)}


def update_volume_space(handle) -> int:
    handle.seek(0, 2); size = handle.tell()
    if size % SECTOR_SIZE:
        raise ValueError("ISO output is not sector aligned")
    sectors = size // SECTOR_SIZE
    sector = PVD_SECTOR
    while True:
        handle.seek(sector * SECTOR_SIZE); descriptor = handle.read(SECTOR_SIZE)
        if len(descriptor) != SECTOR_SIZE or descriptor[1:6] != b"CD001":
            raise ValueError("invalid volume descriptor sequence")
        kind = descriptor[0]
        if kind in (1, 2):
            handle.seek(sector * SECTOR_SIZE + 80); handle.write(struct.pack("<I", sectors)); handle.write(struct.pack(">I", sectors))
        if kind == 255:
            break
        sector += 1
    return sectors


def build(args) -> dict:
    if file_sha(args.iso) != BASE_ISO_SHA256:
        raise ValueError("issue-109 base ISO SHA-256 mismatch")
    expansion = json.loads(args.expansion_report.read_text(encoding="utf-8"))
    mapping = expansion["mappings"]
    if not {"겼", "낌"}.issubset({row["character"] for row in mapping}):
        raise ValueError("proof glyphs are absent from expanded mapping")
    original_idm, idm_record = read_iso(args.iso, IDM_PATH)
    parsed = parse_idm(original_idm)
    replacements = {index: encode_translation(text, mapping) for index, text in PROOF_TRANSLATIONS.items()}
    patched_idm = rebuild_idm(parsed, replacements)
    verified = parse_idm(patched_idm)
    for index, text in PROOF_TRANSLATIONS.items():
        if verified["strings"][index]["raw"] != replacements[index]:
            raise ValueError(f"IDM proof verification failed at {index}")
    runtime = json.loads(args.runtime_map.read_text(encoding="utf-8-sig"))
    resource = next(row for row in runtime["resources"] if row["iso_path"] == IDM_PATH)
    if len(resource["copies"]) != 1:
        raise ValueError("unexpected early IDM runtime copy count")
    copy = resource["copies"][0]; archive_path = copy["archive_path"]
    archive, archive_record = read_iso(args.iso, archive_path)
    entry = next(row for row in parse_archive(archive)
                 if row.index == int(copy["entry_index"]) and row.name == copy["entry_name"])
    if archive[entry.offset:entry.offset + entry.size] != original_idm:
        raise ValueError("runtime IDM source differs from standalone IDM")
    patched_archive = replace_file(archive, entry, patched_idm)
    boot = args.boot.read_bytes(); eboot = args.eboot.read_bytes()
    boot_record = find_record(args.iso, "PSP_GAME/SYSDIR/BOOT.BIN")
    eboot_record = find_record(args.iso, "PSP_GAME/SYSDIR/EBOOT.BIN")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(args.output)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    if temporary.exists(): temporary.unlink()
    shutil.copyfile(args.iso, temporary)
    try:
        with temporary.open("r+b") as handle:
            write_fixed(handle, idm_record, patched_idm)
            write_fixed(handle, archive_record, patched_archive)
            boot_result = append_extent(handle, boot_record, boot)
            eboot_result = append_extent(handle, eboot_record, eboot)
            volume_sectors = update_volume_space(handle)
        temporary.replace(args.output)
    except Exception:
        if temporary.exists(): temporary.unlink()
        raise
    reread_boot, reread_boot_record = read_iso(args.output, "PSP_GAME/SYSDIR/BOOT.BIN")
    reread_eboot, reread_eboot_record = read_iso(args.output, "PSP_GAME/SYSDIR/EBOOT.BIN")
    reread_idm, _ = read_iso(args.output, IDM_PATH); reread_archive, _ = read_iso(args.output, archive_path)
    reread_entry = next(row for row in parse_archive(reread_archive) if row.index == entry.index and row.name == entry.name)
    if reread_boot != boot or reread_eboot != eboot or reread_idm != patched_idm:
        raise ValueError("ISO re-extraction mismatch")
    if reread_archive[reread_entry.offset:reread_entry.offset + reread_entry.size] != patched_idm:
        raise ValueError("runtime IDM re-extraction mismatch")
    report = {"valid": True, "base_iso_sha256": BASE_ISO_SHA256,
              "output_iso": str(args.output), "output_iso_size": args.output.stat().st_size,
              "output_iso_sha256": file_sha(args.output), "volume_space_sectors": volume_sectors,
              "boot": {**boot_result, "verified_lba": reread_boot_record.extent_lba},
              "eboot": {**eboot_result, "verified_lba": reread_eboot_record.extent_lba},
              "proof_idm": {"path": IDM_PATH, "standalone_sha256": sha256(patched_idm),
                            "runtime_archive": archive_path, "translations": PROOF_TRANSLATIONS}}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path); parser.add_argument("boot", type=Path); parser.add_argument("eboot", type=Path)
    parser.add_argument("expansion_report", type=Path); parser.add_argument("runtime_map", type=Path)
    parser.add_argument("output", type=Path); parser.add_argument("report", type=Path)
    parser.add_argument("--overwrite", action="store_true"); args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
