#!/usr/bin/env python3
"""Render deterministic Korean boss-title texture parts for Ys VI PSP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROWS = {
    "boss_names_00": [
        ("떠돌이 용", "데미갈바"),
        ("탐욕스러운 날개", "존프라스"),
        ("창람의 수호자", "우드＝메이유"),
        ("공허한 포효", "오쥬간"),
    ],
    "boss_names_01": [
        ("혼돈의 사냥꾼", "라나루나"),
        ("용신병 완전체", "갈바로아"),
        ("검은 열쇠의 계승자", "에른스트"),
        ("외해 기구", "나피쉬팀"),
    ],
}


def render_row(title: str, name: str, font_path: Path) -> Image.Image:
    image = Image.new("RGBA", (256, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(font_path), 14, index=0)
    name_font = ImageFont.truetype(str(font_path), 25, index=0)
    draw.text((5, -2), f"「{title}」", font=title_font, fill=(255, 255, 255, 255), stroke_width=0)
    draw.text((5, 27), name, font=name_font, fill=(255, 255, 255, 255), stroke_width=0)
    name_box = draw.textbbox((5, 27), name, font=name_font)
    right = min(251, max(40, name_box[2] + 4))
    draw.line((5, 61, right, 61), fill=(255, 255, 255, 255), width=1)
    draw.line((5, 62, right, 62), fill=(255, 255, 255, 204), width=1)
    draw.line((5, 63, right, 63), fill=(255, 255, 255, 136), width=1)
    return image


def build(workspace: Path, font_path: Path) -> dict:
    outputs = []
    previews = []
    for resource_id, rows in ROWS.items():
        target = workspace / "edited_parts" / resource_id
        target.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
        for index, (title, name) in enumerate(rows, 1):
            output = target / f"line_{index:02d}.png"
            image = render_row(title, name, font_path)
            image.save(output)
            sheet.alpha_composite(image, (0, (index - 1) * 64))
            outputs.append({
                "resource_id": resource_id,
                "line": index,
                "title": title,
                "name": name,
                "path": output.as_posix(),
                "size": list(image.size),
                "alpha_bbox": list(image.getchannel("A").getbbox()),
            })
        preview = Image.new("RGBA", sheet.size, (20, 24, 28, 255))
        preview.alpha_composite(sheet)
        preview_path = workspace / f"{resource_id}-preview-dark.png"
        preview.save(preview_path)
        previews.append(preview_path.as_posix())
    report = {"valid": True, "font": font_path.as_posix(), "outputs": outputs, "previews": previews}
    report_path = workspace / "boss-name-localize-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("tools/patchdata/ys6_additional_images"))
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/gulim.ttc"))
    args = parser.parse_args()
    if not args.font.is_file():
        raise SystemExit(f"font not found: {args.font}")
    print(json.dumps(build(args.workspace, args.font), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
