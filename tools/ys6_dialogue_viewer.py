#!/usr/bin/env python3
"""GUI viewer for Ys VI dialogue_catalog.json."""

from __future__ import annotations

import json
import csv
import hashlib
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Direct execution sets sys.path to /tools, while legacy build modules also
# support being executed from /tools/scripts. Make that sibling directory
# explicit so both entry styles resolve the same modules.
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from tools.scripts.ys6_cast_name_workspace import (
        STATUSES as CAST_STATUSES, atomic_write_json,
        load_workspace as load_cast_workspace,
        validate_workspace as validate_cast_workspace, write_csv as write_cast_csv,
    )
except ModuleNotFoundError:
    from scripts.ys6_cast_name_workspace import (
        STATUSES as CAST_STATUSES, atomic_write_json,
        load_workspace as load_cast_workspace,
        validate_workspace as validate_cast_workspace, write_csv as write_cast_csv,
    )
try:
    from tools.scripts.ys6_translation_workspace import normalize_editor_translation
    from tools.scripts.ys6_patch_builder import find_default_font, inspect_inputs, run_build
    from tools.scripts.ys6_additional_image_precompile import cache_status, precompile as precompile_additional_images
    from tools.scripts.ys6_item_workspace import encoded_length as item_encoded_length, load_workspace as load_item_workspace, validate_workspace as validate_item_workspace
    from tools.scripts.ys6_system_message_workspace import encoded_length as system_encoded_length, load_workspace as load_system_workspace, validate_workspace as validate_system_workspace
except ModuleNotFoundError:
    from scripts.ys6_translation_workspace import normalize_editor_translation
    from scripts.ys6_patch_builder import find_default_font, inspect_inputs, run_build
    from scripts.ys6_additional_image_precompile import cache_status, precompile as precompile_additional_images
    from scripts.ys6_item_workspace import encoded_length as item_encoded_length, load_workspace as load_item_workspace, validate_workspace as validate_item_workspace
    from scripts.ys6_system_message_workspace import encoded_length as system_encoded_length, load_workspace as load_system_workspace, validate_workspace as validate_system_workspace


def load_catalog(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("strings"), list):
        raise ValueError("지원하는 dialogue_catalog.json 형식이 아닙니다")
    return data.get("stats", {}), data["strings"]


def filter_records(records: list[dict], query: str = "", role: str = "") -> list[dict]:
    needle = query.casefold().strip()
    result = []
    for record in records:
        if role and role not in record.get("roles", []):
            continue
        haystack = " ".join(
            str(record.get(key, ""))
            for key in ("text", "source_text", "translation", "map_group", "map_id", "xso_name", "iso_path", "notes")
        ).casefold()
        if needle and needle not in haystack:
            continue
        result.append(record)
    return result


def filter_records_by_workflow(
    records: list[dict], workflow_status: str, empty_translation_only: bool = False
) -> list[dict]:
    """Apply the dialogue tab's role/status and empty-translation filters."""
    if workflow_status == "dialogue":
        result = [record for record in records if "dialogue" in record.get("roles", [])]
    elif workflow_status != "전체":
        result = [record for record in records if record.get("status") == workflow_status]
    else:
        result = records
    if empty_translation_only:
        result = [
            record
            for record in result
            if not normalize_editor_translation(record.get("translation") or "").strip()
        ]
    return result


def mark_records_override(records: list[dict]) -> dict[str, int]:
    """Mark translated records override without changing their text or notes."""
    result = {"selected": len(records), "changed": 0, "already_override": 0, "empty_translation": 0}
    for record in records:
        if not normalize_editor_translation(record.get("translation", "")).strip():
            result["empty_translation"] += 1
            continue
        if record.get("status") == "override":
            result["already_override"] += 1
            continue
        record["status"] = "override"
        result["changed"] += 1
    return result


def default_config_paths(script_path: Path | None = None) -> tuple[Path, Path, Path, Path, Path]:
    config_dir = (script_path or Path(__file__)).resolve().parent / "config"
    return (
        config_dir / "dialogue-translations.json",
        config_dir / "cast-names.json",
        config_dir / "item-translations.json",
        config_dir / "system-messages.json",
        config_dir / "dialogue-catalog.json",
    )


