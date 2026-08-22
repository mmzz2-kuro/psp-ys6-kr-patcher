#!/usr/bin/env python3
"""Render Korean v140/v141 and v150-v157 message images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MESSAGES = {
    "v140": ["제어 키의 기능 정지를 확인……"],
    "v141": ["지금부터 자동 제어 상태로 이행한다……"],
    "v150": ["나는 아틀라스해 전역을 관리하는", "기상 제어 기구 《나피쉬팀》……"],
    "v151": ["알마에 의해 봉인된 후", "나는 깊은 잠 속에서 꿈을 꾸고 있었다……"],
    "v152": ["위대한 엘딘의 황혼과", "그 씨앗이 에레시아 땅에 뿌리내리는 것을……"],
    "v153": ["하지만 천 년이 지난 지금……", "모든 것은 수포로 돌아간 것 같다……"],
    "v154": ["이제 에레시아 땅에서", "엘딘의 정신은 완전히 사라졌다……"],
    "v155": ["거짓 문명은 멸망해야 한다……"],
    "v156": ["역장에 의한 수벽 전개를 종료……", "에레시아 대륙 서해안 지역을", "소거할 수 있다……"],
    "v157": ["지금부터 최종 단계로 이행한다……"],
}


def fitted_font(draw: ImageDraw.ImageDraw, lines: list[str], font_path: Path,
                maximum: int = 18, minimum: int = 11) -> tuple[ImageFont.FreeTypeFont, int, int]:
    for size in range(maximum, minimum - 1, -1):
        font = ImageFont.truetype(str(font_path), size, index=0)
        step = size + 5
        total_height = step * len(lines) - 2
        fits_width = all(
            draw.textbbox((0, 0), line, font=font, stroke_width=2)[2] <= 252
            for line in lines)
        if fits_width and total_height <= 62:
            return font, size, step
    raise ValueError(f"text does not fit: {lines}")


def render(lines: list[str], font_path: Path) -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", (256, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font, size, line_step = fitted_font(draw, lines, font_path)
    total_height = line_step * len(lines) - 2
    top = (64 - total_height) // 2
    boxes = []
    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        width = box[2] - box[0]
        x = (256 - width) // 2 - box[0]
        desired_top = top + index * line_step
        y = desired_top - box[1]
        draw.text((x, y), line, font=font, fill=(245, 245, 245, 255),
                  stroke_width=2, stroke_fill=(16, 16, 16, 255))
        boxes.append([x + box[0], desired_top, x + box[2], desired_top + box[3] - box[1]])
    return image, {
        "font_size": size,
        "line_boxes": boxes,
        "alpha_bbox": list(image.getchannel("A").getbbox()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path,
                        default=Path("tools/patchdata/ys6_additional_images"))
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/gulim.ttc"))
    args = parser.parse_args()
    if not args.font.is_file():
        raise SystemExit(f"font not found: {args.font}")

    source_root = args.workspace / "source_images" / "control_key_messages"
    stems = ["v140", "v141"] + [f"v{index}" for index in range(150, 158)]
    preview = Image.new("RGBA", (1280, 176), (28, 28, 28, 255))
    preview_draw = ImageDraw.Draw(preview)
    reports = []
    for position, stem in enumerate(stems):
        resource_id = f"control_message_{stem}"
        source = Image.open(source_root / f"{stem}.png").convert("RGBA")
        source_part = args.workspace / "source_parts" / resource_id / "message.png"
        edited = args.workspace / "edited_parts" / resource_id / "message.png"
        source_part.parent.mkdir(parents=True, exist_ok=True)
        edited.parent.mkdir(parents=True, exist_ok=True)
        source.save(source_part)
        output, detail = render(MESSAGES[stem], args.font)
        output.save(edited)
        left = position % 5 * 256
        top = position // 5 * 88
        preview.alpha_composite(output, (left, top + 20))
        preview_draw.text((left + 5, top + 3), resource_id, fill=(255, 255, 255, 255))
        reports.append({
            "id": resource_id,
            "translation": MESSAGES[stem],
            "output": edited.as_posix(),
            **detail,
        })
    preview_path = args.workspace / "control-key-message-preview.png"
    preview.save(preview_path)
    report = {
        "valid": True,
        "font": args.font.as_posix(),
        "resources": reports,
        "preview": preview_path.as_posix(),
    }
    (args.workspace / "control-key-message-localize-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
