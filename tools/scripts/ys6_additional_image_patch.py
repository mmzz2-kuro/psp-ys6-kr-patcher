#!/usr/bin/env python3
"""Prepare and patch editable PNG regions in Ys VI PSP MIG textures."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image, ImageChops

try:
    from tools.scripts.ys6_mig_texture import inspect as inspect_mig
    from tools.scripts.ys6_mig_collection_extract import iter_pictures, render_picture
    from tools.scripts.ys6_option_menu_image import (
        build_optimized_container, encode_dxt1_block_high_quality,
        pc_dxt1_to_psp, psp_dxt1_to_pc, sha256,
    )
    from tools.scripts.ys6_z import verify_container_bytes
except ModuleNotFoundError:
    from ys6_mig_texture import inspect as inspect_mig
    from ys6_mig_collection_extract import iter_pictures, render_picture
    from ys6_option_menu_image import (
        build_optimized_container, encode_dxt1_block_high_quality,
        pc_dxt1_to_psp, psp_dxt1_to_pc, sha256,
    )
    from ys6_z import verify_container_bytes


def _image_section(payload: bytes) -> tuple[dict | None, dict]:
    _root, palette, image = inspect_mig(payload)
    return palette, image


def pc_dxt3_to_psp(blocks: bytes) -> bytes:
    if len(blocks) % 16:
        raise ValueError("DXT3 data is not block aligned")
    output = bytearray(len(blocks))
    for offset in range(0, len(blocks), 16):
        block = blocks[offset:offset + 16]
        output[offset:offset + 16] = block[12:16] + block[8:12] + block[0:8]
    return bytes(output)


def rotate_blocks(image: Image.Image, offset: int) -> Image.Image:
    """Rotate the row-major 4x4 block stream into logical display order."""
    if not offset:
        return image.copy()
    blocks = [image.crop((x, y, x + 4, y + 4))
              for y in range(0, image.height, 4) for x in range(0, image.width, 4)]
    offset %= len(blocks)
    blocks = blocks[offset:] + blocks[:offset]
    output = Image.new("RGBA", image.size)
    for index, block in enumerate(blocks):
        output.paste(block, ((index % (image.width // 4)) * 4,
                             (index // (image.width // 4)) * 4))
    return output


def render(payload: bytes, block_offset: int = 0) -> Image.Image:
    palette, image = _image_section(payload)
    return rotate_blocks(render_picture(payload, palette, image), block_offset)


def _pillow_blocks(image: Image.Image, fmt: str) -> bytes:
    output = io.BytesIO()
    image.convert("RGBA").save(output, format="DDS", pixel_format=fmt)
    return output.getvalue()[128:]


def _regions(resource: dict) -> list[dict]:
    if resource["id"].startswith("place_names_"):
        return [{"id": f"line_{index + 1:02d}", "source_text": text,
                 "file": f"line_{index + 1:02d}.png",
                 "box": [0, index * 32, resource["size"][0], index * 32 + 32]}
                for index, text in enumerate(resource["texts"])]
    if resource.get("regions"):
        return resource["regions"]
    width, height = resource["size"]
    texts = resource.get("texts") or [resource.get("note", resource["id"])]
    # Texture rows are aligned to four pixels. Equal horizontal bands are a
    # conservative editable unit and retain all background pixels around text.
    step = max(4, (height // len(texts)) // 4 * 4)
    result = []
    for index, text in enumerate(texts):
        top = min(height, index * step)
        bottom = height if index == len(texts) - 1 else min(height, top + step)
        result.append({"id": f"line_{index + 1:02d}", "source_text": text,
                       "file": f"line_{index + 1:02d}.png",
                       "box": [0, top, width, bottom]})
    return result


def prepare(workspace: Path) -> dict:
    manifest_path = workspace / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    source_parts = workspace / "source_parts"
    edited_parts = workspace / "edited_parts"
    source_parts.mkdir(parents=True, exist_ok=True)
    edited_parts.mkdir(parents=True, exist_ok=True)
    count = 0
    for resource in manifest["resources"]:
        source = workspace / resource["source_png"]
        with Image.open(source) as opened:
            image = opened.convert("RGBA")
        target = source_parts / resource["id"]
        target.mkdir(parents=True, exist_ok=True)
        (edited_parts / resource["id"]).mkdir(parents=True, exist_ok=True)
        regions = _regions(resource)
        for region in regions:
            box = tuple(region["box"])
            image.crop(box).save(target / region["file"])
            region["width"], region["height"] = box[2] - box[0], box[3] - box[1]
            count += 1
        resource["regions"] = regions
    manifest["schema_version"] = 2
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"valid": True, "resource_count": len(manifest["resources"]), "part_count": count}
    (workspace / "prepare-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def normalize_sources(workspace: Path) -> dict:
    manifest_path = workspace / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    changed = []
    for resource in manifest["resources"]:
        # The extracted PSP block stream starts one 4x4 block before the
        # logical top-left used by the game renderer.
        resource.setdefault("block_offset", 1)
        offset = int(resource["block_offset"])
        if not offset or resource.get("source_block_offset_applied"):
            continue
        path = workspace / resource["source_png"]
        with Image.open(path) as opened:
            normalized = rotate_blocks(opened.convert("RGBA"), offset)
        normalized.save(path)
        resource["source_block_offset_applied"] = True
        changed.append(resource["id"])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"valid": True, "normalized_resources": changed, "count": len(changed)}


def edited_count(workspace: Path) -> tuple[int, list[str]]:
    root = workspace / "edited_parts"
    files = sorted(root.rglob("*.png")) if root.exists() else []
    return len(files), [str(path.relative_to(root)).replace("\\", "/") for path in files]


def compose_payload(source_payload: bytes, resource: dict, workspace: Path) -> tuple[bytes, dict]:
    block_offset = int(resource.get("block_offset", 0))
    original = render(source_payload, block_offset).convert("RGBA")
    if original.size != tuple(resource["size"]):
        raise ValueError(f"{resource['id']}: texture size mismatch")
    composed = original.copy()
    applied = []
    for region in resource["regions"]:
        path = workspace / "edited_parts" / resource["id"] / region["file"]
        if not path.exists():
            continue
        with Image.open(path) as opened:
            opened.load()
            expected = (region["width"], region["height"])
            if opened.size != expected or opened.mode not in {"RGB", "RGBA"}:
                raise ValueError(f"{path}: expected RGB/RGBA {expected[0]}x{expected[1]}")
            patch = opened.convert("RGBA")
        box = tuple(region["box"])
        composed.paste(patch, (box[0], box[1]))
        applied.append(region["id"])
    if not applied:
        return source_payload, {"id": resource["id"], "applied_regions": [], "changed_block_count": 0}
    difference = ImageChops.difference(original, composed)
    rgba_changed = difference.getbbox()
    if rgba_changed is None:
        return source_payload, {"id": resource["id"], "applied_regions": applied, "changed_block_count": 0}

    palette, image_section = _image_section(source_payload)
    if palette is not None:
        raise ValueError(f"{resource['id']}: indexed texture editing is not supported")
    info = image_section["payload"]
    fmt = info["pixel_format"]
    width, height = original.size
    start = image_section["offset"] + 16 + info["data_offset"]
    block_size = 8 if fmt == 8 else 16 if fmt == 9 else 0
    if not block_size:
        raise ValueError(f"{resource['id']}: unsupported pixel format {fmt}")
    encoded_pc = _pillow_blocks(composed, "DXT1" if fmt == 8 else "DXT3")
    encoded = pc_dxt1_to_psp(encoded_pc) if fmt == 8 else pc_dxt3_to_psp(encoded_pc)
    patched = bytearray(source_payload)
    changed_blocks = []
    blocks_per_row = width // 4
    for by in range(height // 4):
        for bx in range(width // 4):
            pixel_box = (bx * 4, by * 4, bx * 4 + 4, by * 4 + 4)
            if difference.crop(pixel_box).getbbox() is None:
                continue
            index = by * blocks_per_row + bx
            offset = index * block_size
            replacement = encoded[offset:offset + block_size]
            if fmt == 8:
                replacement = encode_dxt1_block_high_quality(
                    list(composed.crop(pixel_box).getdata()), replacement)
            else:
                # DXT3 alpha is explicit. Quantize directly from the edited PNG
                # so Pillow's RGB encoder cannot alter transparency.
                alpha = 0
                for i, pixel in enumerate(composed.crop(pixel_box).getdata()):
                    alpha |= ((pixel[3] * 15 + 127) // 255) << (i * 4)
                replacement = replacement[:8] + struct.pack("<Q", alpha)
            physical_index = (index + block_offset) % ((width // 4) * (height // 4))
            target = start + physical_index * block_size
            if patched[target:target + block_size] != replacement:
                patched[target:target + block_size] = replacement
                changed_blocks.append(index)
    return bytes(patched), {"id": resource["id"], "applied_regions": applied,
                            "changed_block_count": len(changed_blocks),
                            "changed_blocks": changed_blocks,
                            "source_sha256": sha256(source_payload),
                            "output_sha256": sha256(bytes(patched))}


def compose_collection_picture(collection: bytes, picture_index: int, resource: dict,
                               workspace: Path) -> tuple[bytes, dict]:
    match = next((row for row in iter_pictures(collection) if row[0] == picture_index), None)
    if match is None:
        raise ValueError(f"{resource['id']}: collection picture {picture_index} not found")
    _index, offset, picture, _palette, _image = match
    picture_payload = collection[offset:offset + picture["size"]]
    # A collection picture is a normal MIG picture section without the 16-byte
    # file signature. Prefixing the signature lets the single-texture parser
    # operate on it while keeping every internal relative offset unchanged.
    root_header = struct.pack("<HHIII", 2, 0, 16 + len(picture_payload), len(picture_payload), 16)
    wrapped = b"MIG.00.1PSP\0" + b"\0" * 4 + root_header + picture_payload
    patched_wrapped, report = compose_payload(wrapped, resource, workspace)
    patched_picture = patched_wrapped[32:]
    if len(patched_picture) != len(picture_payload):
        raise ValueError("collection picture size changed")
    patched = bytearray(collection)
    patched[offset:offset + len(patched_picture)] = patched_picture
    report["picture_index"] = picture_index
    return bytes(patched), report


def build_container(payload: bytes, allocation: int | None = None) -> tuple[bytes, dict]:
    container, memory_level = build_optimized_container(payload)
    valid, decoded, error = verify_container_bytes(container)
    if not valid or decoded != payload:
        raise ValueError(f"container verification failed: {error}")
    if allocation is not None and len(container) > allocation:
        raise ValueError(f"container exceeds allocation: {len(container)} > {allocation}")
    return container, {"container_size": len(container), "allocation": allocation,
                       "remaining_slack": allocation - len(container) if allocation else None,
                       "compression_memory_level": memory_level}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "normalize-sources", "inspect"))
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.workspace)
    elif args.command == "normalize-sources":
        result = normalize_sources(args.workspace)
    else:
        result = dict(zip(("count", "files"), edited_count(args.workspace)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
