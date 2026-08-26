#!/usr/bin/env python3
"""Precompile and validate the Ys VI option-menu image container cache."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_arc import find_file, parse_archive
    from tools.scripts.ys6_option_menu_image import compose
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record
    from ys6_arc import find_file, parse_archive
    from ys6_option_menu_image import compose
    from ys6_z import verify_container_bytes

CACHE_SCHEMA_VERSION = 1
ALGORITHM_VERSION = "ys6-option-menu-dxt1-v1"
SOURCE_ISO_SHA256 = "0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B"
STANDALONE_PATH = "PSP_GAME/USRDIR/data/image/static_tex.dds.z"
INIT_PATH = "PSP_GAME/USRDIR/data/arc/init.bin"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest().upper()


def read_iso_file(iso: Path, internal_path: str) -> tuple[bytes, object]:
    record = find_record(iso, internal_path)
    with iso.open("rb") as stream:
        stream.seek(record.extent_lba * SECTOR_SIZE); data = stream.read(record.data_length)
    if len(data) != record.data_length: raise OSError(f"short ISO read: {internal_path}")
    return data, record


def source_context(iso: Path, workspace: Path) -> dict:
    if sha256_file(iso) != SOURCE_ISO_SHA256: raise ValueError("지원하는 원본 ISO의 SHA-256이 아닙니다")
    standalone, standalone_record = read_iso_file(iso, STANDALONE_PATH)
    valid, payload, error = verify_container_bytes(standalone)
    if not valid or payload is None: raise ValueError(f"option-menu standalone container invalid: {error or ''}")
    source_payload = (workspace / "original-static_tex.dds").read_bytes()
    if payload != source_payload: raise ValueError("option-menu source payload does not match original ISO")
    init_data, _init_record = read_iso_file(iso, INIT_PATH)
    entry = find_file(parse_archive(init_data), "static_tex.dds.z", index=29, flags=0x01000000)
    embedded = init_data[entry.offset:entry.offset + entry.size]
    valid, embedded_payload, error = verify_container_bytes(embedded)
    if not valid or embedded_payload != source_payload: raise ValueError(f"option-menu embedded container mismatch: {error or ''}")
    standalone_allocation = ((standalone_record.data_length + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE
    allocation = min(standalone_allocation, entry.allocated_size)
    return {"standalone": standalone, "payload": source_payload, "embedded": embedded,
            "standalone_allocation": standalone_allocation, "embedded_allocation": entry.allocated_size,
            "allocation": allocation}


def cache_identity(iso: Path, workspace: Path, context: dict | None = None) -> dict:
    context = context or source_context(iso, workspace)
    manifest_path = workspace / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    edited = []
    for region in manifest["regions"]:
        path = workspace / "edited_buttons" / region["file"]
        if path.exists():
            edited.append({"path": str(path.relative_to(workspace)).replace("\\", "/"),
                           "size": path.stat().st_size, "sha256": sha256_file(path)})
    if not edited: raise ValueError("option-menu edited image is empty")
    return {"source_iso_sha256": SOURCE_ISO_SHA256, "algorithm_version": ALGORITHM_VERSION,
            "original_container_sha256": sha256(context["standalone"]),
            "original_payload_sha256": sha256(context["payload"]),
            "manifest_sha256": sha256_file(manifest_path), "edited_files": edited,
            "allocation": context["allocation"], "standalone_allocation": context["standalone_allocation"],
            "embedded_allocation": context["embedded_allocation"]}


def cache_status(iso: Path, workspace: Path) -> dict:
    cache_dir = workspace / "precompiled"; manifest_path = cache_dir / "manifest.json"
    if not manifest_path.exists(): return {"status": "missing", "valid": False, "message": "옵션 메뉴 캐시 없음"}
    try:
        row = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        identity = cache_identity(iso, workspace)
        if row.get("schema_version") != CACHE_SCHEMA_VERSION: return {"status": "stale", "valid": False, "message": "옵션 메뉴 캐시 형식 변경"}
        if any(row.get(key) != value for key, value in identity.items()): return {"status": "stale", "valid": False, "message": "옵션 메뉴 이미지 변경"}
        cache_file = cache_dir / row["file"]
        if not cache_file.is_file() or sha256_file(cache_file) != row.get("output_container_sha256"):
            return {"status": "stale", "valid": False, "message": "옵션 메뉴 캐시 파일 불일치"}
        valid, payload, error = verify_container_bytes(cache_file.read_bytes())
        if not valid or payload is None or sha256(payload) != row.get("output_payload_sha256"):
            return {"status": "stale", "valid": False, "message": f"옵션 메뉴 캐시 payload 불일치: {error or ''}"}
        return {"status": "current", "valid": True, "message": "옵션 메뉴 최신", "changed": False}
    except Exception as exc:
        return {"status": "error", "valid": False, "message": f"옵션 메뉴 캐시 검사 오류: {exc}"}


def load_cached(iso: Path, workspace: Path) -> tuple[bytes, bytes, dict]:
    status = cache_status(iso, workspace)
    if not status["valid"]: raise ValueError(status["message"] + "; 이미지 캐시를 갱신하세요")
    row = json.loads((workspace / "precompiled" / "manifest.json").read_text(encoding="utf-8-sig"))
    container = (workspace / "precompiled" / row["file"]).read_bytes()
    valid, payload, error = verify_container_bytes(container)
    if not valid or payload is None: raise ValueError(f"option-menu cached container invalid: {error or ''}")
    return container, payload, dict(row["report"])


def precompile(iso: Path, workspace: Path) -> dict:
    started = time.perf_counter(); context = source_context(iso, workspace); identity = cache_identity(iso, workspace, context)
    current = cache_status(iso, workspace)
    if current["valid"]:
        row = json.loads((workspace / "precompiled" / "manifest.json").read_text(encoding="utf-8-sig"))
        return {**row, "changed": False, "reuse_count": 1, "rebuild_count": 0,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "cache_bytes": (workspace / "precompiled" / row["file"]).stat().st_size}
    target = (workspace / "precompiled").resolve(); temporary = (workspace / f"precompiled.tmp-{uuid.uuid4().hex}").resolve()
    backup = (workspace / f"precompiled.backup-{uuid.uuid4().hex}").resolve(); root = workspace.resolve()
    if target.parent != root or temporary.parent != root or backup.parent != root: raise ValueError("unsafe option-menu cache path")
    try:
        temporary.mkdir(parents=True); source_file = temporary / "source.dds"; source_file.write_bytes(context["payload"])
        payload_file = temporary / "static_tex.dds"; container_file = temporary / "static_tex.dds.z"
        report = compose(source_file, workspace, payload_file, container_file, context["allocation"])
        container = container_file.read_bytes(); valid, decoded, error = verify_container_bytes(container)
        if not valid or decoded != payload_file.read_bytes(): raise ValueError(f"option-menu cache verification failed: {error or ''}")
        source_file.unlink(); payload_file.unlink()
        row = {"schema_version": CACHE_SCHEMA_VERSION, **identity, "file": container_file.name,
               "output_container_sha256": sha256(container), "output_payload_sha256": sha256(decoded),
               "container_size": len(container), "report": report}
        (temporary / "manifest.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if target.exists(): target.rename(backup)
        temporary.rename(target)
        if backup.exists(): shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if temporary.exists(): shutil.rmtree(temporary)
        if backup.exists() and not target.exists(): backup.rename(target)
        raise
    return {**row, "changed": True, "reuse_count": 0, "rebuild_count": 1,
            "elapsed_seconds": round(time.perf_counter() - started, 3), "cache_bytes": len(container)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("tools/patchdata/ys6_option_menu"))
    parser.add_argument("--status", action="store_true"); args = parser.parse_args()
    result = cache_status(args.iso, args.workspace) if args.status else precompile(args.iso, args.workspace)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
