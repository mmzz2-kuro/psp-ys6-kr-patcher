#!/usr/bin/env python3
"""User-facing Ys VI patch builder using tools/config and tools/patchdata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

try:
    from tools.scripts.ys6_integrated_build import execute
    from tools.scripts.ys6_translation_workspace import validate as validate_dialogue
    from tools.scripts.ys6_cast_name_workspace import validate_workspace as validate_cast
    from tools.scripts.ys6_item_workspace import validate_workspace as validate_items
    from tools.scripts.ys6_system_message_workspace import validate_workspace as validate_system_messages
except ModuleNotFoundError:
    try:
        from .ys6_integrated_build import execute
        from .ys6_translation_workspace import validate as validate_dialogue
        from .ys6_cast_name_workspace import validate_workspace as validate_cast
        from .ys6_item_workspace import validate_workspace as validate_items
        from .ys6_system_message_workspace import validate_workspace as validate_system_messages
    except ImportError:
        from ys6_integrated_build import execute
        from ys6_translation_workspace import validate as validate_dialogue
        from ys6_cast_name_workspace import validate_workspace as validate_cast
        from ys6_item_workspace import validate_workspace as validate_items
        from ys6_system_message_workspace import validate_workspace as validate_system_messages


class PatchBuilderError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest().upper()


def layout(tools_dir: Path | None = None) -> dict[str, Path]:
    root = (tools_dir or Path(__file__).resolve().parents[1]).resolve()
    config, patch = root / "config", root / "patchdata"
    return {
        "tools": root, "dialogue": config / "dialogue-translations.json",
        "cast": config / "cast-names.json", "catalog": config / "dialogue-catalog.json",
        "items": config / "item-translations.json",
        "system_messages": config / "system-messages.json",
        "build_config": patch / "build-config.json", "runtime_map": patch / "runtime-archive-map.json",
        "font_usage": patch / "font-usage.json", "seed_mapping": patch / "seed-mapping.json",
        "original_eboot": patch / "original-eboot.bin", "han_override": patch / "hangul-98fc-manual.txt",
        "standalone_paths": patch / "standalone-paths.json", "work": patch / "work" / "current",
        "option_menu": patch / "ys6_option_menu",
        "option_menu_source": patch / "ys6_option_menu" / "original-static_tex.dds",
        "option_menu_manifest": patch / "ys6_option_menu" / "manifest.json",
        "option_menu_edited": patch / "ys6_option_menu" / "edited_buttons",
        "additional_images": patch / "ys6_additional_images",
        "additional_images_edited": patch / "ys6_additional_images" / "edited_parts",
        "ending_movies": patch / "ys6_ending_movies",
        "ending_movies_manifest": patch / "ys6_ending_movies" / "manifest.json",
        "xmb": patch / "ys6_xmb",
        "xmb_manifest": patch / "ys6_xmb" / "manifest.json",
    }


def find_default_font() -> Path | None:
    candidates = [Path("C:/Windows/Fonts/gulim.ttc"), Path("C:/Windows/Fonts/gulim.ttf")]
    return next((path for path in candidates if path.exists()), None)


def inspect_inputs(tools_dir: Path | None = None, *, include_option_menu_images: bool = True,
                   include_additional_images: bool = True,
                   include_ending_movies: bool = True,
                   include_xmb_image: bool = True) -> dict:
    paths = layout(tools_dir)
    excluded = {"tools", "work", "option_menu_edited", "additional_images_edited"}
    if not include_option_menu_images:
        excluded.update({"option_menu", "option_menu_source", "option_menu_manifest"})
    if not include_additional_images:
        excluded.add("additional_images")
    if not include_ending_movies:
        excluded.update({"ending_movies", "ending_movies_manifest"})
    if not include_xmb_image:
        excluded.update({"xmb", "xmb_manifest"})
    required = [value for key, value in paths.items() if key not in excluded]
    missing = [str(path) for path in required if not path.exists()]
    if missing: raise PatchBuilderError("필수 파일 없음: " + ", ".join(missing))
    config = json.loads(paths["build_config"].read_text(encoding="utf-8-sig"))
    for name, expected in config["assets"].items():
        path = paths["build_config"].parent / name
        actual = sha256_file(path)
        if actual != expected: raise PatchBuilderError(f"패치 데이터 SHA-256 불일치: {name}")
    dialogue = json.loads(paths["dialogue"].read_text(encoding="utf-8-sig"))
    cast = json.loads(paths["cast"].read_text(encoding="utf-8-sig"))
    items = json.loads(paths["items"].read_text(encoding="utf-8-sig"))
    system_messages = json.loads(paths["system_messages"].read_text(encoding="utf-8-sig"))
    dialogue_report = validate_dialogue(dialogue)
    cast_errors = validate_cast(cast)
    item_errors = validate_items(items)
    system_errors = validate_system_messages(system_messages)
    if not dialogue_report["valid"]: raise PatchBuilderError("대사 작업공간 오류: " + "; ".join(dialogue_report["errors"]))
    if cast_errors: raise PatchBuilderError("인물명 작업공간 오류: " + "; ".join(cast_errors))
    if item_errors: raise PatchBuilderError("아이템 작업공간 오류: " + "; ".join(item_errors))
    if system_errors: raise PatchBuilderError("시스템 메시지 작업공간 오류: " + "; ".join(system_errors))
    option_files = (sorted(paths["option_menu_edited"].glob("*.png"))
                    if include_option_menu_images and paths["option_menu_edited"].exists() else [])
    additional_files = (sorted(paths["additional_images_edited"].rglob("*.png"))
                        if include_additional_images and paths["additional_images_edited"].exists() else [])
    ending_manifest = (json.loads(paths["ending_movies_manifest"].read_text(encoding="utf-8-sig"))
                       if include_ending_movies else {"movies": []})
    for movie in ending_manifest["movies"]:
        movie_path = paths["ending_movies"] / movie["file"]
        if not movie_path.exists(): raise PatchBuilderError(f"엔딩 영상 파일 없음: {movie_path}")
        if sha256_file(movie_path) != movie["output_sha256"]: raise PatchBuilderError(f"엔딩 영상 SHA-256 불일치: {movie['file']}")
    xmb_manifest = (json.loads(paths["xmb_manifest"].read_text(encoding="utf-8-sig"))
                    if include_xmb_image else {"assets": []})
    for asset in xmb_manifest["assets"]:
        asset_path = paths["xmb"] / asset["file"]
        if not asset_path.exists(): raise PatchBuilderError(f"XMB 이미지 파일 없음: {asset_path}")
        if sha256_file(asset_path) != asset["output_sha256"]: raise PatchBuilderError(f"XMB 이미지 SHA-256 불일치: {asset['file']}")
    return {
        "dialogue_records": len(dialogue["records"]),
        "override_count": sum(row.get("status") == "override" for row in dialogue["records"]),
        "draft_count": sum(row.get("status") == "draft" for row in dialogue["records"]),
        "cast_reviewed_count": sum(row.get("status") == "reviewed" for row in cast["records"]),
        "cast_person_reviewed_count": sum(row.get("status") == "reviewed" and not row.get("identifier", "").startswith("CAST_M") for row in cast["records"]),
        "monster_reviewed_count": sum(row.get("status") == "reviewed" and row.get("identifier", "").startswith("CAST_M") for row in cast["records"]),
        "item_override_count": sum(row.get("status") == "override" for row in items["records"]),
        "item_draft_count": sum(row.get("status") == "draft" for row in items["records"]),
        "system_message_count": len(system_messages["records"]),
        "system_override_count": sum(row.get("status") == "override" for row in system_messages["records"]),
        "system_draft_count": sum(row.get("status") == "draft" for row in system_messages["records"]),
        "option_menu_image_count": len(option_files),
        "option_menu_image_files": [path.name for path in option_files],
        "option_menu_images_enabled": include_option_menu_images,
        "additional_image_count": len(additional_files),
        "additional_image_files": [str(path.relative_to(paths["additional_images_edited"])).replace("\\", "/") for path in additional_files],
        "additional_images_enabled": include_additional_images,
        "ending_movie_count": len(ending_manifest["movies"]),
        "ending_movies_enabled": include_ending_movies,
        "xmb_image_count": len(xmb_manifest["assets"]),
        "xmb_image_enabled": include_xmb_image,
        "font": str(find_default_font() or ""), "paths": paths, "config": config,
    }


def run_build(mode: str, iso: Path, output: Path | None = None, font: Path | None = None,
              tools_dir: Path | None = None, overwrite: bool = False,
              include_option_menu_images: bool = True,
              include_additional_images: bool = True,
              include_ending_movies: bool = True,
              include_xmb_image: bool = True) -> dict:
    info = inspect_inputs(
        tools_dir,
        include_option_menu_images=include_option_menu_images,
        include_additional_images=include_additional_images,
        include_ending_movies=include_ending_movies,
        include_xmb_image=include_xmb_image,
    ); paths, config = info["paths"], info["config"]
    font = font or find_default_font()
    if font is None or not font.exists(): raise PatchBuilderError("굴림 TTC/TTF 폰트를 찾을 수 없습니다")
    if not iso.exists(): raise PatchBuilderError(f"원본 ISO를 찾을 수 없습니다: {iso}")
    if sha256_file(iso) != config["original_iso_sha256"]: raise PatchBuilderError("지원하는 원본 ISO의 SHA-256이 아닙니다")
    if mode == "build":
        if output is None: raise PatchBuilderError("출력 ISO 경로가 필요합니다")
        if iso.resolve() == output.resolve(): raise PatchBuilderError("원본 ISO와 출력 ISO 경로가 같습니다")
        if output.exists() and not overwrite: raise PatchBuilderError(f"출력 ISO가 이미 존재합니다: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
    args = SimpleNamespace(
        mode=mode, iso=iso, workspace=paths["dialogue"], cast_name_workspace=paths["cast"],
        item_workspace=paths["items"],
        system_message_workspace=paths["system_messages"],
        catalog=paths["catalog"], runtime_map=paths["runtime_map"], font_usage=paths["font_usage"],
        seed_mapping=paths["seed_mapping"], original_eboot=paths["original_eboot"], font=font,
        han_override=paths["han_override"], horizontal_left_inset=int(config["horizontal_left_inset"]),
        castinfo_name=None, castinfo_identifier="CAST_C240", castinfo_expected_name="イーシャ",
        work=paths["work"], standalone_path=json.loads(paths["standalone_paths"].read_text(encoding="utf-8-sig")),
        option_menu_workspace=paths["option_menu"] if include_option_menu_images else None,
        option_menu_source=paths["option_menu_source"] if include_option_menu_images else None,
        additional_image_workspace=paths["additional_images"] if include_additional_images else None,
        ending_movie_workspace=paths["ending_movies"] if include_ending_movies else None,
        xmb_workspace=paths["xmb"] if include_xmb_image else None,
        output_iso=output, overwrite=overwrite,
    )
    return execute(args)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "preflight", "build")); parser.add_argument("--iso", type=Path)
    parser.add_argument("--output", type=Path); parser.add_argument("--font", type=Path); parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-option-menu-images", action="store_true")
    parser.add_argument("--no-additional-images", action="store_true")
    parser.add_argument("--no-ending-movies", action="store_true")
    parser.add_argument("--no-xmb-image", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.mode == "inspect":
            result = inspect_inputs(
                include_option_menu_images=not args.no_option_menu_images,
                include_additional_images=not args.no_additional_images,
                include_ending_movies=not args.no_ending_movies,
                include_xmb_image=not args.no_xmb_image,
            ); result = {key:value for key,value in result.items() if key not in {"paths", "config"}}
        else:
            if args.iso is None: parser.error(f"{args.mode} requires --iso")
            result = run_build(
                args.mode, args.iso, args.output, args.font, overwrite=args.overwrite,
                include_option_menu_images=not args.no_option_menu_images,
                include_additional_images=not args.no_additional_images,
                include_ending_movies=not args.no_ending_movies,
                include_xmb_image=not args.no_xmb_image,
            )
        print(json.dumps(result.get("summary", result), ensure_ascii=False, indent=2)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, PatchBuilderError) as exc:
        print(f"패치 빌드 실패: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
