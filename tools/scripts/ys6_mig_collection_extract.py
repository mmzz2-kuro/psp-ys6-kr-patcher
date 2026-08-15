#!/usr/bin/env python3
"""Extract every picture section from a multi-picture Ys VI PSP MIG texture."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.scripts.ys6_mig_texture import payload_header, section, unswizzle_8bpp
except ModuleNotFoundError:
    from ys6_mig_texture import payload_header, section, unswizzle_8bpp


MAGIC = b"MIG.00.1PSP\0"


def psp_dxt1_to_pc(blocks: bytes) -> bytes:
    output = bytearray()
    for offset in range(0, len(blocks), 8):
        block = blocks[offset:offset + 8]
        output.extend(block[4:8] + block[0:4])
    return bytes(output)


def psp_dxt3_to_pc(blocks: bytes) -> bytes:
    if len(blocks) % 16:
        raise ValueError("DXT3 data is not block aligned")
    output = bytearray(len(blocks))
    for offset in range(0, len(blocks), 16):
        block = blocks[offset:offset + 16]
        output[offset:offset + 16] = block[8:16] + block[4:8] + block[0:4]
    return bytes(output)


def decode_16bit(value: int, pixel_format: int) -> tuple[int, int, int, int]:
    if pixel_format == 0:  # RGB5650
        r, g, b, a = (value & 31), ((value >> 5) & 63), ((value >> 11) & 31), 255
        return (r * 255 // 31, g * 255 // 63, b * 255 // 31, a)
    if pixel_format == 1:  # RGBA5551
        r, g, b, a = (value & 31), ((value >> 5) & 31), ((value >> 10) & 31), 255 if value & 0x8000 else 0
        return (r * 255 // 31, g * 255 // 31, b * 255 // 31, a)
    if pixel_format == 2:  # RGBA4444
        r, g, b, a = (value & 15), ((value >> 4) & 15), ((value >> 8) & 15), ((value >> 12) & 15)
        return (r * 17, g * 17, b * 17, a * 17)
    raise ValueError(f"unsupported 16-bit pixel format: {pixel_format}")


def palette_colors(data: bytes, palette: dict) -> list[tuple[int, int, int, int]]:
    info = palette["payload"]
    start = palette["offset"] + 16 + info["data_offset"]
    count = info["width"] * info["height"]
    if info["pixel_format"] == 3:
        raw = data[start:start + count * 4]
        return [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    raw = data[start:start + count * 2]
    return [decode_16bit(int.from_bytes(raw[i:i + 2], "little"), info["pixel_format"])
            for i in range(0, len(raw), 2)]


def render_picture(data: bytes, palette: dict | None, image: dict) -> Image.Image:
    info = image["payload"]
    width, height = info["width"], info["height"]
    start = image["offset"] + 16 + info["data_offset"]
    if info["pixel_format"] == 5 and palette is not None:
        raw = data[start:start + width * height]
        if info["pixel_order"] == 1:
            raw = unswizzle_8bpp(raw, width, height)
        colors = palette_colors(data, palette)
        rgba = bytearray()
        for raw_index in raw:
            index = ((raw_index & 0xE7) | ((raw_index & 0x08) << 1) | ((raw_index & 0x10) >> 1))
            rgba.extend(colors[index])
        return Image.frombytes("RGBA", (width, height), bytes(rgba))
    if info["pixel_format"] == 8 and palette is None:
        size = width * height // 2
        return Image.frombytes("RGBA", (width, height), psp_dxt1_to_pc(data[start:start + size]), "bcn", (1,))
    if info["pixel_format"] == 9 and palette is None:
        size = width * height
        return Image.frombytes("RGBA", (width, height), psp_dxt3_to_pc(data[start:start + size]), "bcn", (2,))
    raise ValueError(
        f"unsupported image format={info['pixel_format']} bpp={info['bits_per_pixel']} order={info['pixel_order']}"
    )


def iter_pictures(data: bytes):
    if not data.startswith(MAGIC):
        raise ValueError("input is not MIG.00.1PSP")
    root = section(data, 16)
    cursor = 32
    index = 0
    while cursor < 16 + root["size"]:
        picture = section(data, cursor)
        if picture["kind"] != 3 or picture["size"] <= 0:
            break
        palette = None
        image = None
        child_offset = cursor + picture["child_offset"]
        while child_offset < cursor + picture["size"]:
            child = section(data, child_offset)
            if child["kind"] in (4, 5):
                child["payload"] = payload_header(data, child_offset)
                if child["kind"] == 4:
                    image = child
                else:
                    palette = child
            if child["size"] <= 0:
                break
            child_offset += child["size"]
        if image is not None:
            yield index, cursor, picture, palette, image
        cursor += picture["size"]
        index += 1


def extract(source: Path, output: Path) -> dict:
    data = source.read_bytes()
    images_dir = output / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    records = []
    previews = []
    for index, picture_offset, picture, palette, image_section in iter_pictures(data):
        info = image_section["payload"]
        record = {
            "index": index,
            "picture_offset": picture_offset,
            "picture_size": picture["size"],
            "image_section_offset": image_section["offset"],
            "width": info["width"],
            "height": info["height"],
            "pixel_format": info["pixel_format"],
            "pixel_order": info["pixel_order"],
            "bits_per_pixel": info["bits_per_pixel"],
            "palette_format": palette["payload"]["pixel_format"] if palette else None,
        }
        try:
            rendered = render_picture(data, palette, image_section)
            name = f"{index:03d}_{info['width']}x{info['height']}_pf{info['pixel_format']}.png"
            rendered.save(images_dir / name)
            record["png"] = str(images_dir / name)
            record["rendered"] = True
            if info["width"] >= 64 and info["height"] >= 16:
                previews.append((index, rendered))
        except Exception as exc:
            record["rendered"] = False
            record["error"] = str(exc)
        records.append(record)

    cell_width, cell_height, columns = 288, 304, 4
    for page_index in range(math.ceil(len(previews) / 24)):
        page = previews[page_index * 24:(page_index + 1) * 24]
        rows = math.ceil(len(page) / columns)
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for position, (index, image) in enumerate(page):
            left = position % columns * cell_width
            top = position // columns * cell_height
            preview = image.copy()
            preview.thumbnail((256, 256), Image.Resampling.NEAREST)
            dark = Image.new("RGBA", preview.size, (32, 32, 32, 255))
            dark.alpha_composite(preview.convert("RGBA"))
            sheet.paste(dark.convert("RGB"), (left + 16, top + 36))
            draw.text((left + 16, top + 12), f"index {index:03d}  {image.width}x{image.height}", fill="white")
        sheet.save(output / f"contact-sheet-{page_index + 1:02d}.png")

    report = {
        "source": str(source),
        "picture_count": len(records),
        "rendered_count": sum(record["rendered"] for record in records),
        "contact_sheet_count": math.ceil(len(previews) / 24),
        "pictures": records,
    }
    (output / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = extract(args.source, args.output)
    print(json.dumps({key: report[key] for key in ("picture_count", "rendered_count", "contact_sheet_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
