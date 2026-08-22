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


def _compile_resource(iso: Path, workspace: Path, target: Path, resource: dict,
                      original: bytes, record: object, identity: dict) -> dict:
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
    row = {
        **identity,
        "iso_path": resource["iso_path"],
        "file": output.name,
        "output_container_sha256": sha256(container),
        "output_payload_sha256": sha256(patched_payload),
        "container_size": len(container),
        "allocation": allocation,
        "remaining_slack": allocation - len(container),
        "report": {**report, **container_report},
    }
    print(f"{resource['id']}: {len(container)}/{allocation}", flush=True)
    return row


def _precompile_to(iso: Path, workspace: Path, target: Path, current_cache: Path,
                   progress: Callable[[str, int, int], None] | None = None,
                   planned: Callable[[dict], None] | None = None) -> dict:
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8-sig"))
    actual_iso_sha256 = sha256_file(iso)
    if actual_iso_sha256 != manifest["source_iso_sha256"]:
        raise ValueError("지원하는 원본 ISO의 SHA-256이 아닙니다")
    selected = [resource for resource in manifest["resources"]
                if (workspace / "edited_parts" / resource["id"]).exists()
                and any((workspace / "edited_parts" / resource["id"]).glob("*.png"))]
    old_manifest_path = current_cache / "manifest.json"
    old_manifest = None
    if old_manifest_path.exists():
        try:
            candidate = json.loads(old_manifest_path.read_text(encoding="utf-8-sig"))
            if candidate.get("source_iso_sha256") == actual_iso_sha256:
                old_manifest = candidate
        except (OSError, ValueError, KeyError, TypeError):
            old_manifest = None
    old_rows = {row["resource_id"]: row for row in old_manifest.get("resources", [])} if old_manifest else {}

    prepared = []
    reuse = []
    rebuild = []
    new = []
    selected_ids = {resource["id"] for resource in selected}
    removed = sorted(set(old_rows) - selected_ids)
    for resource in selected:
        original, record = read_iso_file(iso, resource["iso_path"])
        identity = cache_identity(resource, workspace, original)
        old_row = old_rows.get(resource["id"])
        item = (resource, original, record, identity, old_row)
        prepared.append(item)
        if old_row is None:
            new.append(item)
            continue
        cache_file = current_cache / old_row.get("file", "")
        identity_matches = all(old_row.get(key) == value for key, value in identity.items())
        file_matches = (cache_file.is_file()
                        and sha256_file(cache_file) == old_row.get("output_container_sha256"))
        if identity_matches and file_matches:
            reuse.append(item)
        else:
            rebuild.append(item)

    plan = {
        "reuse_count": len(reuse),
        "rebuild_count": len(rebuild),
        "new_count": len(new),
        "remove_count": len(removed),
        "rebuild_resources": [item[0]["id"] for item in rebuild],
        "new_resources": [item[0]["id"] for item in new],
        "removed_resources": removed,
    }
    if planned:
        planned(plan)
    work = rebuild + new
    if not work and not removed and len(reuse) == len(selected) and current_cache.is_dir():
        return {
            **old_manifest,
            **plan,
            "changed": False,
        }

    target.mkdir(parents=True, exist_ok=True)
    row_by_id = {}
    for resource, _original, _record, _identity, old_row in reuse:
        source = current_cache / old_row["file"]
        shutil.copy2(source, target / old_row["file"])
        row_by_id[resource["id"]] = old_row
    for position, (resource, original, record, identity, _old_row) in enumerate(work, 1):
        if progress:
            progress(resource["id"], position, len(work))
        row_by_id[resource["id"]] = _compile_resource(
            iso, workspace, target, resource, original, record, identity)
    rows = [row_by_id[resource["id"]] for resource in selected]
    result = {
        "schema_version": 1,
        "source_iso_sha256": actual_iso_sha256,
        "resource_count": len(rows),
        "resources": rows,
        **plan,
        "changed": True,
    }
    (target / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def precompile(iso: Path, workspace: Path,
               progress: Callable[[str, int, int], None] | None = None,
               planned: Callable[[dict], None] | None = None) -> dict:
    """Atomically replace the cache only after every resource succeeds."""
    started = time.perf_counter()
    target = (workspace / "precompiled").resolve()
    temporary = (workspace / f"precompiled.tmp-{uuid.uuid4().hex}").resolve()
    backup = (workspace / f"precompiled.backup-{uuid.uuid4().hex}").resolve()
    root = workspace.resolve()
    if temporary.parent != root or backup.parent != root or target.parent != root:
        raise ValueError("unsafe precompiled cache path")
    try:
        result = _precompile_to(iso, workspace, temporary, target, progress, planned)
        if result["changed"]:
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
    print(json.dumps({key: result[key] for key in (
        "resource_count", "reuse_count", "rebuild_count", "new_count",
        "remove_count", "changed", "elapsed_seconds", "cache_bytes"
    )}, indent=2))


if __name__ == "__main__":
    main()