class DialogueViewer(tk.Tk):
    def __init__(self, initial_path: Path | None = None, cast_path: Path | None = None, item_path: Path | None = None, system_path: Path | None = None) -> None:
        super().__init__()
        self.title("Ys VI 대사 뷰어")
        self.geometry("1680x920")
        self.records: list[dict] = []
        self.filtered: list[dict] = []
        self.workspace_path: Path | None = None
        self.workspace_document: dict | None = None
        self.dialogue_dirty = False
        self._build_ui()
        if initial_path:
            self.open_json(initial_path)
        else:
            self.status.set("기본 대사 JSON을 찾지 못했습니다. 파일을 직접 열어 주세요.")
        if cast_path:
            if cast_path.exists(): self.cast_editor.open(cast_path)
            else: self.cast_editor.message.set(f"기본 인물명 JSON 없음: {cast_path}")
        if item_path:
            if item_path.exists(): self.item_editor.open(item_path)
            else: self.item_editor.message.set(f"기본 아이템 JSON 없음: {item_path}")
        if system_path:
            if system_path.exists(): self.system_editor.open(system_path)
            else: self.system_editor.message.set(f"기본 시스템 메시지 JSON 없음: {system_path}")

    def _build_ui(self) -> None:
        tabs = ttk.Notebook(self)
        tabs.pack(fill=tk.BOTH, expand=True)
        dialogue_tab = ttk.Frame(tabs)
        cast_tab = CastNameEditor(tabs)
        self.cast_editor = cast_tab
        item_tab = ItemEditor(tabs)
        self.item_editor = item_tab
        system_tab = SystemMessageEditor(tabs)
        self.system_editor = system_tab
        build_tab = PatchBuildEditor(tabs, self)
        self.build_editor = build_tab
        tabs.add(dialogue_tab, text="대사")
        tabs.add(cast_tab, text="인물·몬스터명")
        tabs.add(item_tab, text="아이템")
        tabs.add(system_tab, text="시스템 메시지")
        tabs.add(build_tab, text="패치 빌드")
        top = ttk.Frame(dialogue_tab, padding=8)
        top.pack(fill=tk.X)
        ttk.Button(top, text="카탈로그 열기", command=self.choose_catalog).pack(side=tk.LEFT)
        ttk.Button(top, text="번역 작업공간 열기", command=self.choose_workspace).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="번역 저장", command=self.save_workspace).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="CSV 내보내기", command=self.export_csv).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="CSV 가져오기", command=self.import_csv).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(top, text="검색").pack(side=tk.LEFT, padx=(12, 4))
        self.query = tk.StringVar()
        search = ttk.Entry(top, textvariable=self.query, width=48)
        search.pack(side=tk.LEFT)
        search.bind("<KeyRelease>", lambda _event: self.refresh())
        ttk.Label(top, text="역할").pack(side=tk.LEFT, padx=(12, 4))
        self.role = tk.StringVar()
        self.role_box = ttk.Combobox(top, textvariable=self.role, state="readonly", width=18)
        self.role_box.pack(side=tk.LEFT)
        self.role_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Label(top, text="상태").pack(side=tk.LEFT, padx=(12, 4))
        self.workflow_status = tk.StringVar(value="전체")
        workflow_box = ttk.Combobox(top, textvariable=self.workflow_status, state="readonly", width=12,
                                    values=("전체", "dialogue", "draft", "override", "untranslated", "excluded", "conflict", "orphaned"))
        workflow_box.pack(side=tk.LEFT)
        workflow_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.empty_translation_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="번역 비어 있음만",
            variable=self.empty_translation_only,
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.status = tk.StringVar(value="카탈로그를 열어 주세요.")
        ttk.Label(top, textvariable=self.status).pack(side=tk.RIGHT)

        pane = ttk.Panedwindow(dialogue_tab, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        table_frame = ttk.Frame(pane)
        detail_frame = ttk.Frame(pane)
        pane.add(table_frame, weight=3)
        pane.add(detail_frame, weight=2)
        columns = ("map", "file", "index", "roles", "status", "text", "translation")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        for column, label, width in zip(columns, ("맵", "XSO", "인덱스", "역할", "상태", "원문", "번역"), (110, 135, 50, 120, 85, 350, 350)):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, stretch=column == "text")
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.show_detail)
        self.detail = tk.Text(detail_frame, wrap=tk.WORD, font=("맑은 고딕", 10), height=8)
        self.detail.pack(fill=tk.BOTH, expand=True)
        editor = ttk.Frame(detail_frame, padding=(0, 6, 0, 0)); editor.pack(fill=tk.X)
        ttk.Label(editor, text="번역").grid(row=0, column=0, sticky="nw")
        self.translation = tk.Text(editor, height=4, wrap=tk.WORD, font=("맑은 고딕", 10)); self.translation.grid(row=0, column=1, columnspan=3, sticky="ew")
        ttk.Label(editor, text="상태").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.translation_status = tk.StringVar(value="untranslated")
        ttk.Combobox(editor, textvariable=self.translation_status, state="readonly", values=("untranslated", "draft", "override", "excluded", "conflict", "orphaned"), width=16).grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(editor, text="메모").grid(row=1, column=2, sticky="e", padx=(12, 4), pady=(4, 0))
        self.notes = ttk.Entry(editor); self.notes.grid(row=1, column=3, sticky="ew", pady=(4, 0))
        actions = ttk.Frame(editor)
        actions.grid(row=2, column=1, columnspan=3, sticky="e", pady=(6, 0))
        ttk.Button(actions, text="선택 항목 override", command=self.override_selected).pack(side=tk.LEFT)
        ttk.Button(actions, text="현재 항목 반영", command=self.apply_edit).pack(side=tk.LEFT, padx=(6, 0))
        editor.columnconfigure(1, weight=1); editor.columnconfigure(3, weight=2)

    def choose_catalog(self) -> None:
        selected = filedialog.askopenfilename(title="대사 카탈로그 열기", filetypes=[("JSON", "*.json"), ("모든 파일", "*.*")])
        if selected:
            self.open_catalog(Path(selected))

    def choose_workspace(self) -> None:
        selected = filedialog.askopenfilename(title="번역 작업공간 열기", filetypes=[("JSON", "*.json")])
        if not selected: return
        self.open_workspace(Path(selected))

    def open_workspace(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict) or not isinstance(data.get("records"), list):
                raise ValueError("지원하는 번역 작업공간 형식이 아닙니다")
            self.records = data["records"]
            self.workspace_document = data
            self.workspace_path = path
            roles = sorted({role for record in self.records for role in record.get("roles", [])})
            self.role_box["values"] = [""] + roles; self.role.set(""); self.title(f"Ys VI 번역 편집기 - {path.name}"); self.refresh()
        except Exception as exc:
            messagebox.showerror("열기 실패", f"{path}\n\n{exc}")

    def open_json(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            messagebox.showerror("기본 데이터 열기 실패", f"{path}\n\n{exc}")
            return
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            self.open_workspace(path)
        elif isinstance(data, dict) and isinstance(data.get("strings"), list):
            self.open_catalog(path)
        else:
            messagebox.showerror("열기 실패", f"지원하는 JSON 형식이 아닙니다.\n\n{path}")

    def save_workspace(self) -> None:
        if self.workspace_path is None: messagebox.showwarning("저장", "번역 작업공간을 먼저 열어 주세요."); return
        self.apply_edit(silent=True)
        document = dict(self.workspace_document or {"schema_version": 1})
        document["records"] = self.records
        atomic_write_json(self.workspace_path, document, backup=True)
        self.workspace_document = document
        self.dialogue_dirty = False
        self.status.set(f"저장 완료: {self.workspace_path.name}")

    def export_csv(self) -> None:
        if not self.records: messagebox.showwarning("CSV", "번역 작업공간을 먼저 열어 주세요."); return
        selected = filedialog.asksaveasfilename(title="번역 CSV 내보내기", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not selected: return
        fields = ("iso_path", "map_group", "map_id", "xso_name", "string_index", "roles", "source_text", "source_raw_hex", "source_sha256", "translation", "status", "notes")
        with Path(selected).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for record in self.records:
                row = {field: record.get(field, "") for field in fields}; row["roles"] = " | ".join(record.get("roles", [])); writer.writerow(row)
        self.status.set(f"CSV 내보내기 완료: {Path(selected).name}")

    def import_csv(self) -> None:
        if not self.records: messagebox.showwarning("CSV", "번역 작업공간을 먼저 열어 주세요."); return
        selected = filedialog.askopenfilename(title="번역 CSV 가져오기", filetypes=[("CSV", "*.csv")])
        if not selected: return
        by_key = {(record["iso_path"], int(record["string_index"])): record for record in self.records}
        updated = 0
        try:
            with Path(selected).open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    identity = (row["iso_path"], int(row["string_index"])); record = by_key.get(identity)
                    if record is None: raise ValueError(f"작업공간에 없는 키: {identity}")
                    if row.get("source_sha256") != record.get("source_sha256"): raise ValueError(f"원문 해시 불일치: {identity}")
                    record["translation"] = row.get("translation", ""); record["status"] = row.get("status", "untranslated"); record["notes"] = row.get("notes", ""); updated += 1
        except Exception as exc: messagebox.showerror("CSV 가져오기 실패", str(exc)); return
        self.refresh(); self.status.set(f"CSV 가져오기 완료: {updated:,}개")

    def apply_edit(self, silent: bool = False) -> None:
        selected = self.tree.selection()
        if not selected:
            if not silent: messagebox.showwarning("편집", "항목을 선택해 주세요.")
            return
        record = self.filtered[int(selected[0])]
        values = (normalize_editor_translation(self.translation.get("1.0", "end-1c")), self.translation_status.get(), self.notes.get())
        if values != (record.get("translation", ""), record.get("status", "untranslated"), record.get("notes", "")):
            record["translation"], record["status"], record["notes"] = values; self.dialogue_dirty = True
        if not silent: self.refresh()

    def override_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("override", "override로 변경할 항목을 선택해 주세요.")
            return
        selected_records = [self.filtered[int(item)] for item in selected]
        result = mark_records_override(selected_records)
        if result["changed"]:
            self.dialogue_dirty = True

        # Updating rows in place preserves Ctrl/Shift multi-selection. If a
        # status filter no longer includes the changed records, refresh instead.
        active_filter = self.workflow_status.get()
        if active_filter not in ("전체", "dialogue"):
            self.refresh()
        else:
            for item, record in zip(selected, selected_records):
                values = list(self.tree.item(item, "values"))
                if len(values) >= 5:
                    values[4] = record.get("status", "")
                    self.tree.item(item, values=values)
            if selected:
                first = selected[0]
                self.tree.selection_set(selected)
                self.tree.focus(first)
                self.tree.see(first)
                self.show_detail()

        self.status.set(
            f"override 변경 {result['changed']:,}개 / 이미 override {result['already_override']:,}개 / "
            f"빈 번역 제외 {result['empty_translation']:,}개 (번역 저장 필요)"
        )

    def open_catalog(self, path: Path) -> None:
        try:
            _stats, self.records = load_catalog(path)
        except Exception as exc:
            messagebox.showerror("열기 실패", str(exc))
            return
        roles = sorted({role for record in self.records for role in record.get("roles", [])})
        self.role_box["values"] = [""] + roles
        self.role.set("")
        self.workspace_path = None
        self.workspace_document = None
        self.dialogue_dirty = False
        self.title(f"Ys VI 대사 뷰어 - {path.name}")
        self.refresh()

    def refresh(self) -> None:
        self.filtered = filter_records(self.records, self.query.get(), self.role.get())
        self.filtered = filter_records_by_workflow(
            self.filtered, self.workflow_status.get(), self.empty_translation_only.get()
        )
        self.tree.delete(*self.tree.get_children())
        for index, record in enumerate(self.filtered):
            text = record.get("text", record.get("source_text", "")).replace("\\n", " / ")
            self.tree.insert("", tk.END, iid=str(index), values=(
                f"{record.get('map_group','')}/{record.get('map_id','')}", record.get("xso_name", ""),
                record.get("string_index", ""), ", ".join(record.get("roles", [])), record.get("status", ""), text,
                record.get("translation", "").replace("\\n", " / "),
            ))
        self.status.set(f"{len(self.filtered):,} / {len(self.records):,}개")

    def show_detail(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        record = self.filtered[int(selected[0])]
        lines = [
            record.get("text", record.get("source_text", "")), "", f"역할: {', '.join(record.get('roles', []))}",
            f"맵: {record.get('map_group','')} / {record.get('map_id','')}",
            f"XSO: {record.get('xso_name','')}  인덱스: {record.get('string_index','')}",
            f"ISO 경로: {record.get('iso_path','')}",
            f"파일 오프셋: 0x{record.get('file_offset',0):X}", f"CP932 길이: {record.get('byte_length',0)}바이트",
            f"토큰: {record.get('tokens', [])}", f"마크업: {record.get('markup', [])}", "",
            "확정 참조:", json.dumps(record.get("references", []), ensure_ascii=False, indent=2), "",
            "가능성 참조:", json.dumps(record.get("possible_references", []), ensure_ascii=False, indent=2),
        ]
        self.detail.delete("1.0", tk.END)
        self.detail.insert("1.0", "\n".join(lines))
        self.translation.delete("1.0", tk.END); self.translation.insert("1.0", record.get("translation", ""))
        self.translation_status.set(record.get("status", "untranslated")); self.notes.delete(0, tk.END); self.notes.insert(0, record.get("notes", ""))


class CastNameEditor(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent, padding=8)
        self.path: Path | None = None
        self.workspace: dict = {"schema_version": 1, "records": []}
        self.filtered: list[dict] = []
        self.dirty = False
        self._selected_identifier: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        bar = ttk.Frame(self); bar.pack(fill=tk.X)
        ttk.Button(bar, text="작업공간 열기", command=self.choose).pack(side=tk.LEFT)
        ttk.Button(bar, text="저장", command=self.save).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="검증", command=self.validate).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="CSV 내보내기", command=self.export_csv).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(bar, text="검색").pack(side=tk.LEFT, padx=(14, 4))
        self.query = tk.StringVar(); entry = ttk.Entry(bar, textvariable=self.query, width=30); entry.pack(side=tk.LEFT); entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.filter_status = tk.StringVar(value="전체")
        box = ttk.Combobox(bar, textvariable=self.filter_status, state="readonly", values=("전체", "미번역", "검수 완료") + CAST_STATUSES, width=12); box.pack(side=tk.LEFT, padx=(6, 0)); box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.category = tk.StringVar(value="전체")
        category_box = ttk.Combobox(bar, textvariable=self.category, state="readonly", values=("전체", "인물", "몬스터"), width=9); category_box.pack(side=tk.LEFT, padx=(6, 0)); category_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.message = tk.StringVar(value="인물명 작업공간을 열어 주세요."); ttk.Label(bar, textvariable=self.message).pack(side=tk.RIGHT)

        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL); pane.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left, right = ttk.Frame(pane), ttk.Frame(pane, padding=(8, 0, 0, 0)); pane.add(left, weight=3); pane.add(right, weight=2)
        columns = ("identifier", "source", "translation", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
        for col, label, width in zip(columns, ("ID", "일본어 원문", "한국어 번역", "상태"), (110, 180, 180, 100)):
            self.tree.heading(col, text=label); self.tree.column(col, width=width)
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y); self.tree.bind("<<TreeviewSelect>>", self.show)

        self.info = tk.StringVar(); ttk.Label(right, textvariable=self.info, justify=tk.LEFT).pack(fill=tk.X)
        ttk.Label(right, text="번역").pack(anchor="w", pady=(10, 0)); self.translation = ttk.Entry(right, font=("맑은 고딕", 11)); self.translation.pack(fill=tk.X)
        ttk.Label(right, text="상태").pack(anchor="w", pady=(8, 0)); self.edit_status = tk.StringVar(value="untranslated"); ttk.Combobox(right, textvariable=self.edit_status, state="readonly", values=CAST_STATUSES).pack(fill=tk.X)
        ttk.Label(right, text="메모").pack(anchor="w", pady=(8, 0)); self.notes = tk.Text(right, height=5, wrap=tk.WORD, font=("맑은 고딕", 10)); self.notes.pack(fill=tk.X)
        actions=ttk.Frame(right);actions.pack(anchor="e",pady=(8,0));ttk.Button(actions,text="선택 항목 reviewed",command=self.review_selected).pack(side=tk.LEFT);ttk.Button(actions, text="현재 항목 반영", command=self.apply_edit).pack(side=tk.LEFT,padx=(6,0))

    def choose(self) -> None:
        if self.dirty and not messagebox.askyesno("미저장 변경", "저장하지 않은 변경을 버리고 다른 파일을 여시겠습니까?"): return
        selected = filedialog.askopenfilename(title="인물명 작업공간 열기", filetypes=[("JSON", "*.json")])
        if selected: self.open(Path(selected))

    def open(self, path: Path) -> None:
        try: self.workspace = load_cast_workspace(path)
        except Exception as exc: messagebox.showerror("열기 실패", str(exc)); return
        self.path = path
        self.dirty = False
        self._selected_identifier = None
        self.refresh(commit_current=False)
        self.message.set(f"{path.name}: {len(self.workspace['records']):,}개")

    def _commit_selected(self) -> None:
        if not self._selected_identifier: return
        row = next((r for r in self.workspace["records"] if r["identifier"] == self._selected_identifier), None)
        if row is None: return
        values = (self.translation.get(), self.edit_status.get(), self.notes.get("1.0", "end-1c"))
        if values != (row.get("translation", ""), row.get("status", "untranslated"), row.get("notes", "")):
            row["translation"], row["status"], row["notes"] = values; self.dirty = True

    def apply_edit(self) -> None:
        if not self._selected_identifier: messagebox.showwarning("편집", "항목을 선택해 주세요."); return
        identifier = self._selected_identifier
        self._commit_selected()
        self.refresh(select=identifier, commit_current=False)

    def review_selected(self) -> None:
        selected=self.tree.selection()
        if not selected:messagebox.showwarning("reviewed","항목을 선택해 주세요.");return
        self._commit_selected();changed=0;empty=0
        selected_identifiers = [self.filtered[int(item)]["identifier"] for item in selected]
        for item in selected:
            row=self.filtered[int(item)]
            if not row.get("translation","").strip():empty+=1;continue
            if row.get("status")!="reviewed":row["status"]="reviewed";changed+=1
        self.dirty|=bool(changed)
        self.refresh(selections=selected_identifiers, commit_current=False)
        self.message.set(f"reviewed 변경 {changed:,}개 / 빈 번역 제외 {empty:,}개")

    def save(self) -> None:
        if self.path is None: messagebox.showwarning("저장", "작업공간을 먼저 열어 주세요."); return
        self._commit_selected(); errors = validate_cast_workspace(self.workspace)
        if errors: messagebox.showerror("저장 전 검증 실패", "\n".join(errors[:20])); return
        atomic_write_json(self.path, self.workspace, backup=True); self.dirty = False; self.message.set(f"저장 완료: {self.path.name}")

    def validate(self) -> None:
        self._commit_selected(); errors = validate_cast_workspace(self.workspace)
        if errors: messagebox.showerror("검증 실패", "\n".join(errors[:20]))
        else: messagebox.showinfo("검증", f"정상: {len(self.workspace.get('records', [])):,}개")

    def export_csv(self) -> None:
        if not self.workspace.get("records"): messagebox.showwarning("CSV", "작업공간을 먼저 열어 주세요."); return
        selected = filedialog.asksaveasfilename(title="인물명 CSV 내보내기", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if selected: self._commit_selected(); write_cast_csv(Path(selected), self.workspace); self.message.set(f"CSV 내보내기 완료: {Path(selected).name}")

    def _clear_editor(self) -> None:
        self._selected_identifier = None
        self.info.set("")
        self.translation.delete(0, tk.END)
        self.edit_status.set("untranslated")
        self.notes.delete("1.0", tk.END)

    def refresh(self, select: str | None = None, selections: list[str] | None = None,
                commit_current: bool = True) -> None:
        if commit_current:
            self._commit_selected()
        requested = list(selections or ([] if select is None else [select]))
        # Tree recreation can emit a delayed selection event. Detach the old
        # identifier first so stale editor fields can never be committed.
        self._selected_identifier = None
        needle = self.query.get().casefold().strip(); status = self.filter_status.get()
        rows = self.workspace.get("records", [])
        category=self.category.get()
        if category=="몬스터":rows=[r for r in rows if r.get("identifier","").startswith("CAST_M")]
        elif category=="인물":rows=[r for r in rows if not r.get("identifier","").startswith("CAST_M")]
        if status == "미번역": rows = [r for r in rows if r.get("status") == "untranslated"]
        elif status == "검수 완료": rows = [r for r in rows if r.get("status") == "reviewed"]
        elif status != "전체": rows = [r for r in rows if r.get("status") == status]
        self.filtered = [r for r in rows if not needle or needle in " ".join(str(r.get(k, "")) for k in ("identifier", "source", "translation", "notes")).casefold()]
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.filtered): self.tree.insert("", tk.END, iid=str(i), values=(row["identifier"], row["source"], row.get("translation", ""), row.get("status", "")))
        monsters=sum(r.get("identifier","").startswith("CAST_M") for r in self.workspace.get("records",[]));reviewed_monsters=sum(r.get("identifier","").startswith("CAST_M") and r.get("status")=="reviewed" for r in self.workspace.get("records",[]));self.message.set(f"{len(self.filtered):,}/{len(self.workspace.get('records', [])):,}개 · 몬스터 {monsters} (reviewed {reviewed_monsters})")
        by_identifier = {row["identifier"]: str(i) for i, row in enumerate(self.filtered)}
        visible = [by_identifier[identifier] for identifier in requested if identifier in by_identifier]
        if visible:
            self.tree.selection_set(visible)
            self.tree.focus(visible[0])
            self.tree.see(visible[0])
            self.show()
        else:
            self._clear_editor()

    def show(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected: return
        next_row = self.filtered[int(selected[0])]
        if self._selected_identifier and self._selected_identifier != next_row["identifier"]: self._commit_selected()
        self._selected_identifier = next_row["identifier"]
        self.info.set(f"ID: {next_row['identifier']}\n원문: {next_row['source']}\n식별자 오프셋: 0x{next_row['identifier_offset']:X}\n이름 오프셋: 0x{next_row['name_offset']:X}\n원문 HEX: {next_row['source_raw_hex']}\nSHA-256: {next_row['source_sha256']}")
        self.translation.delete(0, tk.END); self.translation.insert(0, next_row.get("translation", "")); self.edit_status.set(next_row.get("status", "untranslated")); self.notes.delete("1.0", tk.END); self.notes.insert("1.0", next_row.get("notes", ""))


class ItemEditor(ttk.Frame):
    STATUSES = ("untranslated", "draft", "override", "excluded", "conflict")

    def __init__(self, parent) -> None:
        super().__init__(parent, padding=8)
        self.path: Path | None = None; self.workspace = {"schema_version": 1, "records": []}
        self.filtered: list[dict] = []; self.dirty = False; self._selected_index: int | None = None
        bar = ttk.Frame(self); bar.pack(fill=tk.X)
        ttk.Button(bar, text="작업공간 열기", command=self.choose).pack(side=tk.LEFT)
        ttk.Button(bar, text="저장", command=self.save).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="검증", command=self.validate).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="선택 항목 override", command=self.override_selected).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(bar, text="검색").pack(side=tk.LEFT, padx=(14, 4))
        self.query=tk.StringVar(); search=ttk.Entry(bar,textvariable=self.query,width=32);search.pack(side=tk.LEFT);search.bind("<KeyRelease>",lambda _e:self.refresh())
        self.filter_status=tk.StringVar(value="전체");box=ttk.Combobox(bar,textvariable=self.filter_status,state="readonly",values=("전체",)+self.STATUSES,width=12);box.pack(side=tk.LEFT,padx=(6,0));box.bind("<<ComboboxSelected>>",lambda _e:self.refresh())
        self.message=tk.StringVar(value="아이템 작업공간을 열어 주세요.");ttk.Label(bar,textvariable=self.message).pack(side=tk.RIGHT)
        pane=ttk.Panedwindow(self,orient=tk.HORIZONTAL);pane.pack(fill=tk.BOTH,expand=True,pady=(8,0));left,right=ttk.Frame(pane),ttk.Frame(pane,padding=(8,0,0,0));pane.add(left,weight=3);pane.add(right,weight=2)
        columns=("index","id","source","translation","status");self.tree=ttk.Treeview(left,columns=columns,show="headings",selectmode="extended")
        for col,label,width in zip(columns,("번호","ID","일본어 이름","한국어 이름","상태"),(55,90,170,170,90)):
            self.tree.heading(col,text=label);self.tree.column(col,width=width)
        scroll=ttk.Scrollbar(left,orient=tk.VERTICAL,command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(side=tk.LEFT,fill=tk.BOTH,expand=True);scroll.pack(side=tk.RIGHT,fill=tk.Y);self.tree.bind("<<TreeviewSelect>>",self.show)
        self.info=tk.StringVar();ttk.Label(right,textvariable=self.info,justify=tk.LEFT).pack(fill=tk.X)
        ttk.Label(right,text="한국어 이름").pack(anchor="w",pady=(8,0));self.name=ttk.Entry(right,font=("맑은 고딕",11));self.name.pack(fill=tk.X)
        ttk.Label(right,text="일본어 설명").pack(anchor="w",pady=(8,0));self.source_desc=tk.Text(right,height=5,wrap=tk.WORD,font=("맑은 고딕",10),state=tk.DISABLED);self.source_desc.pack(fill=tk.X)
        ttk.Label(right,text="한국어 설명").pack(anchor="w",pady=(8,0));self.description=tk.Text(right,height=6,wrap=tk.WORD,font=("맑은 고딕",10));self.description.pack(fill=tk.X)
        row=ttk.Frame(right);row.pack(fill=tk.X,pady=(8,0));ttk.Label(row,text="상태").pack(side=tk.LEFT);self.edit_status=tk.StringVar(value="draft");ttk.Combobox(row,textvariable=self.edit_status,state="readonly",values=self.STATUSES,width=14).pack(side=tk.LEFT,padx=(6,12));ttk.Label(row,text="메모").pack(side=tk.LEFT);self.notes=ttk.Entry(row);self.notes.pack(side=tk.LEFT,fill=tk.X,expand=True)
        ttk.Button(right,text="현재 항목 반영",command=self.apply_edit).pack(anchor="e",pady=(8,0))

    def choose(self):
        selected=filedialog.askopenfilename(title="아이템 작업공간 열기",filetypes=[("JSON","*.json")]);
        if selected:self.open(Path(selected))

    def open(self,path:Path):
        try:self.workspace=load_item_workspace(path)
        except Exception as exc:messagebox.showerror("열기 실패",str(exc));return
        self.path=path;self.dirty=False;self.refresh()

    def _commit_selected(self):
        if self._selected_index is None:return
        row=next((x for x in self.workspace["records"] if x["index"]==self._selected_index),None)
        if row is None:return
        values=(self.name.get(),self.description.get("1.0","end-1c").replace("\r\n","\n").replace("\r","\n"),self.edit_status.get(),self.notes.get())
        old=(row.get("translation_name",""),row.get("translation_description",""),row.get("status","draft"),row.get("notes",""))
        if values!=old:row["translation_name"],row["translation_description"],row["status"],row["notes"]=values;self.dirty=True

    def apply_edit(self):
        self._commit_selected();self.refresh(select=self._selected_index)

    def save(self):
        if self.path is None:messagebox.showwarning("저장","작업공간을 먼저 열어 주세요.");return
        self._commit_selected();errors=validate_item_workspace(self.workspace)
        if errors:messagebox.showerror("저장 전 검증 실패","\n".join(errors[:20]));return
        atomic_write_json(self.path,self.workspace,backup=True);self.dirty=False;self.message.set(f"저장 완료: {self.path.name}")

    def validate(self):
        self._commit_selected();errors=validate_item_workspace(self.workspace)
        if errors:messagebox.showerror("검증 실패","\n".join(errors[:20]))
        else:messagebox.showinfo("검증",f"정상: {len(self.workspace.get('records',[])):,}개")

    def override_selected(self):
        selected=self.tree.selection()
        if not selected:messagebox.showwarning("override","항목을 선택해 주세요.");return
        self._commit_selected();changed=0;empty=0
        for item in selected:
            row=self.filtered[int(item)]
            if not row.get("translation_name","").strip():empty+=1;continue
            if row.get("status")!="override":row["status"]="override";changed+=1
        self.dirty|=bool(changed);self.refresh();self.message.set(f"override 변경 {changed:,}개 / 빈 이름 제외 {empty:,}개")

    def refresh(self,select=None):
        rows=self.workspace.get("records",[]);status=self.filter_status.get();needle=self.query.get().casefold().strip()
        if status!="전체":rows=[x for x in rows if x.get("status")==status]
        self.filtered=[x for x in rows if not needle or needle in " ".join(str(x.get(k,"")) for k in ("resource_id","source_name","source_description","translation_name","translation_description","notes")).casefold()]
        self.tree.delete(*self.tree.get_children())
        for i,row in enumerate(self.filtered):self.tree.insert("",tk.END,iid=str(i),values=(row["index"],row["resource_id"],row["source_name"],row.get("translation_name",""),row.get("status","")))
        counts={s:sum(x.get("status")==s for x in self.workspace.get("records",[])) for s in self.STATUSES};self.message.set(f"{len(self.filtered):,}/{len(self.workspace.get('records',[])):,}개 · override {counts['override']} · draft {counts['draft']}")
        if select is not None:
            for i,row in enumerate(self.filtered):
                if row["index"]==select:self.tree.selection_set(str(i));self.tree.see(str(i));self.show();break

    def show(self,_event=None):
        selected=self.tree.selection()
        if not selected:return
        row=self.filtered[int(selected[0])]
        if self._selected_index is not None and self._selected_index!=row["index"]:self._commit_selected()
        self._selected_index=row["index"];name_length=item_encoded_length(row.get("translation_name",""))+1;description_length=item_encoded_length(row.get("translation_description",""),True)+1;self.info.set(f"번호: {row['index']}\nID: {row['resource_id']}\n일본어 이름: {row['source_name']}\n인코딩 길이: 이름 {name_length}/32 · 설명 {description_length}/108바이트\n원본 레코드 SHA-256: {row['source_record_sha256']}")
        self.name.delete(0,tk.END);self.name.insert(0,row.get("translation_name",""));self.source_desc.configure(state=tk.NORMAL);self.source_desc.delete("1.0",tk.END);self.source_desc.insert("1.0",row.get("source_description",""));self.source_desc.configure(state=tk.DISABLED);self.description.delete("1.0",tk.END);self.description.insert("1.0",row.get("translation_description",""));self.edit_status.set(row.get("status","draft"));self.notes.delete(0,tk.END);self.notes.insert(0,row.get("notes",""))


class SystemMessageEditor(ttk.Frame):
    STATUSES = ("untranslated", "draft", "override", "excluded", "conflict")

    def __init__(self, parent) -> None:
        super().__init__(parent, padding=8)
        self.path: Path | None = None
        self.workspace = {"schema_version": 1, "encoding": "euc_jp", "record_count": 0, "records": []}
        self.filtered: list[dict] = []
        self.dirty = False
        self._selected_identifier: str | None = None
        bar = ttk.Frame(self); bar.pack(fill=tk.X)
        ttk.Button(bar, text="작업공간 열기", command=self.choose).pack(side=tk.LEFT)
        ttk.Button(bar, text="저장", command=self.save).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="검증", command=self.validate).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(bar, text="선택 항목 override", command=self.override_selected).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(bar, text="검색").pack(side=tk.LEFT, padx=(14, 4))
        self.query = tk.StringVar(); search = ttk.Entry(bar, textvariable=self.query, width=34); search.pack(side=tk.LEFT); search.bind("<KeyRelease>", lambda _e: self.refresh())
        self.filter_status = tk.StringVar(value="전체")
        box = ttk.Combobox(bar, textvariable=self.filter_status, state="readonly", values=("전체",) + self.STATUSES, width=12); box.pack(side=tk.LEFT, padx=(6, 0)); box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.message = tk.StringVar(value="시스템 메시지 작업공간을 열어 주세요."); ttk.Label(bar, textvariable=self.message).pack(side=tk.RIGHT)
        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL); pane.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left, right = ttk.Frame(pane), ttk.Frame(pane, padding=(8, 0, 0, 0)); pane.add(left, weight=3); pane.add(right, weight=2)
        columns = ("offset", "source", "translation", "length", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
        for col, label, width in zip(columns, ("EBOOT 오프셋", "일본어 원문", "한국어 번역", "길이", "상태"), (105, 300, 300, 80, 95)):
            self.tree.heading(col, text=label); self.tree.column(col, width=width, stretch=col in ("source", "translation"))
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y); self.tree.bind("<<TreeviewSelect>>", self.show)
        self.info = tk.StringVar(); ttk.Label(right, textvariable=self.info, justify=tk.LEFT, wraplength=460).pack(fill=tk.X)
        ttk.Label(right, text="일본어 원문").pack(anchor="w", pady=(8, 0)); self.source = tk.Text(right, height=5, wrap=tk.WORD, font=("맑은 고딕", 10), state=tk.DISABLED); self.source.pack(fill=tk.X)
        ttk.Label(right, text="한국어 번역").pack(anchor="w", pady=(8, 0)); self.translation = tk.Text(right, height=5, wrap=tk.WORD, font=("맑은 고딕", 10)); self.translation.pack(fill=tk.X)
        row = ttk.Frame(right); row.pack(fill=tk.X, pady=(8, 0)); ttk.Label(row, text="상태").pack(side=tk.LEFT)
        self.edit_status = tk.StringVar(value="untranslated"); ttk.Combobox(row, textvariable=self.edit_status, state="readonly", values=self.STATUSES, width=14).pack(side=tk.LEFT, padx=(6, 12))
        ttk.Label(row, text="분류").pack(side=tk.LEFT); self.category = ttk.Entry(row, width=14); self.category.pack(side=tk.LEFT, padx=(6, 12))
        ttk.Label(row, text="메모").pack(side=tk.LEFT); self.notes = ttk.Entry(row); self.notes.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(right, text="현재 항목 반영", command=self.apply_edit).pack(anchor="e", pady=(8, 0))

    def choose(self):
        selected = filedialog.askopenfilename(title="시스템 메시지 작업공간 열기", filetypes=[("JSON", "*.json")])
        if selected: self.open(Path(selected))

    def open(self, path: Path):
        try: self.workspace = load_system_workspace(path)
        except Exception as exc: messagebox.showerror("열기 실패", str(exc)); return
        self.path = path; self.dirty = False; self._selected_identifier = None; self.refresh()

    def _commit_selected(self):
        if self._selected_identifier is None: return
        row = next((x for x in self.workspace["records"] if x["identifier"] == self._selected_identifier), None)
        if row is None: return
        values = (self.translation.get("1.0", "end-1c"), self.edit_status.get(), self.category.get(), self.notes.get())
        old = (row.get("translation", ""), row.get("status", "untranslated"), row.get("category", ""), row.get("notes", ""))
        if values != old:
            row["translation"], row["status"], row["category"], row["notes"] = values; self.dirty = True

    def apply_edit(self):
        identifier = self._selected_identifier; self._commit_selected(); self.refresh(select=identifier)

    def save(self):
        if self.path is None: messagebox.showwarning("저장", "작업공간을 먼저 열어 주세요."); return
        self._commit_selected(); errors = validate_system_workspace(self.workspace)
        if errors: messagebox.showerror("저장 전 검증 실패", "\n".join(errors[:20])); return
        atomic_write_json(self.path, self.workspace, backup=True); self.dirty = False; self.message.set(f"저장 완료: {self.path.name}")

    def validate(self):
        self._commit_selected(); errors = validate_system_workspace(self.workspace)
        if errors: messagebox.showerror("검증 실패", "\n".join(errors[:20]))
        else: messagebox.showinfo("검증", f"정상: {len(self.workspace.get('records', [])):,}개")

    def override_selected(self):
        selected = self.tree.selection()
        if not selected: messagebox.showwarning("override", "항목을 선택해 주세요."); return
        self._commit_selected()
        selected_rows = [self.filtered[int(item)] for item in selected]
        selected_identifier = selected_rows[0]["identifier"]
        changed = 0; empty = 0; overflow = 0
        for row in selected_rows:
            translation = row.get("translation", "")
            if not translation.strip(): empty += 1; continue
            if system_encoded_length(translation) + 1 > row["allocated_size"]:
                row["status"] = "conflict"; overflow += 1; continue
            if row.get("status") != "override": row["status"] = "override"; changed += 1
        self.dirty |= bool(changed or overflow)
        # The editor widgets still contain the pre-override status. Do not let
        # a later selection change commit those stale values back to this row.
        self._selected_identifier = None
        self.refresh(select=selected_identifier)
        self.message.set(f"override 변경 {changed:,}개 / 빈 번역 {empty:,}개 / 길이 초과 conflict {overflow:,}개")

    def _clear_detail(self):
        self._selected_identifier = None
        self.info.set("")
        self.source.configure(state=tk.NORMAL); self.source.delete("1.0", tk.END); self.source.configure(state=tk.DISABLED)
        self.translation.delete("1.0", tk.END)
        self.edit_status.set("untranslated")
        self.category.delete(0, tk.END)
        self.notes.delete(0, tk.END)

    def refresh(self, select=None):
        rows = self.workspace.get("records", []); status = self.filter_status.get(); needle = self.query.get().casefold().strip()
        if status != "전체": rows = [x for x in rows if x.get("status") == status]
        self.filtered = [x for x in rows if not needle or needle in " ".join(str(x.get(k, "")) for k in ("identifier", "offset", "source", "translation", "category", "notes")).casefold()]
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.filtered):
            used = system_encoded_length(row.get("translation", "")) + 1 if row.get("translation") else 0
            self.tree.insert("", tk.END, iid=str(i), values=(f"0x{row['offset']:X}", row["source"], row.get("translation", ""), f"{used}/{row['allocated_size']}", row.get("status", "")))
        counts = {s: sum(x.get("status") == s for x in self.workspace.get("records", [])) for s in self.STATUSES}; self.message.set(f"{len(self.filtered):,}/{len(self.workspace.get('records', [])):,}개 · override {counts['override']} · draft {counts['draft']} · conflict {counts['conflict']}")
        if select is not None:
            for i, row in enumerate(self.filtered):
                if row["identifier"] == select:
                    self.tree.selection_set(str(i)); self.tree.see(str(i)); self.show(); return
            self._clear_detail()

    def show(self, _event=None):
        selected = self.tree.selection()
        if not selected: return
        row = self.filtered[int(selected[0])]
        if self._selected_identifier is not None and self._selected_identifier != row["identifier"]: self._commit_selected()
        self._selected_identifier = row["identifier"]
        used = system_encoded_length(row.get("translation", "")) + 1 if row.get("translation") else 0
        self.info.set(f"ID: {row['identifier']}\nEBOOT 오프셋: 0x{row['offset']:X}\n번역 길이: {used}/{row['allocated_size']}바이트\n원본 SHA-256: {row['source_sha256']}\n원본 HEX: {row['source_raw_hex']}")
        self.source.configure(state=tk.NORMAL); self.source.delete("1.0", tk.END); self.source.insert("1.0", row["source"]); self.source.configure(state=tk.DISABLED)
        self.translation.delete("1.0", tk.END); self.translation.insert("1.0", row.get("translation", "")); self.edit_status.set(row.get("status", "untranslated")); self.category.delete(0, tk.END); self.category.insert(0, row.get("category", "")); self.notes.delete(0, tk.END); self.notes.insert(0, row.get("notes", ""))


