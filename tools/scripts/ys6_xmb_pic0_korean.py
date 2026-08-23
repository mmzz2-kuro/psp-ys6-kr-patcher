#!/usr/bin/env python3
"""Create a deterministic Korean Ys VI PSP XMB PIC0 preview."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 310, 180
COPYRIGHT_TOP = 153
TITLE = "이스 ~나피쉬팀의 상자~"
BODY = (
    "전해지는 「다정함」,",
    "펼쳐지는 「모험심」―.",
    "",
    "무대는 대륙의 아득한 서쪽, 바다 끝―.",
    "절해의 외딴섬에서 펼쳐지는",
    "아돌의 새로운 모험!",
    "성장하는 세 자루의 에메라스 검과",
    "다채로운 액션으로 적을 물리치자!",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def centered(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont,
             fill: tuple[int, int, int, int], stroke_width: int = 1) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = (WIDTH - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width,
              stroke_fill=(0, 0, 0, fill[3]), anchor=None)


def build(source: Path, background: Path, output: Path, composite: Path, font_path: Path) -> dict:
    original = Image.open(source).convert("RGBA")
    if original.size != (WIDTH, HEIGHT):
        raise ValueError(f"PIC0 규격 불일치: {original.size}")

    result = original.copy()
    # Preserve the two original copyright rows exactly; clear only Japanese/title content.
    result.paste((0, 0, 0, 0), (0, 0, WIDTH, COPYRIGHT_TOP))
    draw = ImageDraw.Draw(result)
    title_font = ImageFont.truetype(str(font_path), 13)
    body_font = ImageFont.truetype(str(font_path), 11)
    centered(draw, 0, TITLE, title_font, (198, 245, 255, 255), 1)
    y = 20
    for line in BODY:
        if line:
            centered(draw, y, line, body_font, (255, 255, 255, 255), 1)
        y += 15 if line else 8

    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, format="PNG", optimize=True, compress_level=9)

    bg = Image.open(background).convert("RGBA")
    if bg.size != (480, 272):
        raise ValueError(f"PIC1 규격 불일치: {bg.size}")
    preview = bg.copy()
    preview.alpha_composite(result, (170, 92))
    preview.convert("RGB").save(composite, format="PNG", optimize=True, compress_level=9)

    report = {
        "source": str(source),
        "output": str(output),
        "output_size": output.stat().st_size,
        "output_sha256": sha256(output),
        "allocated_limit": 57344,
        "fits_iso_extent": output.stat().st_size <= 57344,
        "composite": str(composite),
        "font": str(font_path),
        "copyright_top": COPYRIGHT_TOP,
        "title": TITLE,
        "body": list(BODY),
    }
    (output.parent / "draft-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ys VI XMB PIC0 한글 시안 생성")
    parser.add_argument("source", type=Path)
    parser.add_argument("background", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("composite", type=Path)
    parser.add_argument("--font", type=Path, default=Path(r"C:\Windows\Fonts\malgun.ttf"))
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.background, args.output, args.composite, args.font), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
