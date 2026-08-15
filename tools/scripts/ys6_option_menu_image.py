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


def rgb565_to_rgb(value: int) -> tuple[int, int, int]:
    r5 = (value >> 11) & 0x1F
    g6 = (value >> 5) & 0x3F
    b5 = value & 0x1F
    return (
        (r5 << 3) | (r5 >> 2),
        (g6 << 2) | (g6 >> 4),
        (b5 << 3) | (b5 >> 2),
    )


def rgb_to_565(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return (
        ((r * 31 + 127) // 255) << 11
        | ((g * 63 + 127) // 255) << 5
        | ((b * 31 + 127) // 255)
    )


def dxt1_palette(color0: int, color1: int) -> tuple[tuple[int, int, int, int], ...]:
    first = rgb565_to_rgb(color0)
    second = rgb565_to_rgb(color1)
    if color0 > color1:
        third = tuple((2 * first[i] + second[i]) // 3 for i in range(3))
        fourth = tuple((first[i] + 2 * second[i]) // 3 for i in range(3))
        return (
            (*first, 255), (*second, 255), (*third, 255), (*fourth, 255),
        )
    third = tuple((first[i] + second[i]) // 2 for i in range(3))
    return ((*first, 255), (*second, 255), (*third, 255), (0, 0, 0, 0))


def fit_dxt1_block(pixels: list[tuple[int, int, int, int]], color0: int,
                   color1: int) -> tuple[int, bytes]:
    transparent = any(pixel[3] < 128 for pixel in pixels)
    if transparent:
        if color0 > color1:
            color0, color1 = color1, color0
        choices = 3
    else:
        if color0 <= color1:
            color0, color1 = color1, color0
        if color0 == color1:
            color0 = min(0xFFFF, color0 + 1)
            if color0 <= color1:
                color1 = max(0, color1 - 1)
        choices = 4
    palette = dxt1_palette(color0, color1)
    indices = 0
    error = 0
    for pixel_index, pixel in enumerate(pixels):
        if pixel[3] < 128:
            choice = 3
        else:
            choice = min(
                range(choices),
                key=lambda candidate: sum(
                    (pixel[channel] - palette[candidate][channel]) ** 2
                    for channel in range(3)
                ),
            )
            error += sum(
                (pixel[channel] - palette[choice][channel]) ** 2
                for channel in range(3)
            )
        indices |= choice << (pixel_index * 2)
    # PSP stores the four index bytes before the two little-endian RGB565 endpoints.
    return error, struct.pack("<IHH", indices, color0, color1)


def decode_psp_dxt1_block(block: bytes) -> list[tuple[int, int, int, int]]:
    indices, color0, color1 = struct.unpack("<IHH", block)
    palette = dxt1_palette(color0, color1)
    return [palette[(indices >> (pixel_index * 2)) & 3] for pixel_index in range(16)]


def block_rgb_error(pixels: list[tuple[int, int, int, int]], block: bytes) -> int:
    decoded = decode_psp_dxt1_block(block)
    error = 0
    for source, restored in zip(pixels, decoded):
        if (source[3] < 128) != (restored[3] < 128):
            error += 255 * 255 * 4
        elif source[3] >= 128:
            error += sum((source[channel] - restored[channel]) ** 2 for channel in range(3))
    return error


def adjacent_565(value: int) -> set[int]:
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    candidates = {value}
    for channel, limit in ((0, 31), (1, 63), (2, 31)):
        for delta in (-1, 1):
            values = [r, g, b]
            values[channel] = max(0, min(limit, values[channel] + delta))
            candidates.add((values[0] << 11) | (values[1] << 5) | values[2])
    return candidates


def encode_dxt1_block_high_quality(
    pixels: list[tuple[int, int, int, int]], baseline: bytes,
) -> bytes:
    opaque = [pixel[:3] for pixel in pixels if pixel[3] >= 128]
    if not opaque:
        return struct.pack("<IHH", 0xFFFFFFFF, 0, 0)

    # Start from the existing encoder plus several image-derived endpoint pairs.
    _, base0, base1 = struct.unpack("<IHH", baseline)
    by_luma = sorted(opaque, key=lambda rgb: 299 * rgb[0] + 587 * rgb[1] + 114 * rgb[2])
    seeds = [
        (base0, base1),
        (rgb_to_565(by_luma[-1]), rgb_to_565(by_luma[0])),
    ]
    best_block = baseline
    best_error = block_rgb_error(pixels, baseline)
    for seed0, seed1 in seeds:
        _, current = fit_dxt1_block(pixels, seed0, seed1)
        current_error = block_rgb_error(pixels, current)
        # Coordinate descent in RGB565 endpoint space. Each accepted move strictly
        # lowers decoded RGB error, and the Pillow block remains the fallback.
        for _ in range(8):
            improved = False
            _, current0, current1 = struct.unpack("<IHH", current)
            for candidate0 in adjacent_565(current0):
                if candidate0 == current0:
                    continue
                _, candidate = fit_dxt1_block(pixels, candidate0, current1)
                candidate_error = block_rgb_error(pixels, candidate)
                if candidate_error < current_error:
                    current, current_error = candidate, candidate_error
                    improved = True
            _, current0, current1 = struct.unpack("<IHH", current)
            for candidate1 in adjacent_565(current1):
                if candidate1 == current1:
                    continue
                _, candidate = fit_dxt1_block(pixels, current0, candidate1)
                candidate_error = block_rgb_error(pixels, candidate)
                if candidate_error < current_error:
                    current, current_error = candidate, candidate_error
                    improved = True
            if not improved:
                break
        if current_error < best_error:
            best_block, best_error = current, current_error
    return best_block


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
                # Copy the edited RGBA pixels verbatim.  Supplying the image
                # again as a mask would alpha-blend it with the original atlas
                # and alter the pixels around antialiased text.
                composed.paste(piece, (box[0], box[1]))
        else:
            box = tuple(region["box"])
            composed.paste(patch, (box[0], box[1]))
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
            baseline = encoded[start:start + DXT1_BLOCK_SIZE]
            pixels = list(composed.crop(pixel_box).getdata())
            replacement = encode_dxt1_block_high_quality(pixels, baseline)
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
