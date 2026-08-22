#!/usr/bin/env python3
"""Precompile verified Ys VI additional-image containers for fast GUI builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Callable

try:
    from tools.scripts.iso9660_info import SECTOR_SIZE, find_record
    from tools.scripts.ys6_additional_image_patch import (
        build_container, cache_identity, compose_collection_surface,
        compose_payload,
    )
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from iso9660_info import SECTOR_SIZE, find_record
    from ys6_additional_image_patch import (
        build_container, cache_identity, compose_collection_surface,
        compose_payload,
    )
    from ys6_z import verify_container_bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_iso_file(iso: Path, internal_path: str) -> tuple[bytes, object]:
    record = find_record(iso, internal_path)
    with iso.open("rb") as stream:
        stream.seek(record.extent_lba * SECTOR_SIZE)
        return stream.read(record.data_length), record


def cache_status(iso: Path, workspace: Path) -> dict:
    manifest_path = workspace / "manifest.json"
    cache_path = workspace / "precompiled" / "manifest.json"
    if not cache_path.exists():
        return {"status": "missing", "valid": False, "message": "캐시 없음"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
        cached = {row["resource_id"]: row for row in cache["resources"]}
        checked = 0
        for resource in manifest["resources"]:
            edit_dir = workspace / "edited_parts" / resource["id"]
            if not edit_dir.exists() or not any(edit_dir.glob("*.png")):
                continue
            row = cached.get(resource["id"])
            if row is None:
                return {"status": "stale", "valid": False, "message": f"캐시 누락: {resource['id']}"}
            original, _record = read_iso_file(iso, resource["iso_path"])
            identity = cache_identity(resource, workspace, original)
            for key, value in identity.items():
                if row.get(key) != value:
                    reason = "수정 이미지 변경" if key == "edited_files" else "매니페스트 변경" if key == "resource_definition_sha256" else "원본 이미지 불일치"
                    return {"status": "stale", "valid": False, "message": f"{reason}: {resource['id']}"}
            container_path = workspace / "precompiled" / row["file"]
            if not container_path.exists() or sha256(container_path.read_bytes()) != row["output_container_sha256"]:
                return {"status": "stale", "valid": False, "message": f"캐시 파일 불일치: {resource['id']}"}
            checked += 1
        return {"status": "current", "valid": True, "message": f"최신 캐시 ({checked}개)", "resource_count": checked}
    except Exception as exc:
        return {"status": "error", "valid": False, "message": f"캐시 검사 오류: {exc}"}


def _precompile_to(iso: Path, workspace: Path, target: Path,
                   progress: Callable[[str, int, int], None] | None = None) -> dict:
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8-sig"))
    actual_iso_sha256 = sha256_file(iso)
    if actual_iso_sha256 != manifest["source_iso_sha256"]:
        raise ValueError("지원하는 원본 ISO의 SHA-256이 아닙니다")
    target.mkdir(parents=True, exist_ok=True)
    selected = [resource for resource in manifest["resources"]
                if (workspace / "edited_parts" / resource["id"]).exists()
                and any((workspace / "edited_parts" / resource["id"]).glob("*.png"))]
    rows = []
    for position, resource in enumerate(selected, 1):
        if progress:
            progress(resource["id"], position, len(selected))
        original, record = read_iso_file(iso, resource["iso_path"])
        valid, payload, error = verify_container_bytes(original)
        if not valid or payload is None:
            raise ValueError(f"{resource['id']}: invalid original container: {error}")
        if resource.get("collection_pictures"):
            patched_payload, report = compose_collection_surface(payload, resource, workspace)
        else:
            patched_payload, report = compose_payload(payload, resource, workspace)
        allocation = ((record.data_length + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE
        container, container_report = build_container(patched_payload, allocation)
        valid, decoded, error = verify_container_bytes(container)
        if not valid or decoded != patched_payload:
            raise ValueError(f"{resource['id']}: precompiled verification failed: {error}")
        output = target / f"{resource['id']}.dds.z"
        output.write_bytes(container)
        identity = cache_identity(resource, workspace, original)
        rows.append({
            **identity,
            "iso_path": resource["iso_path"],
            "file": output.name,
            "output_container_sha256": sha256(container),
            "output_payload_sha256": sha256(patched_payload),
            "container_size": len(container),
            "allocation": allocation,
            "remaining_slack": allocation - len(container),
            "report": {**report, **container_report},
        })
        print(f"{resource['id']}: {len(container)}/{allocation}", flush=True)
    result = {
        "schema_version": 1,
        "source_iso_sha256": actual_iso_sha256,
        "resource_count": len(rows),
        "resources": rows,
    }
    (target / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def precompile(iso: Path, workspace: Path,
               progress: Callable[[str, int, int], None] | None = None) -> dict:
    """Atomically replace the cache only after every resource succeeds."""
    started = time.perf_counter()
    target = (workspace / "precompiled").resolve()
    temporary = (workspace / f"precompiled.tmp-{uuid.uuid4().hex}").resolve()
    backup = (workspace / f"precompiled.backup-{uuid.uuid4().hex}").resolve()
    root = workspace.resolve()
    if temporary.parent != root or backup.parent != root or target.parent != root:
        raise ValueError("unsafe precompiled cache path")
    try:
        result = _precompile_to(iso, workspace, temporary, progress)
        if target.exists():
            target.rename(backup)
        temporary.rename(target)
        if backup.exists():
            # The new cache is already installed. A cleanup failure must not
            # turn a successful atomic replacement into a reported failure.
            shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if backup.exists() and not target.exists():
            backup.rename(target)
        raise
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    result["cache_bytes"] = sum(path.stat().st_size for path in target.glob("*.dds.z"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("tools/patchdata/ys6_additional_images"))
    args = parser.parse_args()
    result = precompile(args.iso, args.workspace)
    print(json.dumps({"valid": True, "resource_count": result["resource_count"]}, indent=2))


if __name__ == "__main__":
    main()
