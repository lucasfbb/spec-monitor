"""Renderização de markdown e diffs para a UI."""

import difflib

import markdown as md_lib


def render_markdown(content: str) -> str:
    return md_lib.markdown(content, extensions=["tables", "fenced_code", "sane_lists"])


def unified_diff_lines(old: str, new: str, old_label: str, new_label: str) -> list[dict]:
    """Linhas de diff unificado já classificadas para o template."""
    lines = []
    for line in difflib.unified_diff(
        old.splitlines(), new.splitlines(), fromfile=old_label, tofile=new_label, lineterm=""
    ):
        if line.startswith("+++") or line.startswith("---"):
            kind = "meta"
        elif line.startswith("@@"):
            kind = "hunk"
        elif line.startswith("+"):
            kind = "add"
        elif line.startswith("-"):
            kind = "del"
        else:
            kind = "ctx"
        lines.append({"kind": kind, "text": line})
    return lines
