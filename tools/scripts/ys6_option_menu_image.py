#!/usr/bin/env python3
"""Extract and recompose editable Ys VI PSP option-menu button PNG files."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

try:
    from tools.scripts.ys6_z import build_container, verify_container_bytes
except ModuleNotFoundError:
    from ys6_z import build_container, verify_container_bytes


ATLAS_OFFSET = 0x106130
ATLAS_WIDTH = 256
ATLAS_HEIGHT = 256
ATLAS_SIZE = ATLAS_WIDTH * ATLAS_HEIGHT // 2
DXT1_BLOCK_SIZE = 8
BLOCKS_PER_ROW = ATLAS_WIDTH // 4

# Coordinates are half-open boxes in the verified logical 256x256 atlas.
# Each text button occupies one 202x24 cell in the source atlas.
DEFAULT_REGIONS = (
    ("bgm_volume", "BGMのボリューム", (0, 0, 202, 24)),
    ("se_volume", "効果音のボリューム", (0, 24, 202, 48)),
    ("voice_volume", "音声のボリューム", (0, 48, 202, 72)),
    ("reset_default", "標準に戻す", (0, 72, 202, 96)),
    ("key_config", "キーコンフィグ", (0, 96, 202, 120)),
    ("controls", "操作説明", (0, 120, 202, 144)),
    ("save", "セーブ", (0, 144, 202, 168)),
    ("return_title", "タイトル画面に戻る", (0, 168, 202, 192)),
)

# Four 54x62 pieces stored vertically at the right edge form one logical
# 216x62 unselected dialogue/message-window image.
DIALOGUE_PIECES = (
    (202, 0, 256, 62),
    (202, 62, 256, 124),
    (202, 124, 256, 186),
    (202, 186, 256, 248),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def build_optimized_container(payload: bytes) -> tuple[bytes, int]:
    """Choose the smallest valid level-9 zlib stream across memory levels."""
    candidates: list[tuple[int, bytes]] = []
    for memory_level in range(5, 10):
        encoder = zlib.compressobj(
            level=9, method=zlib.DEFLATED, wbits=15,
            memLevel=memory_level, strategy=zlib.Z_DEFAULT_STRATEGY,
        )
        stream = encoder.compress(payload) + encoder.flush()
        candidates.append((memory_level, stream))
    memory_level, stream = min(candidates, key=lambda item: len(item[1]))
    header = struct.pack("<II", zlib.crc32(payload) & 0xFFFFFFFF, len(payload))
    return header + stream, memory_level


def psp_dxt1_to_pc(stored: bytes) -> bytes:
    if len(stored) % DXT1_BLOCK_SIZE:
        raise ValueError("PSP DXT1 data is not block aligned")
    output = bytearray()
    for offset in range(0, len(stored), DXT1_BLOCK_SIZE):
        block = stored[offset:offset + DXT1_BLOCK_SIZE]
        output.extend(block[4:8] + block[0:4])
    return bytes(output)


def pc_dxt1_to_psp(stored: bytes) -> bytes:
    if len(stored) % DXT1_BLOCK_SIZE:
        raise ValueError("PC DXT1 data is not block aligned")
    output = bytearray()
    for offset in range(0, len(stored), DXT1_BLOCK_SIZE):
        block = stored[offset:offset + DXT1_BLOCK_SIZE]
        output.extend(block[4:8] + block[0:4])
    return bytes(output)


def decode_atlas(payload: bytes) -> Image.Image:
    if len(payload) < ATLAS_OFFSET + ATLAS_SIZE:
        raise ValueError("static_tex payload is too short for the option atlas")
    blocks = payload[ATLAS_OFFSET:ATLAS_OFFSET + ATLAS_SIZE]
    return Image.frombytes(
        "RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), psp_dxt1_to_pc(blocks), "bcn", (1,)
    )


def encode_atlas(image: Image.Image) -> bytes:
    if image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
        raise ValueError(f"atlas must be {ATLAS_WIDTH}x{ATLAS_HEIGHT}")
    buffer = io.BytesIO()
    image.convert("RGBA").save(buffer, format="DDS", pixel_format="DXT1")
    dds = buffer.getvalue()
    blocks = dds[128:]
    if len(blocks) != ATLAS_SIZE:
        raise ValueError(f"unexpected encoded DXT1 size: {len(blocks)}")
    return pc_dxt1_to_psp(blocks)


def default_manifest(source_sha256: str) -> dict:
    return {
        "schema_version": 1,
        "atlas": {
            "payload_offset": ATLAS_OFFSET,
            "width": ATLAS_WIDTH,
            "height": ATLAS_HEIGHT,
            "format": "PSP_DXT1",
            "source_payload_sha256": source_sha256,
        },
        "notes": [
            "source_buttons 파일은 원본이므로 수정하지 않습니다.",
            "수정 파일은 edited_buttons에 같은 파일명과 크기로 저장합니다.",
            "선택 상태는 문구별 복제 이미지가 아니라 selection_highlight 공통 레이어입니다.",
        ],
        "regions": [
            {
                "id": name,
                "source_text": text,
                "file": f"{name}.png",
                "box": list(box),
                "width": box[2] - box[0],
                "height": box[3] - box[1],
            }
            for name, text, box in DEFAULT_REGIONS
        ] + [{
            "id": "dialogue_unselected",
            "source_text": "비선택 다이얼로그/메시지 창",
            "file": "dialogue_unselected.png",
            "pieces": [list(box) for box in DIALOGUE_PIECES],
            "piece_width": 54,
            "piece_height": 62,
            "width": 216,
            "height": 62,
        }],
    }


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema_version") != 1 or not isinstance(data.get("regions"), list):
        raise ValueError("unsupported or invalid manifest")
    return data


def extract(source_payload: Path, output: Path) -> dict:
    payload = source_payload.read_bytes()
    atlas = decode_atlas(payload)
    source_dir = output / "source_buttons"
    edited_dir = output / "edited_buttons"
    source_dir.mkdir(parents=True, exist_ok=True)
    edited_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(output / "original-atlas.png")
    manifest = default_manifest(sha256(payload))
    diagnostic = atlas.copy()
    draw = ImageDraw.Draw(diagnostic)
    for index, region in enumerate(manifest["regions"]):
        if "pieces" in region:
            crop = Image.new("RGBA", (region["width"], region["height"]))
            for piece_index, raw_box in enumerate(region["pieces"]):
                box = tuple(raw_box)
                crop.paste(atlas.crop(box), (piece_index * region["piece_width"], 0))
                draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), outline=(0, 255, 255, 255))
                draw.text((box[0] + 2, box[1] + 2), f"D{piece_index + 1}", fill=(255, 255, 0, 255))
        else:
            box = tuple(region["box"])
            crop = atlas.crop(box)
            draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), outline=(255, 0, 255, 255))
            draw.text((box[0] + 2, box[1] + 2), str(index + 1), fill=(0, 255, 0, 255))
        crop.save(source_dir / region["file"])
    diagnostic.save(output / "button-regions.png")
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "valid": True,
        "source_payload": str(source_payload),
        "output": str(output),
        "original_atlas": str(output / "original-atlas.png"),
        "diagnostic": str(output / "button-regions.png"),
        "manifest": str(manifest_path),
        "region_count": len(manifest["regions"]),
        "source_payload_sha256": sha256(payload),
    }
    (output / "extract-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def compose(source_payload: Path, workspace: Path, output_payload: Path,
            output_container: Path | None, allocation: int | None) -> dict:
    payload = source_payload.read_bytes()
    manifest = load_manifest(workspace / "manifest.json")
    expected_hash = manifest["atlas"].get("source_payload_sha256")
    if expected_hash and sha256(payload) != expected_hash:
        raise ValueError("source payload does not match the payload used for extraction")
    original = decode_atlas(payload)
    composed = original.copy()
    edited_dir = workspace / "edited_buttons"
    applied = []
    for region in manifest["regions"]:
        edited = edited_dir / region["file"]
        if not edited.exists():
            continue
        with Image.open(edited) as opened:
            opened.load()
            if opened.size != (region["width"], region["height"]):
                raise ValueError(
                    f"{edited.name}: expected {region['width']}x{region['height']}, got {opened.width}x{opened.height}"
                )
            if opened.mode not in {"RGB", "RGBA"}:
                raise ValueError(f"{edited.name}: RGB or RGBA PNG required, got {opened.mode}")
            patch = opened.convert("RGBA")
        if "pieces" in region:
            for piece_index, raw_box in enumerate(region["pieces"]):
                box = tuple(raw_box)
                left = piece_index * region["piece_width"]
                piece = patch.crop((left, 0, left + region["piece_width"], region["piece_height"]))
                composed.paste(piece, (box[0], box[1]), piece)
        else:
            box = tuple(region["box"])
            composed.paste(patch, (box[0], box[1]), patch)
        applied.append(region["id"])
    if not applied:
        raise ValueError("edited_buttons contains no applicable PNG files")

    difference = ImageChops.difference(original, composed)
    # RGBA difference images commonly have an all-zero alpha difference even
    # when RGB pixels changed.  Use RGB for geometry/change detection.
    rgb_difference = difference.convert("RGB")
    changed_box = rgb_difference.getbbox()
    if changed_box is None:
        raise ValueError("edited PNG files do not change any pixels")
    encoded = encode_atlas(composed)
    patched = bytearray(payload)
    changed_blocks = []
    min_x, min_y, max_x, max_y = changed_box
    for block_y in range(min_y // 4, (max_y - 1) // 4 + 1):
        for block_x in range(min_x // 4, (max_x - 1) // 4 + 1):
            pixel_box = (block_x * 4, block_y * 4, block_x * 4 + 4, block_y * 4 + 4)
            if rgb_difference.crop(pixel_box).getbbox() is None:
                continue
            index = block_y * BLOCKS_PER_ROW + block_x
            start = index * DXT1_BLOCK_SIZE
            replacement = encoded[start:start + DXT1_BLOCK_SIZE]
            target = ATLAS_OFFSET + start
            before = bytes(patched[target:target + DXT1_BLOCK_SIZE])
            if replacement != before:
                patched[target:target + DXT1_BLOCK_SIZE] = replacement
                changed_blocks.append(index)

    output_payload.parent.mkdir(parents=True, exist_ok=True)
    output_payload.write_bytes(patched)
    preview_dir = output_payload.parent
    composed.save(preview_dir / "composed-atlas.png")
    difference.save(preview_dir / "difference.png")
    decoded = decode_atlas(bytes(patched))
    decoded.save(preview_dir / "roundtrip-decoded.png")
    container_size = None
    if output_container is not None:
        container, compression_memory_level = build_optimized_container(bytes(patched))
        valid, verified, error = verify_container_bytes(container)
        if not valid or verified != bytes(patched):
            raise ValueError(f"container verification failed: {error}")
        if allocation is not None and len(container) > allocation:
            raise ValueError(f"container exceeds allocation: {len(container)} > {allocation}")
        output_container.parent.mkdir(parents=True, exist_ok=True)
        output_container.write_bytes(container)
        container_size = len(container)
    else:
        compression_memory_level = None
    report = {
        "valid": True,
        "source_payload": str(source_payload),
        "output_payload": str(output_payload),
        "output_container": str(output_container) if output_container else None,
        "applied_regions": applied,
        "changed_pixel_box": list(changed_box),
        "changed_dxt1_block_count": len(changed_blocks),
        "changed_dxt1_blocks": changed_blocks,
        "container_size": container_size,
        "compression_memory_level": compression_memory_level,
        "allocation": allocation,
        "source_payload_sha256": sha256(payload),
        "output_payload_sha256": sha256(bytes(patched)),
    }
    (preview_dir / "compose-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extract_parser = commands.add_parser("extract")
    extract_parser.add_argument("source_payload", type=Path)
    extract_parser.add_argument("output", type=Path)
    compose_parser = commands.add_parser("compose")
    compose_parser.add_argument("source_payload", type=Path)
    compose_parser.add_argument("workspace", type=Path)
    compose_parser.add_argument("output_payload", type=Path)
    compose_parser.add_argument("--output-container", type=Path)
    compose_parser.add_argument("--allocation", type=lambda value: int(value, 0))
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            result = extract(args.source_payload, args.output)
        else:
            result = compose(
                args.source_payload, args.workspace, args.output_payload,
                args.output_container, args.allocation,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"옵션 메뉴 이미지 처리 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
