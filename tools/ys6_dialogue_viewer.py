#!/usr/bin/env python3
"""GUI viewer for Ys VI dialogue_catalog.json."""

from __future__ import annotations

import json
import csv
import hashlib
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
except ModuleNotFoundError:
    from scripts.ys6_translation_workspace import normalize_editor_translation
    from scripts.ys6_patch_builder import find_default_font, inspect_inputs, run_build


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
            for key in ("text", "source_text", "translation", "map_group", "map_id", "xso_name", "iso_path")
        ).casefold()
        if needle and needle not in haystack:
            continue
        result.append(record)
    return result


def default_config_paths(script_path: Path | None = None) -> tuple[Path, Path, Path]:
    config_dir = (script_path or Path(__file__)).resolve().parent / "config"
    return (
        config_dir / "dialogue-translations.json",
        config_dir / "cast-names.json",
        config_dir / "dialogue-catalog.json",
    )


class DialogueViewer(tk.Tk):
    def __init__(self, initial_path: Path | None = None, cast_path: Path | None = None) -> None:
        super().__init__()
        self.title("Ys VI 대사 뷰어")
        self.geometry("1280x760")
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

    def _build_ui(self) -> None:
        tabs = ttk.Notebook(self)
        tabs.pack(fill=tk.BOTH, expand=True)
        dialogue_tab = ttk.Frame(tabs)
        cast_tab = CastNameEditor(tabs)
        self.cast_editor = cast_tab
        build_tab = PatchBuildEditor(tabs, self)
        self.build_editor = build_tab
        tabs.add(dialogue_tab, text="대사")
        tabs.add(cast_tab, text="인물명")
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
        self.status = tk.StringVar(value="카탈로그를 열어 주세요.")
        ttk.Label(top, textvariable=self.status).pack(side=tk.RIGHT)

        pane = ttk.Panedwindow(dialogue_tab, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        table_frame = ttk.Frame(pane)
        detail_frame = ttk.Frame(pane)
        pane.add(table_frame, weight=3)
        pane.add(detail_frame, weight=2)
        columns = ("map", "file", "index", "roles", "status", "text", "translation")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
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
        ttk.Button(editor, text="현재 항목 반영", command=self.apply_edit).grid(row=2, column=3, sticky="e", pady=(6, 0))
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
        workflow_status = self.workflow_status.get()
        if workflow_status == "dialogue":
            self.filtered = [record for record in self.filtered if "dialogue" in record.get("roles", [])]
        elif workflow_status != "전체":
            self.filtered = [record for record in self.filtered if record.get("status") == workflow_status]
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
        self.message = tk.StringVar(value="인물명 작업공간을 열어 주세요."); ttk.Label(bar, textvariable=self.message).pack(side=tk.RIGHT)

        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL); pane.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left, right = ttk.Frame(pane), ttk.Frame(pane, padding=(8, 0, 0, 0)); pane.add(left, weight=3); pane.add(right, weight=2)
        columns = ("identifier", "source", "translation", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings")
        for col, label, width in zip(columns, ("ID", "일본어 원문", "한국어 번역", "상태"), (110, 180, 180, 100)):
            self.tree.heading(col, text=label); self.tree.column(col, width=width)
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y); self.tree.bind("<<TreeviewSelect>>", self.show)

        self.info = tk.StringVar(); ttk.Label(right, textvariable=self.info, justify=tk.LEFT).pack(fill=tk.X)
        ttk.Label(right, text="번역").pack(anchor="w", pady=(10, 0)); self.translation = ttk.Entry(right, font=("맑은 고딕", 11)); self.translation.pack(fill=tk.X)
        ttk.Label(right, text="상태").pack(anchor="w", pady=(8, 0)); self.edit_status = tk.StringVar(value="untranslated"); ttk.Combobox(right, textvariable=self.edit_status, state="readonly", values=CAST_STATUSES).pack(fill=tk.X)
        ttk.Label(right, text="메모").pack(anchor="w", pady=(8, 0)); self.notes = tk.Text(right, height=5, wrap=tk.WORD, font=("맑은 고딕", 10)); self.notes.pack(fill=tk.X)
        ttk.Button(right, text="현재 항목 반영", command=self.apply_edit).pack(anchor="e", pady=(8, 0))

    def choose(self) -> None:
        if self.dirty and not messagebox.askyesno("미저장 변경", "저장하지 않은 변경을 버리고 다른 파일을 여시겠습니까?"): return
        selected = filedialog.askopenfilename(title="인물명 작업공간 열기", filetypes=[("JSON", "*.json")])
        if selected: self.open(Path(selected))

    def open(self, path: Path) -> None:
        try: self.workspace = load_cast_workspace(path)
        except Exception as exc: messagebox.showerror("열기 실패", str(exc)); return
        self.path = path; self.dirty = False; self.refresh(); self.message.set(f"{path.name}: {len(self.workspace['records']):,}개")

    def _commit_selected(self) -> None:
        if not self._selected_identifier: return
        row = next((r for r in self.workspace["records"] if r["identifier"] == self._selected_identifier), None)
        if row is None: return
        values = (self.translation.get(), self.edit_status.get(), self.notes.get("1.0", "end-1c"))
        if values != (row.get("translation", ""), row.get("status", "untranslated"), row.get("notes", "")):
            row["translation"], row["status"], row["notes"] = values; self.dirty = True

    def apply_edit(self) -> None:
        if not self._selected_identifier: messagebox.showwarning("편집", "항목을 선택해 주세요."); return
        self._commit_selected(); self.refresh(select=self._selected_identifier)

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

    def refresh(self, select: str | None = None) -> None:
        needle = self.query.get().casefold().strip(); status = self.filter_status.get()
        rows = self.workspace.get("records", [])
        if status == "미번역": rows = [r for r in rows if r.get("status") == "untranslated"]
        elif status == "검수 완료": rows = [r for r in rows if r.get("status") == "reviewed"]
        elif status != "전체": rows = [r for r in rows if r.get("status") == status]
        self.filtered = [r for r in rows if not needle or needle in " ".join(str(r.get(k, "")) for k in ("identifier", "source", "translation", "notes")).casefold()]
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.filtered): self.tree.insert("", tk.END, iid=str(i), values=(row["identifier"], row["source"], row.get("translation", ""), row.get("status", "")))
        self.message.set(f"{len(self.filtered):,} / {len(self.workspace.get('records', [])):,}개")
        if select:
            for i, row in enumerate(self.filtered):
                if row["identifier"] == select: self.tree.selection_set(str(i)); self.tree.see(str(i)); self.show(); break

    def show(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected: return
        next_row = self.filtered[int(selected[0])]
        if self._selected_identifier and self._selected_identifier != next_row["identifier"]: self._commit_selected()
        self._selected_identifier = next_row["identifier"]
        self.info.set(f"ID: {next_row['identifier']}\n원문: {next_row['source']}\n식별자 오프셋: 0x{next_row['identifier_offset']:X}\n이름 오프셋: 0x{next_row['name_offset']:X}\n원문 HEX: {next_row['source_raw_hex']}\nSHA-256: {next_row['source_sha256']}")
        self.translation.delete(0, tk.END); self.translation.insert(0, next_row.get("translation", "")); self.edit_status.set(next_row.get("status", "untranslated")); self.notes.delete("1.0", tk.END); self.notes.insert("1.0", next_row.get("notes", ""))


class PatchBuildEditor(ttk.Frame):
    def __init__(self, parent, app: DialogueViewer) -> None:
        super().__init__(parent, padding=12); self.app = app; self.events = queue.Queue(); self.running = False
        self.iso = tk.StringVar(); self.output = tk.StringVar(); self.font = tk.StringVar(value=str(find_default_font() or ""))
        self.counts = tk.StringVar(value="패치 데이터를 확인하지 않았습니다."); self.result = tk.StringVar()
        self._build_ui(); self.after(100, self._poll); self.refresh_data(silent=True)

    def _build_ui(self) -> None:
        form = ttk.Frame(self); form.pack(fill=tk.X)
        for row, (label, variable, command) in enumerate((("원본 ISO", self.iso, self.choose_iso), ("출력 ISO", self.output, self.choose_output), ("글꼴", self.font, self.choose_font))):
            ttk.Label(form, text=label, width=10).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Button(form, text="찾아보기", command=command).grid(row=row, column=2, padx=(6, 0), pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(self, textvariable=self.counts).pack(anchor="w", pady=(10, 4))
        buttons = ttk.Frame(self); buttons.pack(fill=tk.X)
        self.refresh_button = ttk.Button(buttons, text="데이터 다시 읽기", command=self.refresh_data); self.refresh_button.pack(side=tk.LEFT)
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

    def choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(title="패치 ISO 저장", defaultextension=".iso", initialfile="Ys VI - Korean Patched.iso", filetypes=[("ISO", "*.iso")])
        if selected: self.output.set(selected)

    def choose_font(self) -> None:
        selected = filedialog.askopenfilename(title="굴림 글꼴 선택", filetypes=[("TrueType", "*.ttc *.ttf"), ("모든 파일", "*.*")])
        if selected: self.font.set(selected)

    def refresh_data(self, silent: bool = False) -> None:
        try:
            info = inspect_inputs(); self.counts.set(f"대사 override {info['override_count']:,}개 / draft {info['draft_count']:,}개(제외) / 인물명 reviewed {info['cast_reviewed_count']:,}개")
            if not self.font.get(): self.font.set(info["font"])
        except Exception as exc:
            self.counts.set(f"패치 데이터 오류: {exc}")
            if not silent: messagebox.showerror("패치 데이터", str(exc))

    def _save_pending(self) -> bool:
        self.app.apply_edit(silent=True)
        self.app.cast_editor._commit_selected()
        if self.app.dialogue_dirty or self.app.cast_editor.dirty:
            if not messagebox.askyesno("미저장 번역", "저장하지 않은 번역 변경이 있습니다. 지금 저장하고 빌드하시겠습니까?"): return False
            if self.app.dialogue_dirty: self.app.save_workspace()
            if self.app.cast_editor.dirty: self.app.cast_editor.save()
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
        threading.Thread(target=self._worker, args=(mode, iso, output, font, overwrite), daemon=True).start()

    def _worker(self, mode, iso, output, font, overwrite) -> None:
        try:
            result = run_build(mode, iso, output, font, overwrite=overwrite)
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
                else: self._append("오류: " + event[1] + "\n"); self.result.set("실패"); self._finish(); messagebox.showerror("패치 빌드 실패", event[1])
        except queue.Empty: pass
        self.after(100, self._poll)

    def _finish(self) -> None:
        self.running = False; self.progress.stop(); self._set_buttons(True); self.refresh_data(silent=True)

    def _set_buttons(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in (self.refresh_button, self.preflight_button, self.build_button): button.configure(state=state)

    def _append(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL); self.log.insert(tk.END, text); self.log.see(tk.END); self.log.configure(state=tk.DISABLED)


def main() -> int:
    default_workspace, default_cast, default_catalog = default_config_paths()
    if len(sys.argv) > 1:
        initial = Path(sys.argv[1])
    else:
        initial = default_workspace if default_workspace.exists() else (default_catalog if default_catalog.exists() else None)
    app = DialogueViewer(initial, default_cast)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
