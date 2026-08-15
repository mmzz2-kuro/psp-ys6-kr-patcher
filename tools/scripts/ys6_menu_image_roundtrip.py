#!/usr/bin/env python3
"""Extract and round-trip Ys VI PSP menu DDS.Z resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import io
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from tools.scripts.ys6_iso_z_search import iter_files
    from tools.scripts.ys6_z import build_container, verify_container_bytes
    from tools.scripts.ys6_mig_texture import MAGIC as MIG_MAGIC, inspect as inspect_mig, render as render_mig, unswizzle_8bpp
except ModuleNotFoundError:
    from iso9660_info import PVD_SECTOR, SECTOR_SIZE, parse_record
    from ys6_iso_z_search import iter_files
    from ys6_z import build_container, verify_container_bytes
    from ys6_mig_texture import MAGIC as MIG_MAGIC, inspect as inspect_mig, render as render_mig, unswizzle_8bpp

TARGET_NAMES = frozenset((
    "optionbg00.dds.z", "optionbg01.dds.z", "optionbg02.dds.z", "optionselect.dds.z",
))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def dds_metadata(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a supported DDS header")
    header_size, flags, height, width, pitch, depth, mipmaps = struct.unpack_from("<7I", data, 4)
    if header_size != 124:
        raise ValueError(f"unexpected DDS header size: {header_size}")
    pf_size, pf_flags, fourcc, bitcount = struct.unpack_from("<4I", data, 76)
    fourcc_text = fourcc.to_bytes(4, "little").rstrip(b"\0").decode("ascii", "replace")
    return {
        "width": width, "height": height, "pitch_or_linear_size": pitch,
        "depth": depth, "mipmap_count": mipmaps or 1, "pixel_format_size": pf_size,
        "pixel_format_flags_hex": f"0x{pf_flags:08X}", "fourcc": fourcc_text,
        "bitcount": bitcount, "header_flags_hex": f"0x{flags:08X}",
    }


def mig_metadata(data: bytes) -> dict:
    root, palette, image = inspect_mig(data)
    info = image["payload"]
    return {
        "format": "MIG.00.1PSP", "width": info["width"], "height": info["height"],
        "pixel_format": info["pixel_format"], "pixel_order": info["pixel_order"],
        "bits_per_pixel": info["bits_per_pixel"],
        "palette_format": palette["payload"]["pixel_format"] if palette else None,
        "palette_width": palette["payload"]["width"] if palette else None,
        "palette_height": palette["payload"]["height"] if palette else None,
        "root_size": root["size"], "image_section_offset": image["offset"],
    }


def swizzle_8bpp(source: bytes, width: int, height: int) -> bytes:
    if width % 16 or height % 8:
        raise ValueError("8-bit PSP swizzle requires width/height multiples of 16/8")
    output = bytearray(width * height); cursor = 0
    for block_y in range(0, height, 8):
        for block_x in range(0, width, 16):
            for row in range(8):
                start = (block_y + row) * width + block_x
                output[cursor:cursor + 16] = source[start:start + 16]; cursor += 16
    return bytes(output)


def clut_index(raw_index: int) -> int:
    return ((raw_index & 0xE7) | ((raw_index & 0x08) << 1) | ((raw_index & 0x10) >> 1))


def psp_dxt3_to_pc(blocks: bytes) -> bytes:
    """Convert PSP DXT3 blocks to the byte order used by DDS/BC2."""
    if len(blocks) % 16:
        raise ValueError("DXT3 payload is not aligned to 16-byte blocks")
    converted = bytearray(len(blocks))
    for offset in range(0, len(blocks), 16):
        block = blocks[offset:offset + 16]
        # PSP: color indices, RGB565 endpoints, alpha rows.
        # PC:  alpha rows, RGB565 endpoints, color indices.
        converted[offset:offset + 16] = block[8:16] + block[4:8] + block[0:4]
    return bytes(converted)


def pc_dxt3_to_psp(blocks: bytes) -> bytes:
    """Convert DDS/BC2 DXT3 blocks back to the PSP byte order."""
    if len(blocks) % 16:
        raise ValueError("DXT3 payload is not aligned to 16-byte blocks")
    converted = bytearray(len(blocks))
    for offset in range(0, len(blocks), 16):
        block = blocks[offset:offset + 16]
        converted[offset:offset + 16] = block[12:16] + block[8:12] + block[0:8]
    return bytes(converted)


def render_any_mig(data: bytes, block_offset: int = 0) -> Image.Image:
    _root, palette, image = inspect_mig(data); info = image["payload"]
    if info["pixel_format"] == 5:
        rendered, _ = render_mig(data); return rendered
    if info["pixel_format"] == 9 and palette is None:
        start = image["offset"] + 16 + info["data_offset"]
        byte_count = info["width"] * info["height"]
        blocks = data[start:start + byte_count]
        if len(blocks) != byte_count: raise ValueError("truncated MIG DXT3 data")
        if block_offset:
            shift = (block_offset * 16) % len(blocks)
            blocks = blocks[shift:] + blocks[:shift]
        pc_blocks = psp_dxt3_to_pc(blocks)
        return Image.frombytes("RGBA", (info["width"], info["height"]), pc_blocks, "bcn", (2,))
    raise ValueError(f"unsupported MIG pixel format: {info['pixel_format']}")


def render_mig_dxt3_layout(data: bytes, width: int, height: int) -> Image.Image:
    """Render a PSP DXT3 MIG using an explicit storage layout for diagnostics."""
    _root, palette, image = inspect_mig(data); info = image["payload"]
    if info["pixel_format"] != 9 or palette is not None:
        raise ValueError("explicit layout rendering requires an unpaletted DXT3 MIG")
    byte_count = info["width"] * info["height"]
    if width * height != byte_count:
        raise ValueError("explicit layout dimensions do not match the DXT3 payload size")
    start = image["offset"] + 16 + info["data_offset"]
    blocks = data[start:start + byte_count]
    return Image.frombytes("RGBA", (width, height), psp_dxt3_to_pc(blocks), "bcn", (2,))


def render_mig_dxt3_block_offset(data: bytes, block_offset: int) -> Image.Image:
    """Render after cyclically shifting the compressed 4x4 block stream."""
    _root, palette, image = inspect_mig(data); info = image["payload"]
    if info["pixel_format"] != 9 or palette is not None:
        raise ValueError("block-offset rendering requires an unpaletted DXT3 MIG")
    byte_count = info["width"] * info["height"]
    start = image["offset"] + 16 + info["data_offset"]
    blocks = data[start:start + byte_count]
    shift = (block_offset * 16) % len(blocks)
    shifted = blocks[shift:] + blocks[:shift]
    return Image.frombytes("RGBA", (info["width"], info["height"]), psp_dxt3_to_pc(shifted), "bcn", (2,))


def read_targets(iso: Path, name_contains: str | None = None) -> list[tuple[str, object, bytes]]:
    result = []
    with iso.open("rb") as handle:
        handle.seek(PVD_SECTOR * SECTOR_SIZE)
        pvd = handle.read(SECTOR_SIZE)
        root = parse_record(pvd, 156, PVD_SECTOR * SECTOR_SIZE)
        for raw_path, record in iter_files(handle, root):
            path = raw_path.split(";", 1)[0]
            filename = Path(path).name.lower()
            if name_contains is not None:
                if name_contains.casefold() not in filename.casefold() or not filename.endswith(".dds.z"):
                    continue
            elif filename not in TARGET_NAMES:
                continue
            handle.seek(record.extent_lba * SECTOR_SIZE)
            result.append((path, record, handle.read(record.data_length)))
    return sorted(result, key=lambda item: item[0])


def extract(iso: Path, output: Path, name_contains: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    previews = []
    for path, record, container in read_targets(iso, name_contains):
        valid, payload, error = verify_container_bytes(container)
        if not valid or payload is None:
            raise ValueError(f"invalid Z container {path}: {error}")
        if payload.startswith(MIG_MAGIC):
            meta = mig_metadata(payload); image = render_any_mig(payload); mode = image.mode
        else:
            meta = {"format": "DDS", **dds_metadata(payload)}
            dds_path_probe = output / (Path(path).name.removesuffix(".z") + ".probe")
            dds_path_probe.write_bytes(payload)
            with Image.open(dds_path_probe) as opened: opened.load(); image = opened.convert("RGBA"); mode = opened.mode
            dds_path_probe.unlink()
        stem = Path(path).name.removesuffix(".z")
        dds_path, png_path = output / stem, output / (stem + ".png")
        dds_path.write_bytes(payload)
        rgba = image.convert("RGBA"); rgba.save(png_path)
        dark = Image.new("RGBA", rgba.size, (32, 32, 32, 255)); dark.alpha_composite(rgba)
        dark.save(output / (stem + ".dark.png"))
        if rgba.width == 256:
            for shift in (16, 32, 64):
                wrapped = Image.new("RGBA", rgba.size)
                wrapped.paste(rgba.crop((rgba.width - shift, 0, rgba.width, rgba.height)), (0, 0))
                wrapped.paste(rgba.crop((0, 0, rgba.width - shift, rgba.height)), (shift, 0))
                wrapped_dark = Image.new("RGBA", wrapped.size, (32, 32, 32, 255))
                wrapped_dark.alpha_composite(wrapped)
                wrapped_dark.save(output / f"{stem}.wrap-shift-{shift}.png")
        if payload.startswith(MIG_MAGIC) and meta.get("pixel_format") == 9:
            area = meta["width"] * meta["height"]
            for alternate_width in (128, 512, 1024):
                if area % alternate_width:
                    continue
                alternate_height = area // alternate_width
                alternate = render_mig_dxt3_layout(payload, alternate_width, alternate_height).convert("RGBA")
                alternate_dark = Image.new("RGBA", alternate.size, (32, 32, 32, 255))
                alternate_dark.alpha_composite(alternate)
                alternate_dark.save(output / f"{stem}.layout-{alternate_width}x{alternate_height}.png")
            for block_offset in (-1, 1):
                shifted = render_mig_dxt3_block_offset(payload, block_offset).convert("RGBA")
                shifted_dark = Image.new("RGBA", shifted.size, (32, 32, 32, 255))
                shifted_dark.alpha_composite(shifted)
                shifted_dark.save(output / f"{stem}.block-offset-{block_offset:+d}.png")
        previews.append((stem, dark.convert("RGB")))
        rebuilt = build_container(payload, 9)
        roundtrip_valid, roundtrip_payload, roundtrip_error = verify_container_bytes(rebuilt)
        if not roundtrip_valid or roundtrip_payload != payload:
            raise ValueError(f"unchanged roundtrip failed {path}: {roundtrip_error}")
        rebuilt_path = output / (Path(path).name + ".roundtrip")
        rebuilt_path.write_bytes(rebuilt)
        allocated = math.ceil(record.data_length / SECTOR_SIZE) * SECTOR_SIZE
        rows.append({
            "iso_path": path, "extent_lba": record.extent_lba,
            "original_container_size": len(container), "allocated_size": allocated,
            "original_container_sha256": sha256(container),
            "dds_size": len(payload), "dds_sha256": sha256(payload),
            "roundtrip_container_size": len(rebuilt), "roundtrip_dds_identical": True,
            "roundtrip_fits_allocation": len(rebuilt) <= allocated,
            "dds_path": str(dds_path), "png_path": str(png_path), "mode": mode, **meta,
        })
    if previews:
        cell_width = max(320, max(image.width for _name, image in previews) + 32)
        cell_height = max(320, max(image.height for _name, image in previews) + 64)
        columns = min(3, len(previews)); rows_count = math.ceil(len(previews) / columns)
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows_count), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for index, (name, preview) in enumerate(previews):
            left = (index % columns) * cell_width; top = (index // columns) * cell_height
            sheet.paste(preview, (left + 16, top + 40))
            draw.text((left + 16, top + 12), name, fill=(255, 255, 255))
        sheet.save(output / "contact-sheet.png")
    report = {"schema_version": 1, "iso": str(iso), "name_contains": name_contains, "resource_count": len(rows), "resources": rows}
    (output / "extract-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def marker(dds: Path, output_dds: Path, output_png: Path, pixel_format: str, x: int, y: int) -> dict:
    with Image.open(dds) as source:
        source.load(); image = source.convert("RGBA")
    if not 0 <= x < image.width or not 0 <= y < image.height:
        raise ValueError("marker coordinate is outside the image")
    draw = ImageDraw.Draw(image)
    box = (x, y, min(image.width - 1, x + 7), min(image.height - 1, y + 7))
    draw.rectangle(box, fill=(255, 0, 255, 255), outline=(255, 255, 255, 255), width=1)
    output_dds.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_dds, pixel_format=pixel_format)
    image.save(output_png)
    with Image.open(output_dds) as check:
        check.load(); decoded = check.convert("RGBA")
    rebuilt_meta = dds_metadata(output_dds.read_bytes())
    container = build_container(output_dds.read_bytes(), 9)
    container_path = output_dds.with_suffix(output_dds.suffix + ".z")
    container_path.write_bytes(container)
    return {
        "source_dds": str(dds), "output_dds": str(output_dds), "output_png": str(output_png),
        "container": str(container_path), "marker_box": box, "requested_pixel_format": pixel_format,
        "decoded_mode": decoded.mode, "decoded_size": decoded.size,
        "dds_size": output_dds.stat().st_size, "container_size": len(container), **rebuilt_meta,
    }


def mig_marker(source: Path, output_mig: Path, output_png: Path, x: int, y: int, marker_size: int = 16) -> dict:
    data = bytearray(source.read_bytes()); root, palette, image = inspect_mig(data)
    info = image["payload"]
    if info["pixel_format"] == 9 and palette is None:
        original_data = bytes(data)
        rendered = render_any_mig(original_data, block_offset=1).convert("RGBA")
        if not 0 <= x < rendered.width or not 0 <= y < rendered.height: raise ValueError("marker coordinate is outside the image")
        box = (x, y, min(rendered.width - 1, x + marker_size - 1), min(rendered.height - 1, y + marker_size - 1))
        ImageDraw.Draw(rendered).rectangle(box, fill=(255, 0, 255, 255), outline=(255, 255, 255, 255), width=1)
        buffer = io.BytesIO(); rendered.save(buffer, format="DDS", pixel_format="DXT3"); encoded_dds = buffer.getvalue()
        encoded_blocks = pc_dxt3_to_psp(encoded_dds[128:])
        expected = info["width"] * info["height"]
        if len(encoded_blocks) != expected: raise ValueError(f"unexpected DXT3 payload size: {len(encoded_blocks)}/{expected}")
        image_start = image["offset"] + 16 + info["data_offset"]
        # Preserve all untouched compressed blocks byte-for-byte.  Re-encoding
        # the complete atlas would introduce compression drift outside the
        # requested edit and can disturb fully transparent padding pixels.
        blocks_per_row = info["width"] // 4
        changed_blocks = 0
        block_map = []
        total_blocks = expected // 16
        for block_y in range(box[1] // 4, box[3] // 4 + 1):
            for block_x in range(box[0] // 4, box[2] // 4 + 1):
                logical_index = block_y * blocks_per_row + block_x
                stored_index = (logical_index + 1) % total_blocks
                source_offset = logical_index * 16
                target = image_start + stored_index * 16
                data[target:target + 16] = encoded_blocks[source_offset:source_offset + 16]
                block_map.append({
                    "logical_block_x": block_x, "logical_block_y": block_y,
                    "logical_block_index": logical_index, "stored_block_index": stored_index,
                    "mig_file_offset": target,
                })
                changed_blocks += 1
        output_mig.parent.mkdir(parents=True, exist_ok=True); output_mig.write_bytes(data)
        verified = render_any_mig(bytes(data), block_offset=1)
        verified.save(output_png)
        container = build_container(bytes(data), 9); container_path = output_mig.with_suffix(output_mig.suffix + ".z"); container_path.write_bytes(container)
        report = {"source_mig":str(source),"output_mig":str(output_mig),"output_png":str(output_png),"container":str(container_path),"marker_box":box,"logical_block_offset":1,"changed_dxt3_blocks":changed_blocks,"block_map":block_map,"source_mig_sha256":sha256(original_data),"output_mig_sha256":sha256(bytes(data)),"output_png_sha256":sha256(output_png.read_bytes()),"container_sha256":sha256(container),"container_size":len(container),**mig_metadata(bytes(data))}
        report_path = output_mig.with_suffix(output_mig.suffix + ".marker-report.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report"] = str(report_path)
        return report
    if palette is None:
        raise ValueError("MIG marker requires a palette")
    palette_info = palette["payload"]
    width, height = info["width"], info["height"]
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("marker coordinate is outside the image")
    image_start = image["offset"] + 16 + info["data_offset"]
    stored = bytes(data[image_start:image_start + width * height])
    linear = bytearray(unswizzle_8bpp(stored, width, height) if info["pixel_order"] == 1 else stored)
    counts = [linear.count(index) for index in range(256)]
    raw_index = min(range(256), key=lambda index: counts[index])
    palette_index = clut_index(raw_index)
    palette_start = palette["offset"] + 16 + palette_info["data_offset"]
    color_offset = palette_start + palette_index * 4
    original_color = bytes(data[color_offset:color_offset + 4])
    data[color_offset:color_offset + 4] = bytes((255, 0, 255, 255))
    box = (x, y, min(width - 1, x + 7), min(height - 1, y + 7))
    for py in range(box[1], box[3] + 1):
        for px in range(box[0], box[2] + 1): linear[py * width + px] = raw_index
    encoded_indices = swizzle_8bpp(bytes(linear), width, height) if info["pixel_order"] == 1 else bytes(linear)
    data[image_start:image_start + width * height] = encoded_indices
    output_mig.parent.mkdir(parents=True, exist_ok=True); output_mig.write_bytes(data)
    rendered, _ = render_mig(bytes(data)); rendered.save(output_png)
    container = build_container(bytes(data), 9); container_path = output_mig.with_suffix(output_mig.suffix + ".z"); container_path.write_bytes(container)
    return {
        "source_mig": str(source), "output_mig": str(output_mig), "output_png": str(output_png),
        "container": str(container_path), "marker_box": box, "raw_palette_index": raw_index,
        "mapped_palette_index": palette_index, "previous_usage_count": counts[raw_index],
        "original_palette_rgba_hex": original_color.hex().upper(), "container_size": len(container),
        **mig_metadata(bytes(data)),
    }


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_extract = sub.add_parser("extract"); p_extract.add_argument("iso", type=Path); p_extract.add_argument("output", type=Path); p_extract.add_argument("--name-contains")
    p_marker = sub.add_parser("marker"); p_marker.add_argument("dds", type=Path); p_marker.add_argument("output_dds", type=Path); p_marker.add_argument("output_png", type=Path); p_marker.add_argument("--pixel-format", choices=("DXT1", "DXT3", "DXT5"), required=True); p_marker.add_argument("--x", type=int, default=2); p_marker.add_argument("--y", type=int, default=2)
    p_mig = sub.add_parser("mig-marker"); p_mig.add_argument("source", type=Path); p_mig.add_argument("output_mig", type=Path); p_mig.add_argument("output_png", type=Path); p_mig.add_argument("--x", type=int, default=2); p_mig.add_argument("--y", type=int, default=2); p_mig.add_argument("--size", type=int, default=16)
    args = parser.parse_args(argv)
    try:
        if args.command == "extract": result = extract(args.iso, args.output, args.name_contains)
        elif args.command == "marker": result = marker(args.dds, args.output_dds, args.output_png, args.pixel_format, args.x, args.y)
        else: result = mig_marker(args.source, args.output_mig, args.output_png, args.x, args.y, args.size)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (OSError, ValueError) as exc:
        print(f"메뉴 이미지 왕복 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
