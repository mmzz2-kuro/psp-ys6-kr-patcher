#!/usr/bin/env python3
"""Headless regression checks for CastNameEditor selection-state handling."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ys6_dialogue_viewer import CastNameEditor


class Var:
    def __init__(self, value=""): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class Entry(Var):
    def delete(self, *_args): self.value = ""
    def insert(self, _where, value): self.value = value


class Text(Entry):
    def get(self, *_args): return self.value


class Tree:
    def __init__(self): self.rows = {}; self.selected = (); self.focused = None
    def selection(self): return self.selected
    def selection_set(self, values):
        if isinstance(values, str): values = (values,)
        self.selected = tuple(values)
    def get_children(self): return tuple(self.rows)
    def delete(self, *items):
        for item in items: self.rows.pop(item, None)
        self.selected = tuple(item for item in self.selected if item in self.rows)
    def insert(self, _parent, _where, iid, values): self.rows[iid] = values
    def focus(self, item): self.focused = item
    def see(self, _item): pass


def editor_for(rows: list[dict], category: str = "전체", status: str = "전체") -> CastNameEditor:
    editor = object.__new__(CastNameEditor)
    editor.workspace = {"schema_version": 1, "records": copy.deepcopy(rows)}
    editor.filtered = []
    editor.dirty = False
    editor._selected_identifier = None
    editor.query = Var("")
    editor.filter_status = Var(status)
    editor.category = Var(category)
    editor.message = Var("")
    editor.info = Var("")
    editor.translation = Entry("")
    editor.edit_status = Var("untranslated")
    editor.notes = Text("")
    editor.tree = Tree()
    editor.refresh(commit_current=False)
    return editor


def select(editor: CastNameEditor, identifier: str) -> None:
    index = next(i for i, row in enumerate(editor.filtered) if row["identifier"] == identifier)
    editor.tree.selection_set(str(index))
    editor.show()


def row(editor: CastNameEditor, identifier: str) -> dict:
    return next(value for value in editor.workspace["records"] if value["identifier"] == identifier)


def run(workspace_path: Path) -> dict:
    document = json.loads(workspace_path.read_text(encoding="utf-8-sig"))
    records = document["records"]
    cases = {}
    for label, identifiers in {
        "person": ("CAST_C920", "CAST_C930"),
        "monster": ("CAST_M450", "CAST_M460"),
    }.items():
        sample = [next(copy.deepcopy(value) for value in records if value["identifier"] == identifier)
                  for identifier in identifiers]
        editor = editor_for(sample)
        untouched = copy.deepcopy(row(editor, identifiers[1]))
        select(editor, identifiers[0])
        editor.review_selected()
        select(editor, identifiers[1])
        cases[label + "_single"] = (
            row(editor, identifiers[0])["status"] == "reviewed"
            and row(editor, identifiers[1]) == untouched)

        sample = [next(copy.deepcopy(value) for value in records if value["identifier"] == identifier)
                  for identifier in identifiers]
        editor = editor_for(sample, status="미번역")
        select(editor, identifiers[0])
        editor.review_selected()
        select(editor, identifiers[1])
        cases[label + "_filtered"] = (
            row(editor, identifiers[0])["status"] == "reviewed"
            and editor._selected_identifier == identifiers[1])

        sample = [next(copy.deepcopy(value) for value in records if value["identifier"] == identifier)
                  for identifier in identifiers]
        editor = editor_for(sample)
        editor.tree.selection_set(("0", "1"))
        editor.show()
        editor.review_selected()
        cases[label + "_multi"] = all(
            row(editor, identifier)["status"] == "reviewed" for identifier in identifiers)

    editor = editor_for(records[:2])
    editor._selected_identifier = records[0]["identifier"]
    editor.translation.value = "stale"
    editor.edit_status.value = "reviewed"
    editor.open(workspace_path)
    cases["open_resets_selection"] = (
        editor._selected_identifier is None
        and editor.translation.get() == ""
        and editor.edit_status.get() == "untranslated")

    search_rows = [copy.deepcopy(next(value for value in records if value["identifier"] == key))
                   for key in ("CAST_C920", "CAST_C930")]
    editor = editor_for(search_rows)
    editor.query.set("CAST_C920")
    editor.refresh()
    select(editor, "CAST_C920")
    editor.review_selected()
    editor.query.set("")
    editor.refresh()
    cases["search_filter"] = row(editor, "CAST_C920")["status"] == "reviewed"

    category_rows = [copy.deepcopy(next(value for value in records if value["identifier"] == key))
                     for key in ("CAST_C920", "CAST_M450")]
    editor = editor_for(category_rows, category="인물")
    select(editor, "CAST_C920")
    editor.review_selected()
    editor.category.set("몬스터")
    editor.refresh()
    select(editor, "CAST_M450")
    editor.review_selected()
    cases["category_switch"] = all(
        row(editor, identifier)["status"] == "reviewed"
        for identifier in ("CAST_C920", "CAST_M450"))

    if not all(cases.values()):
        raise AssertionError(cases)
    return {"valid": True, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(run(Path("tools/config/cast-names.json")), ensure_ascii=False, indent=2))
