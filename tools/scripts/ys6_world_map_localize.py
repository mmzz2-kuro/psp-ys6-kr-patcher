#!/usr/bin/env python3
"""Localize Ys VI's PSP world map while preserving pixels outside label regions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


LABELS = (
    {"text": "그라나바리스", "box": (104, 47, 176, 67), "position": (108, 50), "font_size": 9},
    {"text": "태양의 후미", "box": (192, 60, 242, 80), "position": (194, 62), "font_size": 8},
    {"text": "카난평원", "box": (205, 72, 265, 92), "position": (210, 74), "font_size": 9},
    {"text": "녹수동", "box": (190, 94, 224, 116), "position": (194, 97), "font_size": 9},
    {"text": "제메스의 성지", "box": (75, 106, 151, 126), "position": (79, 109), "font_size": 8},
    {"text": "항구도시 리모쥬", "box": (221, 130, 298, 161), "position": (229, 135), "font_size": 8, "fill": (180, 36, 30, 255)},
    {"text": "해안길", "box": (190, 144, 228, 167), "position": (195, 147), "font_size": 9},
    {"text": "바람개비언덕", "box": (83, 148, 153, 174), "position": (87, 151), "font_size": 8},
    {"text": "쿠아테라의 수해", "box": (102, 161, 184, 186), "position": (106, 164), "font_size": 8},
    {"text": "다리", "box": (177, 171, 207, 194), "position": (182, 175), "font_size": 9},
    {"text": "레다마을", "box": (124, 195, 171, 221), "position": (128, 198), "font_size": 8, "fill": (180, 36, 30, 255)},
    {"text": "기도의 샘", "box": (159, 193, 214, 220), "position": (164, 197), "font_size": 8},
    {"text": "달의 해변", "box": (87, 205, 137, 232), "position": (91, 209), "font_size": 8},
)

# Red location dots touch two red labels. Restore only these small marker cores
# after inpainting, not the Japanese red glyph pixels around them.
MARKERS = ((146, 121, 3), (242, 136, 3), (184, 179, 2), (145, 197, 3), (176, 202, 2))


def localize(source_path: Path, output_path: Path, font_path: Path, report_path: Path | None = None) -> dict:
    with Image.open(source_path) as opened:
        source = opened.convert("RGBA")
    if source.size != (320, 240):
        raise ValueError(f"expected 320x240 source, got {source.size}")

    source_array = np.asarray(source)
    bgr = cv2.cvtColor(source_array[:, :, :3], cv2.COLOR_RGB2BGR)
    label_box_mask = np.zeros((source.height, source.width), dtype=np.uint8)
    for label in LABELS:
        left, top, right, bottom = label["box"]
        label_box_mask[top:bottom, left:right] = 255
    blurred_bgr = cv2.GaussianBlur(bgr, (31, 31), 0)
    inward_distance = cv2.distanceTransform(label_box_mask, cv2.DIST_L2, 3)
    blend = np.clip(inward_distance / 3.0, 0.0, 1.0)[:, :, None]
    cleaned_bgr = np.rint(bgr * (1.0 - blend) + blurred_bgr * blend).astype(np.uint8)
    cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
    cleaned = Image.fromarray(cleaned_rgb, "RGB").convert("RGBA")
    cleaned.putalpha(source.getchannel("A"))

    # Preserve every pixel outside the explicit expanded label boxes exactly.
    composed = source.copy()
    composed.paste(cleaned, (0, 0), Image.fromarray(label_box_mask, "L"))

    source_pixels = source.load()
    output_pixels = composed.load()
    for center_x, center_y, radius in MARKERS:
        for y in range(max(0, center_y - radius), min(source.height, center_y + radius + 1)):
            for x in range(max(0, center_x - radius), min(source.width, center_x + radius + 1)):
                if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2:
                    output_pixels[x, y] = source_pixels[x, y]

    fonts = {
        size: ImageFont.truetype(str(font_path), size)
        for size in {int(label["font_size"]) for label in LABELS}
    }
    draw = ImageDraw.Draw(composed)
    for label in LABELS:
        draw.text(
            label["position"], label["text"], font=fonts[int(label["font_size"])],
            fill=label.get("fill", (238, 235, 220, 255)),
            stroke_width=1, stroke_fill=(48, 42, 34, 255),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(output_path)

    difference = np.any(np.asarray(source) != np.asarray(composed), axis=2)
    changed_pixels = int(difference.sum())
    changed_blocks = set()
    ys, xs = np.nonzero(difference)
    for x, y in zip(xs, ys):
        changed_blocks.add((int(x) // 4, int(y) // 4))
    outside_mask = difference & (label_box_mask == 0)
    report = {
        "source": str(source_path).replace("\\", "/"),
        "output": str(output_path).replace("\\", "/"),
        "size": list(composed.size),
        "labels": [
            {key: list(value) if isinstance(value, tuple) else value
             for key, value in label.items() if key != "fill"}
            for label in LABELS
        ],
        "changed_pixel_count": changed_pixels,
        "changed_block_count": len(changed_blocks),
        "removed_source_pixel_count": int((label_box_mask > 0).sum()),
        "outside_label_box_changed_pixel_count": int(outside_mask.sum()),
        "alpha_preserved": source.getchannel("A").tobytes() == composed.getchannel("A").tobytes(),
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/malgunbd.ttf"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    print(json.dumps(localize(args.source, args.output, args.font, args.report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