class PatchBuildEditor(ttk.Frame):
    def __init__(self, parent, app: DialogueViewer) -> None:
        super().__init__(parent, padding=12); self.app = app; self.events = queue.Queue(); self.running = False
        self.iso = tk.StringVar(); self.output = tk.StringVar(); self.font = tk.StringVar(value=str(find_default_font() or ""))
        self.apply_option_images = tk.BooleanVar(value=True)
        self.apply_additional_images = tk.BooleanVar(value=True)
        self.cache_state = tk.StringVar(value="이미지 캐시: 원본 ISO 선택 필요")
        self.counts = tk.StringVar(value="패치 데이터를 확인하지 않았습니다."); self.result = tk.StringVar()
        self._build_ui(); self.after(100, self._poll); self.refresh_data(silent=True)

    def _build_ui(self) -> None:
        form = ttk.Frame(self); form.pack(fill=tk.X)
        for row, (label, variable, command) in enumerate((("원본 ISO", self.iso, self.choose_iso), ("출력 ISO", self.output, self.choose_output), ("글꼴", self.font, self.choose_font))):
            ttk.Label(form, text=label, width=10).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Button(form, text="찾아보기", command=command).grid(row=row, column=2, padx=(6, 0), pady=4)
        form.columnconfigure(1, weight=1)
        image_options = ttk.Frame(self); image_options.pack(fill=tk.X, pady=(8, 0))
        self.option_images_check = ttk.Checkbutton(
            image_options, text="옵션 메뉴 이미지 적용", variable=self.apply_option_images,
            command=lambda: self.refresh_data(silent=True))
        self.option_images_check.pack(side=tk.LEFT)
        self.additional_images_check = ttk.Checkbutton(
            image_options, text="추가 이미지 적용", variable=self.apply_additional_images,
            command=lambda: self.refresh_data(silent=True))
        self.additional_images_check.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(image_options, textvariable=self.cache_state).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(self, textvariable=self.counts).pack(anchor="w", pady=(10, 4))
        buttons = ttk.Frame(self); buttons.pack(fill=tk.X)
        self.refresh_button = ttk.Button(buttons, text="데이터 다시 읽기", command=self.refresh_data); self.refresh_button.pack(side=tk.LEFT)
        self.option_images_button = ttk.Button(buttons, text="메뉴 이미지 폴더", command=self.open_option_images); self.option_images_button.pack(side=tk.LEFT, padx=(6, 0))
        self.additional_images_button = ttk.Button(buttons, text="추가 이미지 폴더", command=self.open_additional_images); self.additional_images_button.pack(side=tk.LEFT, padx=(6, 0))
        self.cache_refresh_button = ttk.Button(buttons, text="이미지 캐시 갱신", command=self.start_cache_refresh); self.cache_refresh_button.pack(side=tk.LEFT, padx=(6, 0))
        self.preflight_button = ttk.Button(buttons, text="사전 검증", command=lambda: self.start("preflight")); self.preflight_button.pack(side=tk.LEFT, padx=(6, 0))
        self.build_button = ttk.Button(buttons, text="패치 ISO 만들기", command=lambda: self.start("build")); self.build_button.pack(side=tk.LEFT, padx=(6, 0))
        self.progress = ttk.Progressbar(buttons, mode="indeterminate", length=180); self.progress.pack(side=tk.RIGHT)
        ttk.Label(self, textvariable=self.result, foreground="#145a32").pack(anchor="w", pady=(8, 4))
        self.log = tk.Text(self, height=24, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED); self.log.pack(fill=tk.BOTH, expand=True)

    def choose_iso(self) -> None:
        selected = filedialog.askopenfilename(title="Ys VI 원본 ISO 선택", filetypes=[("ISO", "*.iso")])
        if selected:
            self.iso.set(selected)
            if not self.output.get(): self.output.set(str(Path(selected).with_name("Ys VI - Korean Patched.iso")))
            self.refresh_cache_status(silent=True)

    def choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(title="패치 ISO 저장", defaultextension=".iso", initialfile="Ys VI - Korean Patched.iso", filetypes=[("ISO", "*.iso")])
        if selected: self.output.set(selected)

    def choose_font(self) -> None:
        selected = filedialog.askopenfilename(title="굴림 글꼴 선택", filetypes=[("TrueType", "*.ttc *.ttf"), ("모든 파일", "*.*")])
        if selected: self.font.set(selected)

    def open_option_images(self) -> None:
        try:
            info = inspect_inputs()
            folder = info["paths"]["option_menu_edited"]
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror("메뉴 이미지", str(exc))

    def open_additional_images(self) -> None:
        try:
            info = inspect_inputs()
            folder = info["paths"]["additional_images_edited"]
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror("추가 이미지", str(exc))

    def refresh_data(self, silent: bool = False) -> None:
        try:
            info = inspect_inputs(
                include_option_menu_images=self.apply_option_images.get(),
                include_additional_images=self.apply_additional_images.get(),
            )
            option_status = f"적용 {info['option_menu_image_count']:,}" if info["option_menu_images_enabled"] else "제외"
            additional_status = f"적용 {info['additional_image_count']:,}" if info["additional_images_enabled"] else "제외"
            self.counts.set(f"대사 override {info['override_count']:,} / 시스템 override {info['system_override_count']:,}·draft {info['system_draft_count']:,} / 아이템 override {info['item_override_count']:,}·draft {info['item_draft_count']:,} / 인물 reviewed {info['cast_person_reviewed_count']:,} / 몬스터 reviewed {info['monster_reviewed_count']:,} / 메뉴 이미지 {option_status} / 추가 이미지 {additional_status}")
            if not self.font.get(): self.font.set(info["font"])
            self.refresh_cache_status(silent=True)
        except Exception as exc:
            self.counts.set(f"패치 데이터 오류: {exc}")
            if not silent: messagebox.showerror("패치 데이터", str(exc))

    def refresh_cache_status(self, silent: bool = False) -> None:
        if not self.apply_additional_images.get():
            self.cache_state.set("이미지 캐시: 사용 안 함")
            return
        raw_iso = self.iso.get().strip()
        if not raw_iso:
            self.cache_state.set("이미지 캐시: 원본 ISO 선택 필요")
            return
        try:
            info = inspect_inputs(include_option_menu_images=False, include_additional_images=True)
            status = cache_status(Path(raw_iso), info["paths"]["additional_images"])
            self.cache_state.set(f"이미지 캐시: {status['message']}")
        except Exception as exc:
            self.cache_state.set(f"이미지 캐시: 확인 오류 ({exc})")
            if not silent:
                messagebox.showerror("이미지 캐시", str(exc))

    def start_cache_refresh(self) -> None:
        if self.running:
            return
        if not self.apply_additional_images.get():
            messagebox.showwarning("이미지 캐시", "추가 이미지 적용을 먼저 선택해 주세요.")
            return
        raw_iso = self.iso.get().strip()
        if not raw_iso:
            messagebox.showwarning("이미지 캐시", "원본 ISO를 선택해 주세요.")
            return
        try:
            info = inspect_inputs(include_option_menu_images=False, include_additional_images=True)
            workspace = info["paths"]["additional_images"]
        except Exception as exc:
            messagebox.showerror("이미지 캐시", str(exc))
            return
        self.running = True
        self.result.set("")
        self.cache_state.set("이미지 캐시: 갱신 중")
        self._set_buttons(False)
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self._append(f"이미지 캐시 갱신 시작: {raw_iso}\n")
        threading.Thread(
            target=self._cache_worker,
            args=(Path(raw_iso), workspace),
            daemon=True,
        ).start()

    def _cache_worker(self, iso: Path, workspace: Path) -> None:
        try:
            def report(resource_id: str, position: int, total: int) -> None:
                self.events.put(("cache_progress", resource_id, position, total))

            def report_plan(plan: dict) -> None:
                self.events.put(("cache_plan", plan))

            result = precompile_additional_images(
                iso, workspace, progress=report, planned=report_plan)
            self.events.put(("cache_success", result))
        except Exception as exc:
            self.events.put(("cache_error", str(exc)))

    def _save_pending(self) -> bool:
        self.app.apply_edit(silent=True)
        self.app.cast_editor._commit_selected()
        self.app.item_editor._commit_selected()
        self.app.system_editor._commit_selected()
        if self.app.dialogue_dirty or self.app.cast_editor.dirty or self.app.item_editor.dirty or self.app.system_editor.dirty:
            if not messagebox.askyesno("미저장 번역", "저장하지 않은 번역 변경이 있습니다. 지금 저장하고 빌드하시겠습니까?"): return False
            if self.app.dialogue_dirty: self.app.save_workspace()
            if self.app.cast_editor.dirty: self.app.cast_editor.save()
            if self.app.item_editor.dirty: self.app.item_editor.save()
            if self.app.system_editor.dirty: self.app.system_editor.save()
        return True

    def start(self, mode: str) -> None:
        if self.running or not self._save_pending(): return
        iso = Path(self.iso.get().strip()); output = Path(self.output.get().strip()) if self.output.get().strip() else None; font = Path(self.font.get().strip()) if self.font.get().strip() else None
        if not self.iso.get().strip(): messagebox.showwarning("패치 빌드", "원본 ISO를 선택해 주세요."); return
        overwrite = False
        if mode == "build":
            if output is None: messagebox.showwarning("패치 빌드", "출력 ISO 경로를 선택해 주세요."); return
            if output.exists():
                if not messagebox.askyesno("출력 파일", f"기존 파일을 덮어쓰시겠습니까?\n{output}"): return
                overwrite = True
        self.running = True; self.result.set(""); self._set_buttons(False); self.progress.start(10); self._append(f"{mode} 시작: {iso}\n")
        include_option_images = self.apply_option_images.get()
        include_additional_images = self.apply_additional_images.get()
        threading.Thread(
            target=self._worker,
            args=(mode, iso, output, font, overwrite, include_option_images, include_additional_images),
            daemon=True,
        ).start()

    def _worker(self, mode, iso, output, font, overwrite,
                include_option_images, include_additional_images) -> None:
        try:
            result = run_build(
                mode, iso, output, font, overwrite=overwrite,
                include_option_menu_images=include_option_images,
                include_additional_images=include_additional_images,
            )
            self.events.put(("success", mode, result))
        except Exception as exc: self.events.put(("error", str(exc)))

    def _poll(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "success":
                    _, mode, data = event; summary = data["summary"]
                    self._append(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
                    if mode == "build":
                        iso = data["iso"]; self.result.set(f"완료: SHA-256 {iso['output_iso_sha256']}"); self._append(f"출력: {iso['path']}\n")
                    else: self.result.set("사전 검증 완료")
                    self._finish()
                elif event[0] == "cache_progress":
                    _, resource_id, position, total = event
                    self.progress.configure(maximum=max(total, 1), value=position - 1)
                    self.cache_state.set(f"이미지 캐시: 갱신 중 ({position}/{total}) {resource_id}")
                    self._append(f"[{position}/{total}] {resource_id}\n")
                elif event[0] == "cache_plan":
                    plan = event[1]
                    actual = plan["rebuild_count"] + plan["new_count"]
                    self.progress.configure(maximum=max(actual, 1), value=0)
                    self._append(
                        "캐시 갱신 계획: "
                        f"재사용 {plan['reuse_count']} / 재압축 {plan['rebuild_count']} / "
                        f"신규 {plan['new_count']} / 제거 {plan['remove_count']}\n")
                    if plan["rebuild_resources"]:
                        self._append("재압축 대상: " + ", ".join(plan["rebuild_resources"]) + "\n")
                    if plan["new_resources"]:
                        self._append("신규 대상: " + ", ".join(plan["new_resources"]) + "\n")
                elif event[0] == "cache_success":
                    data = event[1]
                    self.progress.configure(value=self.progress.cget("maximum"))
                    self._append(json.dumps({
                        "resource_count": data["resource_count"],
                        "reuse_count": data["reuse_count"],
                        "rebuild_count": data["rebuild_count"],
                        "new_count": data["new_count"],
                        "remove_count": data["remove_count"],
                        "cache_bytes": data["cache_bytes"],
                        "elapsed_seconds": data["elapsed_seconds"],
                    }, ensure_ascii=False, indent=2) + "\n")
                    if data["changed"]:
                        self.result.set(
                            f"이미지 캐시 갱신 완료: 재사용 {data['reuse_count']} / "
                            f"재압축 {data['rebuild_count'] + data['new_count']}")
                    else:
                        self.result.set("이미지 캐시가 이미 최신입니다")
                    self._finish()
                    message = ("추가 이미지 캐시 갱신이 완료되었습니다."
                               if data["changed"] else "이미지 캐시가 이미 최신입니다.")
                    messagebox.showinfo("이미지 캐시", message)
                elif event[0] == "cache_error":
                    self._append("이미지 캐시 갱신 오류: " + event[1] + "\n")
                    self.result.set("이미지 캐시 갱신 실패")
                    self._finish()
                    messagebox.showerror("이미지 캐시 갱신 실패", event[1])
                else: self._append("오류: " + event[1] + "\n"); self.result.set("실패"); self._finish(); messagebox.showerror("패치 빌드 실패", event[1])
        except queue.Empty: pass
        self.after(100, self._poll)

    def _finish(self) -> None:
        self.running = False
        self.progress.stop()
        self.progress.configure(mode="indeterminate", value=0)
        self._set_buttons(True)
        self.refresh_data(silent=True)

    def _set_buttons(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in (self.refresh_button, self.option_images_button, self.additional_images_button, self.cache_refresh_button, self.preflight_button, self.build_button): button.configure(state=state)
        for check in (self.option_images_check, self.additional_images_check): check.configure(state=state)

    def _append(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL); self.log.insert(tk.END, text); self.log.see(tk.END); self.log.configure(state=tk.DISABLED)


def main() -> int:
    default_workspace, default_cast, default_items, default_system, default_catalog = default_config_paths()
    if len(sys.argv) > 1:
        initial = Path(sys.argv[1])
    else:
        initial = default_workspace if default_workspace.exists() else (default_catalog if default_catalog.exists() else None)
    app = DialogueViewer(initial, default_cast, default_items, default_system)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
