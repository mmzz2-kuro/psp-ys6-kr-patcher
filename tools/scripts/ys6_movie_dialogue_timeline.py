#!/usr/bin/env python3
"""Extract review sheets and frame-exact dialogue timelines from Ys VI PMFs."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


FPS_NUM = 30000
FPS_DEN = 1001
FPS = FPS_NUM / FPS_DEN
PTS_START_SECONDS = 1.0


@dataclass(frozen=True)
class Dialogue:
    start_frame: int
    end_frame: int
    speaker: str
    source_text: str
    translation: str = ""
    match_status: str = "unmatched"
    match_reference: str = ""


# Inclusive frame ranges. Filled after reviewing the generated 0.5-second sheets.
TIMELINES: dict[str, list[Dialogue]] = {
    "im03a_kaizoku": [
        Dialogue(1686, 1750, "라바", "おお……\n《ナピシュテムの匣》が！", "오오……\\n'나피쉬팀의 상자'가!", "normalized_newline", "892B678C73CB9545CB1D0644635BD5D49C185187E5F0620A7EE668A43C4125DA"),
        Dialogue(1751, 1817, "라독선장", "やばいな……\n近づきすぎると巻き込まれるぞ。", "위험해……\\n너무 가까이 가면 휘말릴 거야.", "normalized_newline", "9F56A5856885671CA63C5FE75D9685D98662FE87CBFCFD71C0E8A819537E544E"),
        Dialogue(1818, 1875, "도기", "おい、黒髪の小僧！", "어이, 검은 머리 애송이!", "exact", "32FCD59B34237FCB83C034CFA9F1AFE313F281B4B48D68E71796D9985851D7CD"),
        Dialogue(1876, 1942, "도기", "あの中にアドルが\nいるってのは本当なのかよ！？", "저 안에 아돌이\\n있다는 게 정말이야!?", "variable_expanded", "ED96C15ABE476613F50DCFE2E9816E7D63BA8E0FD2DBB6A7B799EB18B9E35505"),
        Dialogue(1962, 2010, "가슈", "ああ……本当だ……", "그래…… 사실이야……", "exact", "12664FBDB17B69DA2A96E49A697BDFC4824CFB5FC308AA0623AB0453CB502FCE"),
        Dialogue(2011, 2070, "가슈", "すまねえ、俺が頼んだせいで……", "미안하다. 내가 부탁하는 바람에……", "exact", "8BBA390A8B7F2D948E878EA5F86D84C2B03F788A2B6D41CA9CF3332F8BD7E427"),
        Dialogue(2071, 2130, "테라", "そ、そんな……\nそんなのってないよっ！", "그, 그럴 수가……\\n이건 너무하잖아!", "normalized_newline", "5336F9C0204503C0C21839B98DFA2E2BFEE2B5CF73D2A6B910CADA9F7E269A9D"),
        Dialogue(2131, 2190, "테라", "どうしていつも\nアドルばっかり危険な目に……", "왜 언제나\\n아돌만 위험한 일을 겪는 거야……", "variable_expanded", "8221267675D72A67BF97D9D9DFA6A9172FAEF9391BF4F56CF4783D6EFC1D6CCD"),
        Dialogue(2191, 2257, "이샤", "…………………………………", "…………………………………", "exact", "87203F61DF69B5EEC8E00B65671DF1FC19CD5D7EB1F6C5BDD4DCF17C0138582A"),
        Dialogue(2307, 2372, "이샤", "…………あ……………………", "…………아……………………", "exact", "E43070D4398B5CF8C5E0CA1D48C4D3768B6237F741A627336478B2C7D30070A8"),
    ],
    "im03b_kazaminooka": [
        Dialogue(1795, 1864, "울", "うっわー！\nなにあれ、すごい綺麗じゃん！", "우와!\\n저게 뭐야? 정말 예쁘잖아!", "normalized_newline", "C6BB9535D1B4C450AB725A5808D3BBDB1330009EC174F77BAAA03C9ABC0AD67C"),
        Dialogue(1865, 1914, "오드족장", "おお……何たることだ……", "오오…… 이게 무슨 일인가……", "exact", "B51C605BDA4659AEFD898B76F8D2B0F0A42958BA895B0F0038E332F54AB3C0E7"),
        Dialogue(1915, 2004, "오드족장", "オルハよ、あの翼はもしや……", "오르하, 저 날개는 혹시……", "exact", "87AB5665C113CC76774A5C689679D3939C43DEC51BDDB99E1DE2D1F2D31798CE"),
        Dialogue(2005, 2084, "오르하", "…………はい…………………", "…………네…………………", "exact", "C9EB1DA85DFD22F2E81E5E95077685399D80F37D3E1B0F5D76653D318146C5FA"),
        Dialogue(2085, 2191, "오르하", "アルマと……\n……母さまたちです……………", "알마와……\\n……어머니들이에요……………", "normalized_newline", "7FD2F5872EF0FA04CD96BF85F1AE928A0D5E6EE057F5614FF687A804511B1152"),
    ],
}


def timestamp(frame: int) -> str:
    millis = round(frame * FPS_DEN * 1000 / FPS_NUM)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def read_frame(cap: cv2.VideoCapture, frame_no: int) -> np.ndarray:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"cannot decode frame {frame_no}")
    return frame


def make_review_sheets(video: Path, out_dir: Path, start: float, end: float) -> None:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    first = max(0, round(start * FPS))
    last = min(total - 1, round(end * FPS))
    step = round(0.5 * FPS)
    tiles: list[np.ndarray] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(range(first, last + 1, step))
    frame_no = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_no += 1
        if frame_no < first or frame_no not in wanted:
            if frame_no >= last:
                break
            continue
        cv2.rectangle(frame, (0, 0), (230, 24), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"f={frame_no:04d}  {timestamp(frame_no)}",
            (6, 17),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        tiles.append(frame.copy())
        if frame_no >= last:
            break
    cap.release()

    cols, rows_per_sheet = 3, 4
    per_sheet = cols * rows_per_sheet
    for sheet_no, offset in enumerate(range(0, len(tiles), per_sheet), 1):
        group = tiles[offset : offset + per_sheet]
        blank = np.zeros_like(group[0])
        group.extend([blank] * (per_sheet - len(group)))
        rows = [np.hstack(group[i : i + cols]) for i in range(0, per_sheet, cols)]
        cv2.imwrite(str(out_dir / f"{video.stem}-review-500ms-{sheet_no:02d}.png"), np.vstack(rows))


def export_timeline(video: Path, out_dir: Path, dialogues: list[Dialogue]) -> None:
    cap = cv2.VideoCapture(str(video))
    records = []
    contact_tiles: list[np.ndarray] = []
    frame_dir = out_dir / "representative_frames" / video.stem
    crop_dir = out_dir / "dialogue_crops" / video.stem
    frame_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)
    for stale in (*frame_dir.glob("dialogue_*.png"), *crop_dir.glob("dialogue_*.png")):
        stale.unlink()
    best: dict[int, tuple[int, int, np.ndarray]] = {}
    frame_no = -1
    final_frame = max(item.end_frame for item in dialogues)
    while frame_no < final_frame:
        ok, frame = cap.read()
        if not ok:
            break
        frame_no += 1
        for index, item in enumerate(dialogues, 1):
            if item.start_frame <= frame_no <= item.end_frame:
                gray = cv2.cvtColor(frame[190:245, 110:410], cv2.COLOR_BGR2GRAY)
                score = int((gray > 170).sum())
                if index not in best or score > best[index][0]:
                    best[index] = (score, frame_no, frame.copy())
                break
    if len(best) != len(dialogues):
        raise RuntimeError("could not decode every dialogue range")
    for index, item in enumerate(dialogues, 1):
        _, representative, frame = best[index]
        frame_name = f"dialogue_{index:02d}_f{representative:04d}.png"
        crop_name = f"dialogue_{index:02d}_f{representative:04d}_crop.png"
        cv2.imwrite(str(frame_dir / frame_name), frame)
        crop = frame[176:272, 0:480]
        cv2.imwrite(str(crop_dir / crop_name), crop)
        tile = np.zeros((118, 480, 3), dtype=np.uint8)
        tile[22:118] = crop
        cv2.putText(tile, f"#{index:02d}  f={item.start_frame}-{item.end_frame}  {timestamp(item.start_frame)}", (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (255, 255, 255), 1, cv2.LINE_AA)
        contact_tiles.append(tile)
        row = asdict(item)
        row.update(
            {
                "index": index,
                "start_time": timestamp(item.start_frame),
                "end_time": timestamp(item.end_frame),
                "start_pts_seconds": round(PTS_START_SECONDS + item.start_frame / FPS, 6),
                "end_pts_seconds": round(PTS_START_SECONDS + item.end_frame / FPS, 6),
                "duration_seconds": round((item.end_frame - item.start_frame + 1) / FPS, 6),
                "representative_frame": str((frame_dir / frame_name).relative_to(out_dir)),
                "dialogue_crop": str((crop_dir / crop_name).relative_to(out_dir)),
            }
        )
        records.append(row)
    cap.release()

    fields = [
        "index", "start_frame", "end_frame", "start_time", "end_time",
        "start_pts_seconds", "end_pts_seconds",
        "duration_seconds", "speaker", "source_text", "translation",
        "match_status", "match_reference", "representative_frame", "dialogue_crop",
    ]
    with (out_dir / f"{video.stem}-dialogues.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    cols = 2
    if len(contact_tiles) % cols:
        contact_tiles.append(np.zeros_like(contact_tiles[0]))
    rows = [np.hstack(contact_tiles[i:i + cols]) for i in range(0, len(contact_tiles), cols)]
    cv2.imwrite(str(out_dir / f"{video.stem}-dialogue-contact-sheet.png"), np.vstack(rows))
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--review-start", type=float, default=50.0)
    parser.add_argument("--review-end", type=float, default=82.0)
    parser.add_argument("--review-only", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    combined = {}
    for video in args.videos:
        make_review_sheets(video, args.output / "review_sheets", args.review_start, args.review_end)
        if not args.review_only:
            combined[video.stem] = export_timeline(video, args.output, TIMELINES.get(video.stem, []))
    if not args.review_only:
        with (args.output / "dialogue-timeline.json").open("w", encoding="utf-8") as fp:
            json.dump(
                {"fps": "30000/1001", "pts_start_seconds": PTS_START_SECONDS, "videos": combined},
                fp,
                ensure_ascii=False,
                indent=2,
            )


if __name__ == "__main__":
    main()
