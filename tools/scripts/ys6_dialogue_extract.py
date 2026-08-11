#!/usr/bin/env python3
"""Build searchable dialogue catalogs from extracted Ys VI PSP .xso.z files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from tools.scripts.ys6_xso import ParsedXso, parse_xso
    from tools.scripts.ys6_z import inspect_container
except ModuleNotFoundError:
    from ys6_xso import ParsedXso, parse_xso
    from ys6_z import inspect_container


ROLE_RULES = {
    ("100502", 4, 3): "dialogue",
    ("100502", 4, 2): "speaker",
    ("500502", 2, 0): "choice",
    ("500502", 2, 1): "choice_symbol",
    ("900602", 1, 0): "choice_prompt",
    ("800302", 2, 0): "script_path",
    ("F00402", 1, 0): "resource_name",
    ("900302", 1, 0): "resource_name",
    ("A01002", 1, 0): "event_symbol",
    ("100602", 1, 0): "resource_name",
}


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def path_context(path: Path, root: Path) -> dict[str, str]:
    relative = path.relative_to(root)
    parts = list(relative.parts)
    lowered = [part.lower() for part in parts]
    if "psp_game" in lowered:
        iso_path = "/".join(parts)
    else:
        iso_path = "PSP_GAME/USRDIR/data/map/" + "/".join(parts)
    filename = path.name[:-2] if path.name.lower().endswith(".z") else path.name
    stem = filename[:-4] if filename.lower().endswith(".xso") else Path(filename).stem
    map_parts = [part for part in parts if part.lower().startswith("s_")]
    return {
        "iso_path": iso_path.replace("\\", "/"),
        "map_group": map_parts[-2] if len(map_parts) >= 2 else (map_parts[0] if map_parts else ""),
        "map_id": map_parts[-1] if map_parts else "",
        "xso_name": stem,
    }


def classify_strings(parsed: ParsedXso) -> list[dict]:
    confirmed: dict[int, list[dict]] = {entry.index: [] for entry in parsed.strings}
    possible: dict[int, list[dict]] = {entry.index: [] for entry in parsed.strings}
    for command in parsed.commands:
        for argument_index, value in enumerate(command.arguments):
            if value >= parsed.info.string_count:
                continue
            reference = {
                "opcode": command.opcode,
                "argument_index": argument_index,
                "command_index": command.index,
                "command_offset": command.file_offset,
            }
            role = ROLE_RULES.get((command.opcode, command.argument_count, argument_index))
            if role:
                reference["role"] = role
                confirmed[value].append(reference)
            else:
                possible[value].append(reference)

    records = []
    for entry in parsed.strings:
        roles = sorted({reference["role"] for reference in confirmed[entry.index]})
        if not roles:
            roles = ["unreferenced"]
        records.append(
            {
                "string_index": entry.index,
                "relative_offset": entry.relative_offset,
                "file_offset": entry.file_offset,
                "byte_length": entry.byte_length,
                "raw_hex": entry.raw_hex,
                "text": entry.text,
                "roles": roles,
                "references": confirmed[entry.index],
                "possible_references": possible[entry.index],
                "tokens": entry.tokens,
                "markup": entry.markup,
                "is_empty": entry.text == "",
                "is_ascii": entry.text.isascii(),
            }
        )
    return records


def build_catalog(compressed_root: Path, decompressed_root: Path, overwrite: bool) -> dict:
    sources = sorted(path for path in compressed_root.rglob("*.xso.z") if path.is_file())
    files = []
    flat_strings = []
    errors = []
    for source in sources:
        relative = source.relative_to(compressed_root)
        output = decompressed_root / str(relative)[:-2]
        info, payload = inspect_container(source, include_data=True)
        if not info.valid or payload is None:
            errors.append({"path": str(relative).replace("\\", "/"), "stage": "decompress", "error": info.error})
            continue
        if output.exists() and not overwrite:
            existing = output.read_bytes()
            if existing != payload:
                errors.append({"path": str(relative), "stage": "output", "error": "기존 해제본이 payload와 다름"})
                continue
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
        try:
            parsed = parse_xso(output)
        except Exception as exc:
            errors.append({"path": str(relative).replace("\\", "/"), "stage": "xsr", "error": str(exc)})
            continue
        context = path_context(source, compressed_root)
        string_records = classify_strings(parsed)
        file_record = {
            **context,
            "compressed_size": source.stat().st_size,
            "decompressed_size": len(payload),
            "compressed_sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
            "xso_sha256": parsed.info.sha256,
            "code_word_count": parsed.info.code_word_count,
            "command_count": len(parsed.commands),
            "string_count": parsed.info.string_count,
        }
        files.append(file_record)
        for record in string_records:
            flat_strings.append({**context, "xso_sha256": parsed.info.sha256, **record})

    role_counts = Counter(role for record in flat_strings for role in record["roles"])
    token_counts = Counter(token for record in flat_strings for token in record["tokens"])
    markup_counts = Counter(markup for record in flat_strings for markup in record["markup"])
    return {
        "schema_version": 1,
        "stats": {
            "source_file_count": len(sources),
            "parsed_file_count": len(files),
            "error_count": len(errors),
            "string_count": len(flat_strings),
            "role_counts": dict(sorted(role_counts.items())),
            "token_counts": dict(sorted(token_counts.items())),
            "markup_counts": dict(sorted(markup_counts.items())),
        },
        "files": files,
        "strings": flat_strings,
        "errors": errors,
    }


def write_csv(catalog: dict, path: Path) -> None:
    fields = [
        "iso_path", "map_group", "map_id", "xso_name", "string_index", "roles",
        "byte_length", "file_offset", "text", "tokens", "markup", "is_empty", "is_ascii",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in catalog["strings"]:
            row = {key: record.get(key, "") for key in fields}
            for key in ("roles", "tokens", "markup"):
                row[key] = " | ".join(row[key])
            writer.writerow(row)


def write_html(catalog: dict, path: Path) -> None:
    embedded = json.dumps(catalog["strings"], ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Ys VI 대사 카탈로그</title>
<style>body{font-family:system-ui,sans-serif;margin:20px}input,select{padding:8px;margin-right:8px}table{border-collapse:collapse;width:100%;margin-top:12px}th,td{border:1px solid #ccc;padding:6px;vertical-align:top}th{position:sticky;top:0;background:#eee}.text{white-space:pre-wrap;min-width:340px}.meta{color:#666;font-size:12px}</style></head>
<body><h1>Ys VI 대사 카탈로그</h1><input id="q" size="45" placeholder="본문, 맵, 파일명 검색"><select id="role"><option value="">모든 역할</option></select><span id="count"></span>
<table><thead><tr><th>맵</th><th>파일/인덱스</th><th>역할</th><th>텍스트</th></tr></thead><tbody id="rows"></tbody></table>
<script>const data=__DATA__;const q=document.querySelector('#q'),role=document.querySelector('#role'),rows=document.querySelector('#rows'),count=document.querySelector('#count');
const roles=[...new Set(data.flatMap(x=>x.roles))].sort();roles.forEach(x=>role.add(new Option(x,x)));
function render(){const needle=q.value.toLowerCase(),r=role.value;const found=data.filter(x=>(!r||x.roles.includes(r))&&(!needle||[x.text,x.map_group,x.map_id,x.xso_name,x.iso_path].join(' ').toLowerCase().includes(needle)));count.textContent=`${found.length} / ${data.length}`;rows.innerHTML=found.slice(0,5000).map(x=>`<tr><td>${esc(x.map_group)} / ${esc(x.map_id)}</td><td>${esc(x.xso_name)} [${x.string_index}]<div class="meta">${esc(x.iso_path)}</div></td><td>${esc(x.roles.join(', '))}</td><td class="text">${esc(x.text)}</td></tr>`).join('')}
function esc(x){return String(x).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}q.addEventListener('input',render);role.addEventListener('change',render);render();</script></body></html>""".replace("__DATA__", embedded)
    path.write_text(html, encoding="utf-8", newline="\n")


def command_build(args: argparse.Namespace) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog(args.compressed, args.decompressed, args.overwrite)
    json_path = args.output / "dialogue_catalog.json"
    csv_path = args.output / "dialogue_catalog.csv"
    html_path = args.output / "dialogue_catalog.html"
    json_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_csv(catalog, csv_path)
    write_html(catalog, html_path)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "html": str(html_path), **catalog["stats"]}, ensure_ascii=False, indent=2))
    return 1 if catalog["errors"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ys VI PSP 전체 XSO 대사 카탈로그 생성기")
    parser.add_argument("compressed", type=Path)
    parser.add_argument("decompressed", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.set_defaults(func=command_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
