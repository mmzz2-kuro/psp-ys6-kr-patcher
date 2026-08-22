#!/usr/bin/env python3
"""Remove Japanese tablet text and render approved Korean text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PAGES = {
    "p200": ["머지않아 내게 황혼이 찾아온다.", "진정한 어둠에 눈이 닫히기 전에", "이 몸에 새겨진 기억만은 글로 남겨 두리라.", "살과 함께 썩어 사라지지 않도록.", "우리 레다가", "한때 알마와 함께 카난 땅에 살았던 일.", "그 비호 아래 누린 평온한 나날과", "이윽고 찾아온 검은 재앙을."],
    "p201": ["과거가 밤의 어둠에 싸인 지도 오래되었다.", "알마의 모습을 마지막으로 본 레다로서", "나는 이것을 남긴다.", "강인하면서도 유연한 에멜라스 판은", "오랜 세월이 흐른 뒤에도", "읽는 이에게 틀림없는 글의 흔적을 보여 주리라.", "깊은 어둠에 도전하는 자여,", "그대에게 한 줄기 빛이 되기를 바랄 뿐이다."],
    "p210": ["먼저 이 글을 간직하고 있는", "에멜라스 자체에 관해", "기록해 두어야 한다.", "에멜라스는 에멜이라는 돌에서 뽑아낸", "결정질 섬유로,", "신들의 나라 엘딘에서 온 알마가", "이 땅에 전해 주었다."],
    "p211": ["그것은 그 나라의 나무이자", "강철이며", "어머니와도 같은 존재였다고 한다.", "얼지 않는 물로 가득한 가마 속에서", "여러 색의 에멜라스가 짜여지고", "마침내 힘을 지닌 검정과", "생명을 지닌 하양이", "만들어졌다."],
    "p212": ["검은 에멜라스는 모든 색의 힘을 함께 지녔고", "한편", "흰 에멜라스는", "그 검은 힘에 말을 거는 능력을 지녔다.", "이윽고 검은 힘은 대양의 수호자로 우뚝 섰고", "흰 광채는 날개가 되어 신들의 등에 깃들었다."],
    "p220": ["나는 또한 우리 레다와 마찬가지로", "알마의 백성으로서 이 땅에 살았던", "꼬리 없는 자들도 기록해 두어야 한다.", "그들은 영리했고", "스스로의 뜻을 이루는 강인함이 넘쳤으며", "알마의 기술을 익히자", "곧 직접 에멜라스를 짜낼 수 있게 되었다."],
    "p221": ["온갖 에멜라스를 짜는 기술을 익힌 그들은", "마침내 검정과 하양까지", "만들어 내기를 꿈꾸었지만", "알마는 결코 그 방법을 가르쳐 주지 않았다.", "검은 힘은 너무나 강대하여", "날개 없는 자가 다룰 수 없었기 때문이다.", "그래도 그들은 뜻을 버리지 않고", "자신들의 굴속에서 외로운 연구를 계속했다."],
    "p222": ["하지만 그들이 칠흑의 빛을 보는 날은", "끝내 찾아오지 않았다.", "그 가마에서 태어난 것은", "희지도 검지도 않은", "잿빛 에멜라스뿐이었다."],
    "p230": ["이 카난 땅을 덮친 재앙과", "검은 에멜라스의 상자에 대해서도", "기록해 두어야 한다.", "알마가 세웠다고 전해지는 칠흑의 상자는", "그 힘으로 바람과 파도를 잠재우고", "엘딘의 세상에 두루 평안을 가져다주었다."],
    "p231": ["하지만 꼬리 없는 자들이", "검은 에멜라스의 비밀을 찾아 안으로 들어섰을 때", "상자의 힘은 재앙이 되어 쏟아져 내렸다.", "어리석게도 그들은 상자를 조종하려 했다.", "흰 광채 없이는 검은 힘을 다스릴 수 없다.", "상자는 광기에 이끌렸고", "바다는 넘쳐흘렀다."],
    "p232": ["알마가 상자를 잠재웠을 때에는", "높은 곳만 남긴 채 육지가 물속으로 사라지고", "카난 땅도 섬으로 모습을 바꾼 뒤였다.", "함께 따르던 우리 레다의 무사를 확인한 알마는", "커다랗게 날개를 펼쳤다.", "그리고 흰 육신을 그 자리에 남긴 채", "하늘로 돌아갔다."],
    "p240": ["모든 것을 잃은 뒤에도", "내게는 아직 기록할 것이 남아 있다.", "재앙이 일으킨 거대한 파도는", "멀리 신들의 땅에까지 미쳤다.", "많은 신은 그곳에서 하늘로 돌아가기를 바랐지만", "레다와 꼬리 없는 자들을 이끌고", "새로운 대지로 떠난 신들도 있었다고 한다."],
    "p241": ["그리고 우리 카난의 레다는", "세상을 떠난 알마의 영혼을 지키기 위해", "섬이 된 이 땅에서 살아가기를 택했다.", "머지않아 나 또한", "저 흰 날개에 안겨 성스러운 땅으로 향하리라."],
    "p242": ["과거의 기억은 멀어지고", "이제 황혼의 기척만이 가까이 와 있다.", "하지만 두렵지 않다.", "어둠을 지나지 않고서는", "아침이 찾아오지 않으니.", "카난의 바다에 다시 고요가 돌아오는 날까지", "이 글을 읽는 자여,", "자애로운 알마의 축복이 그대와 함께하기를."],
}


def text_mask(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    candidate = ((hsv[:, :, 1] < 75) & (hsv[:, :, 2] > 150)).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(candidate, 8)
    mask = np.zeros(candidate.shape, np.uint8)
    for label in range(1, count):
        x, y, width, height, area = stats[label]
        if 2 <= area <= 260 and width <= 32 and height <= 32 and 4 <= y <= 266:
            mask[labels == label] = 255
    return cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 11)), iterations=1)


def localize(source: Path, lines: list[str], font_path: Path) -> tuple[Image.Image, Image.Image, dict]:
    image = Image.open(source).convert("RGB")
    rgb = np.asarray(image)
    mask = text_mask(rgb)
    clean = cv2.inpaint(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mask, 5, cv2.INPAINT_TELEA)
    clean_rgb = cv2.cvtColor(clean, cv2.COLOR_BGR2RGB)
    output = Image.fromarray(clean_rgb).convert("RGBA")
    draw = ImageDraw.Draw(output)
    font = ImageFont.truetype(str(font_path), 17, index=0)
    line_step = 29
    top = (272 - line_step * len(lines)) // 2
    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        x = (480 - (box[2] - box[0])) // 2
        y = top + index * line_step
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return output, Image.fromarray(clean_rgb), {"mask_pixels": int(np.count_nonzero(mask)), "line_count": len(lines)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("tools/patchdata/ys6_additional_images"))
    parser.add_argument("--source-dir", type=Path, default=Path("tools/patchdata/work/current/image-discovery/tabulas"))
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/gulim.ttc"))
    args = parser.parse_args()
    reports = []
    for stem, lines in PAGES.items():
        resource_id = f"tabulas_{stem}"
        target = args.workspace / "edited_parts" / resource_id
        target.mkdir(parents=True, exist_ok=True)
        output, clean, report = localize(args.source_dir / f"{stem}.png", lines, args.font)
        output.save(target / "page.png")
        clean.save(args.workspace / f"{resource_id}-background-preview.png")
        preview = Image.new("RGBA", output.size, (20, 20, 20, 255)); preview.alpha_composite(output)
        preview.save(args.workspace / f"{resource_id}-preview.png")
        reports.append({"id": resource_id, **report})
    result = {"valid": True, "font": args.font.as_posix(), "pages": reports}
    (args.workspace / "tabulas-localize-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
