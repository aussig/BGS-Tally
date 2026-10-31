""" Expanded and collapsed views of a plugin with default hide/show (and optional move) buttons. """
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable

from config import config # type: ignore

from . import Frame, Button, fit_window
from .tooltip import Tooltip
from .pluginslot import PluginSlot

GLYPH_HIDE:str = "\U0001F648" # see-no-evil monkey
GLYPH_SHOW:str = "\U0001F441" # eye

class Collapsible:
    """ Swaps between an expanded and a collapsed view of a plugin, refitting the window """
    def __init__(self, parent:tk.Widget, hidden:bool = False, movable:bool = False,
                 on_toggle:Callable[[bool], None]|None = None) -> None:
        here:Path = Path(__file__).resolve()
        folder:str = next((p.name for p in here.parents if (p / "load.py").exists()), here.parents[1].name)
        self.key:str = f"th_{folder}"

        self.hidden:bool = config.get_bool(f"{self.key}_hidden", default=hidden)
        self._on_toggle:Callable[[bool], None]|None = on_toggle
        self.expanded:Frame = Frame(parent)
        self.collapsed:Frame = Frame(parent)

        # Column 99 keeps controls rightmost whatever columns the plugin uses; empty columns have no width
        self._buttons:dict[str, tuple[Button, Tooltip]] = {}
        self._add("hide", self.expanded, GLYPH_HIDE, "Hide panel", self.toggle, 99, tk.NE)
        if movable:
            self.slot:PluginSlot = PluginSlot(parent, f"{self.key}_slot")
            self._add("up", self.collapsed, "▲", "Move panel up", lambda: self.slot.move(-1), 97, tk.E)
            self._add("down", self.collapsed, "▼", "Move panel down", lambda: self.slot.move(1), 98, tk.E)
        self._add("show", self.collapsed, GLYPH_SHOW, "Show panel", self.toggle, 99, tk.E)

        self._show_current()

    def button(self, name:str, text:str|None = None, tooltip:str|None = None, **grid) -> Button:
        """ Change a default button's text, tooltip or grid placement """
        btn, tip = self._buttons[name]
        if text is not None:
            btn.configure(text=text)
            # Drop the glyph width: ttk falls back to its style's minimum, as a plain th.Button would
            btn.obj.configure(width='' if isinstance(btn.obj, ttk.Button) else 0)
            btn.alt.configure(width=0)
        if tooltip is not None: tip.text = tooltip
        # Full options via grid(), not grid_configure(), so the theme's alternate widget is re-registered too
        if grid: btn.grid(**{**(getattr(btn, '_last_gridopts', None) or {}), **grid})
        # Gridded in_ a container created later, the button would be stacked beneath it and hidden
        if 'in_' in grid: btn.lift()
        return btn

    def _add(self, name:str, master:Frame, text:str, tooltip:str, command:Callable, column:int, sticky:str) -> None:
        btn:Button = Button(master, text=text, width=3, command=command)
        btn.grid(row=0, column=column, sticky=sticky)
        self._buttons[name] = (btn, Tooltip(btn, text=tooltip))

    def toggle(self, hidden:bool|None = None) -> None:
        """ Swap views, save the state, run on_toggle, then refit so the window measures the final layout """
        self.expanded.grid_forget()
        self.collapsed.grid_forget()
        self.hidden = not self.hidden if hidden is None else hidden
        config.set(f"{self.key}_hidden", self.hidden)
        self._show_current()
        if self._on_toggle: self._on_toggle(self.hidden)
        fit_window(self.expanded)

    def _show_current(self) -> None:
        if self.hidden:
            self.collapsed.grid(row=0, column=0, sticky=tk.EW)
            return

        self.expanded.grid(row=0, column=0, sticky=tk.NSEW)
