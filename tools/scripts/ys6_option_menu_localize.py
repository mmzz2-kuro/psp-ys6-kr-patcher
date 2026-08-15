#!/usr/bin/env python3
"""Create low-change Korean option-menu PNGs from extracted source buttons."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


BUTTONS = {
    "se_volume.png": ("효과음 볼륨", 13),
    "voice_volume.png": ("음성 볼륨", 13),
    "reset_default.png": ("기본값 복원", 13),
    "key_config.png": ("키 설정", 13),
    "save.png": ("저장", 13),
    "return_title.png": ("타이틀 화면으로", 12),
}


def remove_bright_glyphs(path: Path, *, threshold: int = 150) -> Image.Image:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"이미지를 열 수 없습니다: {path}")
    maximum = bgr.max(axis=2)
    minimum = bgr.min(axis=2)
    yy, xx = np.indices(maximum.shape)
    mask = (
        (maximum > threshold)
        & ((maximum - minimum) < 32)
        & (xx > 20)
        & (xx < bgr.shape[1] - 20)
        & (yy > 2)
        & (yy < bgr.shape[0] - 2)
    ).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    clean = cv2.inpaint(bgr, mask, 1.5, cv2.INPAINT_NS)
    return Image.fromarray(cv2.cvtColor(clean, cv2.COLOR_BGR2RGB))


def draw_centered(image: Image.Image, text: str, font_path: Path, size: int) -> None:
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), size)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    x = (image.width - (box[2] - box[0])) // 2 - box[0]
    y = (image.height - (box[3] - box[1])) // 2 - box[1] - 1
    draw.text(
        (x, y), text, font=font, fill=(238, 238, 232),
        stroke_width=1, stroke_fill=(20, 15, 12),
    )


def build(source: Path, output: Path, font_path: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for filename, (text, size) in BUTTONS.items():
        image = remove_bright_glyphs(source / filename)
        draw_centered(image, text, font_path, size)
        image.save(output / filename)

    filename = "dialogue_unselected.png"
    image = remove_bright_glyphs(source / filename, threshold=135)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), 10)
    text = "타이틀 화면으로\n돌아가시겠습니까?"
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=0, align="center", stroke_width=1)
    x = (image.width - (box[2] - box[0])) // 2 - box[0]
    y = (image.height - (box[3] - box[1])) // 2 - box[1]
    draw.multiline_text(
        (x, y), text, font=font, spacing=0, align="center",
        fill=(238, 238, 232), stroke_width=1, stroke_fill=(20, 15, 12),
    )
    image.save(output / filename)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/malgunbd.ttf"))
    args = parser.parse_args()
    build(args.source, args.output, args.font)
    print(f"생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
