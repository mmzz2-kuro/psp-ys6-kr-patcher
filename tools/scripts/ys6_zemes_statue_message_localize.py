#!/usr/bin/env python3
"""Render approved Korean v100-v108 Zemes statue message images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MESSAGES = {
    "v100": ["……잘 왔도다……"],
    "v101": ["내 이름은 알마……", "위대한 《상자》를 봉인한 자……"],
    "v102": ["내 육신은 이곳에서 스러질지라도", "그 혼은 후손들에게 이어지리라……"],
    "v103": ["검사여……", "머나먼 땅에서 동포들을 구한 자여……"],
    "v104": ["마지막 《열쇠》를 그대에게 맡기리라……"],
    "v105": ["검사여……명심하라……"],
    "v106": ["……빼앗긴 《검은 열쇠》가", "《상자》의 뚜껑을 열려 하고 있다……"],
    "v107": ["……사악한 꿈이……되살아나기 전에……"],
}


def fitted_font(draw: ImageDraw.ImageDraw, lines: list[str], font_path: Path,
                maximum: int = 18, minimum: int = 11) -> tuple[ImageFont.FreeTypeFont, int]:
    for size in range(maximum, minimum - 1, -1):
        font = ImageFont.truetype(str(font_path), size, index=0)
        if all(draw.textbbox((0, 0), line, font=font, stroke_width=2)[2] <= 252 for line in lines):
            return font, size
    raise ValueError(f"text does not fit at {minimum}px: {lines}")


def render(lines: list[str], font_path: Path) -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", (256, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font, size = fitted_font(draw, lines, font_path)
    line_height = size + 8
    total_height = line_height * len(lines) - 4
    top = (64 - total_height) // 2
    boxes = []
    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        width = box[2] - box[0]
        x = (256 - width) // 2 - box[0]
        desired_top = top + index * line_height
        y = desired_top - box[1]
        draw.text((x, y), line, font=font, fill=(245, 245, 245, 255),
                  stroke_width=2, stroke_fill=(16, 16, 16, 255))
        boxes.append([x + box[0], desired_top, x + box[2], desired_top + box[3] - box[1]])
    return image, {"font_size": size, "line_boxes": boxes,
                   "alpha_bbox": list(image.getchannel("A").getbbox())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path,
                        default=Path("tools/patchdata/ys6_additional_images"))
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/gulim.ttc"))
    args = parser.parse_args()
    if not args.font.is_file():
        raise SystemExit(f"font not found: {args.font}")

    source_root = args.workspace / "source_images" / "zemes_statue_messages"
    preview = Image.new("RGBA", (768, 288), (28, 28, 28, 255))
    preview_draw = ImageDraw.Draw(preview)
    reports = []
    for position, stem in enumerate([f"v{index}" for index in range(100, 109)]):
        resource_id = f"zemes_statue_{stem}"
        source = source_root / f"{stem}.png"
        source_part = args.workspace / "source_parts" / resource_id / "message.png"
        edited = args.workspace / "edited_parts" / resource_id / "message.png"
        source_part.parent.mkdir(parents=True, exist_ok=True)
        edited.parent.mkdir(parents=True, exist_ok=True)
        original = Image.open(source).convert("RGBA")
        original.save(source_part)
        if stem == "v108":
            output = original.copy()
            detail = {"font_size": None, "line_boxes": [],
                      "alpha_bbox": list(output.getchannel("A").getbbox())}
            lines = ["(원문 점 표시 유지)"]
        else:
            lines = MESSAGES[stem]
            output, detail = render(lines, args.font)
        output.save(edited)
        left = position % 3 * 256
        top = position // 3 * 96
        preview.alpha_composite(output, (left, top + 24))
        preview_draw.text((left + 5, top + 5), resource_id, fill=(255, 255, 255, 255))
        reports.append({"id": resource_id, "translation": lines,
                        "output": edited.as_posix(), **detail})
    preview_path = args.workspace / "zemes-statue-message-preview.png"
    preview.save(preview_path)
    report = {"valid": True, "font": args.font.as_posix(), "resources": reports,
              "preview": preview_path.as_posix()}
    (args.workspace / "zemes-statue-message-localize-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
