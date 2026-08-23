#!/usr/bin/env python3
"""Composite Korean dialogue into the two Ys VI ending movie previews."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


FPS = "30000/1001"
WIDTH, HEIGHT = 480, 272
NAME_ROI = (124, 170, 350, 188)
BODY_ROI = (124, 191, 430, 252)
NAME_POS = (132, 172)
BODY_POS = (130, 195)
BODY_LINE_STEP = 22
PANEL_MEAN_THRESHOLD = 46.0


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def glyph_mask(frame: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = roi
    patch = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    # Dialogue glyphs are pale and nearly achromatic. Dilation also removes their dark outline.
    mask = np.where((gray >= 118) & (hsv[:, :, 1] <= 92), 255, 0).astype(np.uint8)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    return mask


def erase_japanese(frame: np.ndarray, roi: tuple[int, int, int, int], mask: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = roi
    patch = frame[y1:y2, x1:x2]
    restored = cv2.inpaint(patch, mask, 3, cv2.INPAINT_TELEA)
    result = frame.copy()
    result[y1:y2, x1:x2] = restored
    return result


def draw_korean(
    frame: np.ndarray,
    speaker: str,
    translation: str,
    name_font: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
) -> np.ndarray:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    fill = (238, 238, 232)
    stroke = (15, 15, 18)
    draw.text(NAME_POS, speaker, font=name_font, fill=fill, stroke_width=1, stroke_fill=stroke)
    for line_no, line in enumerate(translation.split("\\n")):
        draw.text(
            (BODY_POS[0], BODY_POS[1] + line_no * BODY_LINE_STEP),
            line,
            font=body_font,
            fill=fill,
            stroke_width=1,
            stroke_fill=stroke,
        )
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def build_lookup(rows: list[dict]) -> tuple[dict[int, dict], int]:
    lookup: dict[int, dict] = {}
    for row in rows:
        for frame_no in range(row["start_frame"], row["end_frame"] + 1):
            if frame_no in lookup:
                raise ValueError(f"overlapping dialogue frame {frame_no}")
            lookup[frame_no] = row
    return lookup, max(row["end_frame"] for row in rows)


def open_encoder(output: Path) -> subprocess.Popen:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "bgr24", "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", FPS, "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def make_contact_sheet(items: list[tuple[int, np.ndarray]], output: Path) -> None:
    tiles = []
    for index, frame in items:
        tile = np.zeros((294, WIDTH, 3), dtype=np.uint8)
        tile[22:] = frame
        cv2.putText(tile, f"dialogue #{index:02d}", (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(tile)
    cols = 2
    if len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    cv2.imwrite(str(output), np.vstack(rows))


def process_video(
    video: Path,
    rows: list[dict],
    output_dir: Path,
    name_font: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
) -> dict:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video}")
    lookup, _ = build_lookup(rows)
    preview_path = output_dir / f"{video.stem}-korean-preview.mp4"
    comparisons = output_dir / "comparisons" / video.stem
    representatives = output_dir / "representative_frames" / video.stem
    comparisons.mkdir(parents=True, exist_ok=True)
    representatives.mkdir(parents=True, exist_ok=True)
    for stale in (*comparisons.glob("*.png"), *representatives.glob("*.png")):
        stale.unlink()
    best_originals: dict[int, tuple[int, int, np.ndarray]] = {}
    brightness: dict[int, list[float]] = {int(row["index"]): [] for row in rows}
    frame_no = -1
    while True:
        ok, original = cap.read()
        if not ok:
            break
        frame_no += 1
        row = lookup.get(frame_no)
        if row is None:
            continue
        index = int(row["index"])
        x1, y1, x2, y2 = BODY_ROI
        body_gray = cv2.cvtColor(original[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        mean = float(body_gray.mean())
        brightness[index].append(mean)
        if mean < PANEL_MEAN_THRESHOLD:
            score = int((body_gray > 170).sum())
            if index not in best_originals or score > best_originals[index][0]:
                best_originals[index] = (score, frame_no, original.copy())
    cap.release()
    if len(best_originals) != len(rows):
        raise RuntimeError(f"missing stable representative frame: {sorted(set(range(1, len(rows) + 1)) - set(best_originals))}")
    masks = {
        index: (glyph_mask(item[2], NAME_ROI), glyph_mask(item[2], BODY_ROI))
        for index, item in best_originals.items()
    }
    ranges = {index: (min(values), max(values)) for index, values in brightness.items()}

    cap = cv2.VideoCapture(str(video))
    encoder = open_encoder(preview_path)
    changed_frames = 0
    frame_no = -1
    try:
        while True:
            ok, original = cap.read()
            if not ok:
                break
            frame_no += 1
            output = original
            row = lookup.get(frame_no)
            if row is not None:
                index = int(row["index"])
                x1, y1, x2, y2 = BODY_ROI
                body_gray = cv2.cvtColor(original[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
                name_mask, body_mask = masks[index]
                erased = erase_japanese(original, NAME_ROI, name_mask)
                erased = erase_japanese(erased, BODY_ROI, body_mask)
                korean = draw_korean(erased, row["speaker"], row["translation"], name_font, body_font)
                low, high = ranges[index]
                if high - low > 8.0:
                    alpha = float(np.clip((high - float(body_gray.mean())) / (high - low), 0.0, 1.0))
                else:
                    alpha = 1.0
                output = cv2.addWeighted(korean, alpha, erased, 1.0 - alpha, 0.0)
                changed_frames += 1
            assert encoder.stdin is not None
            encoder.stdin.write(output.tobytes())
    finally:
        cap.release()
        if encoder.stdin:
            encoder.stdin.close()
        return_code = encoder.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg encoder failed with exit code {return_code}")
    contact_items: list[tuple[int, np.ndarray]] = []
    for index in sorted(best_originals):
        _, representative, original = best_originals[index]
        row = rows[index - 1]
        name_mask, body_mask = masks[index]
        output = erase_japanese(original, NAME_ROI, name_mask)
        output = erase_japanese(output, BODY_ROI, body_mask)
        output = draw_korean(output, row["speaker"], row["translation"], name_font, body_font)
        cv2.imwrite(str(representatives / f"dialogue_{index:02d}_f{representative:04d}.png"), output)
        comparison = np.hstack((original, output))
        cv2.putText(comparison, "original", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(comparison, "korean", (WIDTH + 6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(comparisons / f"dialogue_{index:02d}_f{representative:04d}_comparison.png"), comparison)
        contact_items.append((index, output))
    contact_items.sort(key=lambda item: item[0])
    make_contact_sheet(contact_items, output_dir / f"{video.stem}-korean-contact-sheet.png")
    return {
        "input": str(video),
        "output": str(preview_path),
        "frame_count": frame_no + 1,
        "changed_frames": changed_frames,
        "unchanged_frames": frame_no + 1 - changed_frames,
        "timeline_frames": len(lookup),
        "fade_guard_frames": len(lookup) - changed_frames,
        "dialogue_count": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--video-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font", type=Path, default=Path(r"C:\Windows\Fonts\malgun.ttf"))
    args = parser.parse_args()

    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    name_font = load_font(args.font, 12)
    body_font = load_font(args.font, 15)
    reports = []
    for stem, rows in timeline["videos"].items():
        reports.append(process_video(args.video_dir / f"{stem}.pmf", rows, args.output, name_font, body_font))
    report = {
        "fps": FPS,
        "resolution": [WIDTH, HEIGHT],
        "font": str(args.font),
        "name_font_size": 12,
        "body_font_size": 15,
        "name_position": NAME_POS,
        "body_position": BODY_POS,
        "body_line_step": BODY_LINE_STEP,
        "panel_mean_threshold": PANEL_MEAN_THRESHOLD,
        "name_roi": NAME_ROI,
        "body_roi": BODY_ROI,
        "videos": reports,
    }
    (args.output / "compositing-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
