#!/usr/bin/env python3
"""User-facing SPECIAL VERSION patch profile backed by canonical assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

try:
    from tools.scripts.ys6_special_remaining_idm_preflight import preflight
except ModuleNotFoundError:
    from ys6_special_remaining_idm_preflight import preflight


PROFILE = "ULJM-05155"


class SpecialPatchBuilderError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def layout(tools_dir: Path | None = None) -> dict[str, Path]:
    root = (tools_dir or Path(__file__).resolve().parents[1]).resolve()
    patch = root / "patchdata" / "ys6_special_version"
    return {
        "tools": root,
        "special": patch,
        "build_config": patch / "build-config.json",
        "base_mapping": patch / "base-mapping-rev4.json",
        "mapping": patch / "hangul-mapping.json",
        "base_translations": patch / "base-translations.json",
        "remaining": patch / "remaining-translations.json",
        "cast_items": patch / "cast-item-translations.json",
        "system_messages": patch / "system-messages.json",
        "system_aliases": patch / "system-glyph-aliases.json",
        "runtime_map": patch / "runtime-map.json",
        "seed_boot": patch / "seed-boot.bin",
        "seed_eboot": patch / "seed-eboot.bin",
        "work": root / "patchdata" / "work" / "current" / "117-ys6-special-version-system-message-speaker-port",
    }


def find_default_font() -> Path | None:
    candidates = [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/malgunbd.ttf")]
    return next((path for path in candidates if path.exists()), None)


def inspect_inputs(tools_dir: Path | None = None) -> dict:
    paths = layout(tools_dir)
    missing = [str(path) for key, path in paths.items() if key not in ("tools", "work") and not path.exists()]
    if missing:
        raise SpecialPatchBuilderError("SPECIAL VERSION 필수 파일 없음: " + ", ".join(missing))
    config = json.loads(paths["build_config"].read_text(encoding="utf-8-sig"))
    for name, expected in config["assets"].items():
        actual = sha256_file(paths["special"] / name)
        if actual != expected:
            raise SpecialPatchBuilderError(f"SPECIAL VERSION 패치 데이터 SHA-256 불일치: {name}")
    mapping = json.loads(paths["mapping"].read_text(encoding="utf-8-sig"))
    remaining = json.loads(paths["remaining"].read_text(encoding="utf-8-sig"))
    if int(mapping.get("mapping_revision", 0)) != 7 or len(mapping["mappings"]) != 975:
        raise SpecialPatchBuilderError("SPECIAL VERSION revision 7 매핑 불일치")
    for key in ("character", "game_code", "font_index"):
        values = [row[key] for row in mapping["mappings"]]
        if len(values) != len(set(values)):
            raise SpecialPatchBuilderError(f"SPECIAL VERSION 매핑 중복: {key}")
    counts = remaining.get("summary", {}).get("status_counts", {})
    if counts != {"translated": 293, "reused": 534}:
        raise SpecialPatchBuilderError(f"SPECIAL VERSION 번역 상태 개수 불일치: {counts}")
    cast_items = json.loads(paths["cast_items"].read_text(encoding="utf-8-sig"))
    if cast_items.get("summary") != {"cast_apply_count": 70, "item_apply_count": 72,
                                     "item_excluded_count": 5}:
        raise SpecialPatchBuilderError("SPECIAL VERSION 인물·아이템 적용 목록 불일치")
    system_messages = json.loads(paths["system_messages"].read_text(encoding="utf-8-sig"))
    system_summary = system_messages.get("summary", {})
    if system_summary.get("extracted_count") != 332 or system_summary.get("override_count") != 138:
        raise SpecialPatchBuilderError("SPECIAL VERSION 시스템 메시지 작업공간 불일치")
    return {
        "profile": PROFILE,
        "profile_name": "SPECIAL VERSION",
        "default_output_name": config["default_output_name"],
        "dialogue_records": 827,
        "override_count": 6156,
        "draft_count": 0,
        "cast_reviewed_count": 70,
        "cast_person_reviewed_count": sum(row["identifier"].startswith("CAST_C") for row in cast_items["cast"]),
        "monster_reviewed_count": sum(row["identifier"].startswith("CAST_M") for row in cast_items["cast"]),
        "item_override_count": 72,
        "item_draft_count": 0,
        "item_excluded_count": 5,
        "system_message_count": 332,
        "system_override_count": 138,
        "system_draft_count": int(system_summary.get("blocked_count", 0)),
        "option_menu_image_count": 0,
        "option_menu_images_enabled": False,
        "additional_image_count": 0,
        "additional_images_enabled": False,
        "ending_movie_count": 0,
        "ending_movies_enabled": False,
        "xmb_image_count": 0,
        "xmb_image_enabled": False,
        "analog_stick_patch_enabled": False,
        "hangul_mapping_count": len(mapping["mappings"]),
        "hangul_mapping_revision": int(mapping["mapping_revision"]),
        "hangul_mapping_sha256": sha256_file(paths["mapping"]),
        "hangul_mapping_missing_count": 0,
        "hangul_mapping_missing_characters": [],
        "font": str(find_default_font() or ""),
        "unsupported_options": ["option_menu_images", "additional_images", "ending_movies", "xmb_image", "analog_stick"],
        "paths": paths,
        "config": config,
    }


def run_build(mode: str, iso: Path, output: Path | None = None, font: Path | None = None,
              tools_dir: Path | None = None, overwrite: bool = False) -> dict:
    info = inspect_inputs(tools_dir)
    if not iso.exists():
        raise SpecialPatchBuilderError(f"SPECIAL VERSION 원본 ISO를 찾을 수 없습니다: {iso}")
    if sha256_file(iso) != info["config"]["original_iso_sha256"]:
        raise SpecialPatchBuilderError("지원하는 SPECIAL VERSION 원본 ISO의 SHA-256이 아닙니다")
    font = font or find_default_font()
    if font is None or not font.exists():
        raise SpecialPatchBuilderError("맑은 고딕 TTF 폰트를 찾을 수 없습니다")
    if mode == "build":
        if output is None:
            raise SpecialPatchBuilderError("출력 ISO 경로가 필요합니다")
        if iso.resolve() == output.resolve():
            raise SpecialPatchBuilderError("원본 ISO와 출력 ISO 경로가 같습니다")
        if output.exists() and not overwrite:
            raise SpecialPatchBuilderError(f"출력 ISO가 이미 존재합니다: {output}")
    paths = info["paths"]
    args = SimpleNamespace(
        iso=iso,
        mapping=paths["mapping"],
        base_translations=paths["base_translations"],
        remaining=paths["remaining"],
        cast_item_workspace=paths["cast_items"],
        system_messages=paths["system_messages"],
        system_aliases=paths["system_aliases"],
        runtime_map=paths["runtime_map"],
        seed_boot=paths["seed_boot"],
        seed_eboot=paths["seed_eboot"],
        work=paths["work"],
        font=font,
        output=output if mode == "build" else None,
        overwrite=overwrite,
    )
    report = preflight(args)
    summary = {
        "valid": report["valid"],
        "profile": PROFILE,
        "profile_name": "SPECIAL VERSION",
        "translation_count": report["total_translation_count"],
        "idm_resource_count": report["idm_resource_count"],
        "runtime_copy_count": report["runtime_copy_count"],
        "mapping_revision": report["mapping_revision"],
        "mapping_count": report["mapping_count"],
        "font_table_count": report["font_table_count"],
        "overflow_count": report["overflow_count"],
        "s4010_free_bytes": report["s4010"]["standalone_free_bytes"],
        "cast_apply_count": report["cast_items"]["cast_apply_count"],
        "item_apply_count": report["cast_items"]["item_apply_count"],
        "item_excluded_count": report["cast_items"]["item_excluded_count"],
        "system_message_count": report["system_messages"]["record_count"],
        "system_override_count": report["system_messages"]["override_count"],
        "unsupported_options": info["unsupported_options"],
    }
    result = {"summary": summary, "profile": PROFILE, "report": report, "iso": None}
    if mode == "build":
        result["iso"] = {
            "path": str(output),
            "output_iso_sha256": report["output_iso_sha256"],
            "size": report["output_iso_size"],
        }
    return result
