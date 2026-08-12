#!/usr/bin/env python3
"""GUI viewer for Ys VI dialogue_catalog.json."""

from __future__ import annotations

import json
import csv
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


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


class DialogueViewer(tk.Tk):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        self.title("Ys VI 대사 뷰어")
        self.geometry("1280x760")
        self.records: list[dict] = []
        self.filtered: list[dict] = []
        self.workspace_path: Path | None = None
        self._build_ui()
        if initial_path:
            self.open_catalog(initial_path)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
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
        self.status = tk.StringVar(value="카탈로그를 열어 주세요.")
        ttk.Label(top, textvariable=self.status).pack(side=tk.RIGHT)

        pane = ttk.Panedwindow(self, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        table_frame = ttk.Frame(pane)
        detail_frame = ttk.Frame(pane)
        pane.add(table_frame, weight=3)
        pane.add(detail_frame, weight=2)
        columns = ("map", "file", "index", "roles", "text", "translation")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for column, label, width in zip(columns, ("맵", "XSO", "인덱스", "역할", "원문", "번역"), (120, 150, 55, 150, 390, 390)):
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
        ttk.Combobox(editor, textvariable=self.translation_status, state="readonly", values=("untranslated", "draft", "reviewed", "excluded", "conflict", "orphaned"), width=16).grid(row=1, column=1, sticky="w", pady=(4, 0))
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
        try:
            data = json.loads(Path(selected).read_text(encoding="utf-8-sig"))
            if not isinstance(data.get("records"), list): raise ValueError("지원하는 번역 작업공간 형식이 아닙니다")
            self.records = data["records"]; self.workspace_path = Path(selected)
            roles = sorted({role for record in self.records for role in record.get("roles", [])})
            self.role_box["values"] = [""] + roles; self.role.set(""); self.title(f"Ys VI 번역 편집기 - {self.workspace_path.name}"); self.refresh()
        except Exception as exc: messagebox.showerror("열기 실패", str(exc))

    def save_workspace(self) -> None:
        if self.workspace_path is None: messagebox.showwarning("저장", "번역 작업공간을 먼저 열어 주세요."); return
        self.apply_edit(silent=True)
        self.workspace_path.write_text(json.dumps({"schema_version": 1, "records": self.records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        record["translation"] = self.translation.get("1.0", "end-1c")
        record["status"] = self.translation_status.get()
        record["notes"] = self.notes.get()
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
        self.title(f"Ys VI 대사 뷰어 - {path.name}")
        self.refresh()

    def refresh(self) -> None:
        self.filtered = filter_records(self.records, self.query.get(), self.role.get())
        self.tree.delete(*self.tree.get_children())
        for index, record in enumerate(self.filtered):
            text = record.get("text", record.get("source_text", "")).replace("\\n", " / ")
            self.tree.insert("", tk.END, iid=str(index), values=(
                f"{record.get('map_group','')}/{record.get('map_id','')}", record.get("xso_name", ""),
                record.get("string_index", ""), ", ".join(record.get("roles", [])), text,
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


def main() -> int:
    if len(sys.argv) > 1:
        initial = Path(sys.argv[1])
    else:
        default_catalog = (
            Path(__file__).resolve().parents[1]
            / ".work"
            / "ys6-full-dialogue"
            / "catalog"
            / "dialogue_catalog.json"
        )
        initial = default_catalog if default_catalog.exists() else None
    app = DialogueViewer(initial)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
