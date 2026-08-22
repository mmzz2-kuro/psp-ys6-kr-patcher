#!/usr/bin/env python3
"""Create and register Korean v130-v132 ending message images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MESSAGES = {
    "v130": ["수많은 인과를 집어삼켜 온", "숙업의 소용돌이는 이제 사라지고."],
    "v131": ["바다도, 하늘도, 끝없이 푸르게 펼쳐져 있었다."],
    "v132": ["새로운 세계의 막이 오르고――", "지금 다시, 아돌의 모험이 시작된다."],
}


def fitted_font(draw: ImageDraw.ImageDraw, lines: list[str], font_path: Path) -> tuple[ImageFont.FreeTypeFont, int, int]:
    for size in range(19, 10, -1):
        font = ImageFont.truetype(str(font_path), size, index=0)
        step = size + 5
        if all(draw.textbbox((0, 0), line, font=font, stroke_width=2)[2] <= 472 for line in lines):
            if step * len(lines) - 2 <= 60:
                return font, size, step
    raise ValueError(f"text does not fit: {lines}")


def render(lines: list[str], font_path: Path) -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", (480, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font, size, step = fitted_font(draw, lines, font_path)
    total_height = step * len(lines) - 2
    top = (64 - total_height) // 2
    boxes = []
    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        width = box[2] - box[0]
        desired_top = top + index * step
        x = (480 - width) // 2 - box[0]
        y = desired_top - box[1]
        draw.text((x, y), line, font=font, fill=(245, 245, 245, 255),
                  stroke_width=2, stroke_fill=(16, 16, 16, 255))
        boxes.append([x + box[0], desired_top, x + box[2], desired_top + box[3] - box[1]])
    return image, {"font_size": size, "line_boxes": boxes,
                   "alpha_bbox": list(image.getchannel("A").getbbox())}


def resource(stem: str) -> dict:
    resource_id = f"ending_message_{stem}"
    return {
        "id": resource_id,
        "source_png": f"source_images/ending_messages/{stem}.png",
        "iso_path": f"PSP_GAME/USRDIR/data/image/{stem}.dds.z",
        "size": [480, 64],
        "pixel_format": "mixed RGBA8888/DXT1" if stem == "v130" else "PSP_DXT1",
        "note": f"Korean localized ending message {stem}",
        "regions": [{
            "id": "message", "source_text": " / ".join(MESSAGES[stem]),
            "translation": " / ".join(MESSAGES[stem]), "file": "message.png",
            "box": [0, 0, 480, 64], "width": 480, "height": 64,
        }],
        "collection_pictures": [
            {"picture_index": 0, "box": [0, 0, 256, 64]},
            {"picture_index": 1, "box": [256, 0, 384, 64]},
            {"picture_index": 2, "box": [384, 0, 448, 64]},
            {"picture_index": 3, "box": [448, 0, 480, 64]},
        ],
        "source_block_offset_applied": True,
        "runtime_copies": [{
            "archive_path": "PSP_GAME/USRDIR/data/arc/s_0002.bin",
            "entry_index": 26 + int(stem[1:]) - 130,
            "entry_name": f"{stem}.dds.z", "flags_hex": "0x01000000",
        }],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("tools/patchdata/ys6_additional_images"))
    parser.add_argument("--preview-source", type=Path,
                        default=Path("tools/patchdata/work/current/090-untranslated-image-candidate-preview"))
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/gulim.ttc"))
    args = parser.parse_args()
    if not args.font.is_file():
        raise SystemExit(f"font not found: {args.font}")

    manifest_path = args.workspace / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    ids = {f"ending_message_{stem}" for stem in MESSAGES}
    manifest["resources"] = [row for row in manifest["resources"] if row["id"] not in ids]
    reports = []
    preview = Image.new("RGBA", (960, 444), (28, 28, 28, 255))
    preview_draw = ImageDraw.Draw(preview)
    for position, (stem, lines) in enumerate(MESSAGES.items()):
        resource_id = f"ending_message_{stem}"
        source = Image.open(args.preview_source / f"{stem}.png").convert("RGBA")
        source_image = args.workspace / "source_images" / "ending_messages" / f"{stem}.png"
        source_part = args.workspace / "source_parts" / resource_id / "message.png"
        edited_part = args.workspace / "edited_parts" / resource_id / "message.png"
        for path in (source_image, source_part, edited_part):
            path.parent.mkdir(parents=True, exist_ok=True)
        source.save(source_image)
        source.save(source_part)
        edited, detail = render(lines, args.font)
        edited.save(edited_part)
        top = position * 148
        preview_draw.text((5, top + 3), resource_id, fill="white")
        preview.alpha_composite(edited.resize((960, 128), Image.Resampling.NEAREST), (0, top + 20))
        reports.append({"id": resource_id, "translation": lines, "output": edited_part.as_posix(), **detail})
        manifest["resources"].append(resource(stem))

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_path = args.workspace / "ending-message-preview-2x.png"
    preview.save(preview_path)
    report = {"valid": True, "font": args.font.as_posix(), "resources": reports,
              "preview": preview_path.as_posix(), "manifest_resource_count": len(manifest["resources"])}
    (args.workspace / "ending-message-localize-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
