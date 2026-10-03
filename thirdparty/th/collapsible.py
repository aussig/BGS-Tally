"""
Expanded and collapsed views of a plugin, swapped by `.toggle()`.

The caller fills `.expanded` and `.collapsed` and grids `hide_button()` and `show_button()` wherever each
layout needs them. `.toggle()` runs `on_toggle` after the swap, then refits EDMC's window.
"""
import tkinter as tk
from typing import Callable

from . import Frame, Button, fit_window
from .tooltip import Tooltip

GLYPH_HIDE:str = "\U0001F648" # see-no-evil monkey
GLYPH_SHOW:str = "\U0001F441" # eye

class Collapsible:
    """ Swaps between an expanded and a collapsed view of a plugin, refitting the window """
    def __init__(self, parent:tk.Widget, hidden:bool = False, on_toggle:Callable[[bool], None]|None = None) -> None:
        self.hidden:bool = hidden
        self._on_toggle:Callable[[bool], None]|None = on_toggle
        self.expanded:Frame = Frame(parent)
        self.collapsed:Frame = Frame(parent)
        self._show_current()

    def hide_button(self, master:tk.Widget, tooltip:str = "", **kw) -> Button:
        """ A button that collapses the view; the caller grids it """
        return self._button(master, GLYPH_HIDE, tooltip, **kw)

    def show_button(self, master:tk.Widget, tooltip:str = "", **kw) -> Button:
        """ A button that expands the view; the caller grids it """
        return self._button(master, GLYPH_SHOW, tooltip, **kw)

    def _button(self, master:tk.Widget, glyph:str, tooltip:str, **kw) -> Button:
        btn:Button = Button(master, text=glyph, width=3, command=self.toggle, **kw)
        if tooltip: Tooltip(btn, text=tooltip)
        return btn

    def toggle(self, hidden:bool|None = None) -> None:
        """ Swap views, run on_toggle, then refit so the window measures the final layout """
        self.expanded.grid_forget()
        self.collapsed.grid_forget()
        self.hidden = not self.hidden if hidden is None else hidden
        self._show_current()
        if self._on_toggle: self._on_toggle(self.hidden)
        fit_window(self.expanded)

    def _show_current(self) -> None:
        if self.hidden:
            self.collapsed.grid(row=0, column=0, sticky=tk.EW)
            return

        self.expanded.grid(row=0, column=0, sticky=tk.NSEW)
