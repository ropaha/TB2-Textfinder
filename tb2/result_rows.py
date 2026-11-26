"""Consistent result row styling for the TB2 tools."""
import tkinter.font as tkfont
from tkinter import ttk


def configure_result_rows(tree, *, total=False):
    tree.tag_configure("row_even", background="#ffffff")
    tree.tag_configure("row_odd", background="#f0f0f0")
    if total:
        font = ttk.Style(tree).lookup("Treeview", "font") or "TkDefaultFont"
        tree._total_row_font = tkfont.Font(root=tree, font=font)
        tree._total_row_font.configure(weight="bold")
        tree.tag_configure("row_total", background="#d6e3f0", font=tree._total_row_font)


def row_tags(index, *extra):
    return ("row_odd" if index % 2 else "row_even", *extra)
