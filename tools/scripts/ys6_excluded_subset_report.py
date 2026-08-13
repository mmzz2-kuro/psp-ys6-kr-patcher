#!/usr/bin/env python3
"""Report Ys VI overrides excluded from a safe buildable subset."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def key(row: dict) -> tuple[str, int]:
    return row["iso_path"], int(row["string_index"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--runtime-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--expected", type=int)
    args = parser.parse_args()

    full = load(args.full)
    subset = load(args.subset)
    catalog = load(args.catalog)
    runtime_map = load(args.runtime_map)
    subset_keys = {key(row) for row in subset["records"] if row.get("status") == "override"}
    file_hash = {row["iso_path"]: row["xso_sha256"] for row in catalog["files"]}
    mapping = {row["xso_sha256"]: row for row in runtime_map["mappings"]}
    full_rows = [row for row in full["records"] if row.get("status") == "override"]
    excluded = [row for row in full_rows if key(row) not in subset_keys]
    if args.expected is not None and len(excluded) != args.expected:
        raise ValueError(f"excluded count mismatch: expected={args.expected}, actual={len(excluded)}")

    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in full_rows:
        grouped[(file_hash[row["iso_path"]], int(row["string_index"]))].append(row)

    reasons = Counter()
    records = []
    for row in excluded:
        digest = file_hash[row["iso_path"]]
        map_row = mapping.get(digest, {})
        shared = grouped[(digest, int(row["string_index"]))]
        if map_row.get("status") == "many_to_many":
            reason = "many_to_many"
        elif len({item["translation"] for item in shared}) > 1:
            reason = "shared_payload_translation_conflict"
        else:
            reason = map_row.get("status", "unknown")
        reasons[reason] += 1
        records.append({
            "reason": reason,
            "iso_path": row["iso_path"],
            "map_group": row.get("map_group", ""),
            "map_id": row.get("map_id", ""),
            "xso_name": row.get("xso_name", ""),
            "string_index": int(row["string_index"]),
            "source_text": row["source_text"],
            "translation": row["translation"],
            "xso_sha256": digest,
            "mapping_status": map_row.get("status"),
            "standalone_paths": map_row.get("standalone_paths", []),
            "runtime_keys": map_row.get("runtime_keys", []),
            "shared_candidates": [
                {"iso_path": item["iso_path"], "translation": item["translation"]}
                for item in shared
            ],
        })
    records.sort(key=lambda row: (row["reason"], row["xso_sha256"], row["string_index"], row["iso_path"]))
    report = {
        "schema_version": 1,
        "full_override_count": len(full_rows),
        "subset_override_count": len(subset_keys),
        "excluded_count": len(records),
        "reason_counts": dict(reasons),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        lines = [
            "# 042. 안전 부분집합 테스트 ISO 제외 대사 166개", "",
            "## 개요", "",
            f"- 전체 임시 override: {len(full_rows):,}개",
            f"- 테스트 ISO 반영: {len(subset_keys):,}개",
            f"- 제외: {len(records):,}개",
            f"- many-to-many 런타임 매핑: {reasons['many_to_many']}개",
            f"- 공유 payload 번역 충돌: {reasons['shared_payload_translation_conflict']}개", "",
            "이 제외는 테스트 ISO에만 적용된다. `/tools/config/dialogue-translations.json`의 번역과 draft 상태는 삭제하거나 변경하지 않았다.", "",
            "## 검토 방법", "",
            "- `many_to_many`: 동일 XSO가 여러 독립 경로와 여러 런타임 아카이브에 연결되어 현재 빌더가 패치 대상을 일대일로 결정하지 못한다.",
            "- `shared_payload_translation_conflict`: 실제로 같은 XSO payload의 같은 인덱스를 여러 맵이 공유하지만 번역 후보가 서로 다르다.",
            "- 아래 표의 `후보 수`가 2 이상이면 JSON 보고서의 `shared_candidates`에서 경로별 번역 전체를 확인할 수 있다.", "",
        ]
        for reason, title in (("many_to_many", "many-to-many 런타임 매핑 28개"), ("shared_payload_translation_conflict", "공유 payload 번역 충돌 138개")):
            lines.extend([f"## {title}", "", "| 번호 | 맵/XSO | 인덱스 | 원문 | 현재 번역 | 후보 수 | XSO SHA-256 |", "|---:|---|---:|---|---|---:|---|"])
            reason_rows = [row for row in records if row["reason"] == reason]
            for number, row in enumerate(reason_rows, 1):
                def cell(value: str) -> str:
                    return value.replace("|", "\\|").replace("\\n", "<br>").replace("\n", "<br>")
                short_path = row["iso_path"].removeprefix("PSP_GAME/USRDIR/data/map/")
                candidate_count = len({item["translation"] for item in row["shared_candidates"]})
                lines.append(f"| {number} | `{short_path}` | {row['string_index']} | {cell(row['source_text'])} | {cell(row['translation'])} | {candidate_count} | `{row['xso_sha256']}` |")
            lines.append("")
        lines.extend([
            "## 후속 해결 방향", "",
            "1. `many_to_many`는 동일 번역 결과를 연결된 모든 독립 경로와 런타임 아카이브에 쓰도록 빌더를 확장한다.",
            "2. 공유 payload 충돌은 후보를 비교해 공통 번역 하나로 통일하거나 런타임 경로별 payload 분리 가능성을 조사한다.",
            "3. 해결 후 전체 4,628개 임시 override로 preflight를 다시 실행한다.", "",
            "## 기계 판독 보고서", "",
            "전체 경로, 런타임 키와 경로별 번역 후보는 `/.work/ys6-safe-subset-test/excluded-166.json`에 보존했다.", "",
        ])
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("full_override_count", "subset_override_count", "excluded_count", "reason_counts")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
