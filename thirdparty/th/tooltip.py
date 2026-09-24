# General purpose 'tooltip' routines -- Tooltip/TooltipBase are aware of th.Base's light/dark
# widget pairs (binding to both halves); TreeTooltip is a separate helper for Treeview widgets.

from ..debug import catch_exceptions
from ..tkrichtext import RichLabel
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

DELAY: int = 500 # Delay before tooltip appears in ms

class TooltipBase:

    def __init__(self, button):
        self.button = button.obj if hasattr(button, 'obj') else button
        self.alt = None
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        # add='+' so this layers on top of whatever the widget already binds for these
        # sequences (e.g. Button's hover-highlight, Autocompleter's mouse_leave) instead of
        # silently replacing it -- plain bind() overwrites any prior handler for the sequence.
        self._id1 = self.button.bind("<Enter>", self.enter, add='+')
        self._id2 = self.button.bind("<Leave>", self.leave, add='+')
        self._id3 = self.button.bind("<ButtonPress>", self.leave, add='+')
        if hasattr(button, 'alt'):
            self.alt = button.alt
            self._id4 = self.alt.bind("<Enter>", self.enter, add='+')
            self._id5 = self.alt.bind("<Leave>", self.leave, add='+')
            self._id6 = self.alt.bind("<ButtonPress>", self.leave, add='+')

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.button.after(DELAY, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.button.after_cancel(id)

    def showtip(self):
        if self.tipwindow:
            return
        # The tip window must be completely outside the button;
        # otherwise when the mouse enters the tip window we get
        # a leave event and it disappears, and then we get an enter
        # event and it reappears, and so on forever :-(
        if self.alt is not None and self.alt.winfo_viewable():
            x = self.alt.winfo_rootx() + 20
            y = self.alt.winfo_rooty() + self.alt.winfo_height() + 1
            self.tipwindow = tw = tk.Toplevel(self.button)
        else:
            x = self.button.winfo_rootx() + 20
            y = self.button.winfo_rooty() + self.button.winfo_height() + 1
            self.tipwindow = tw = tk.Toplevel(self.button)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        self.showcontents()

    @catch_exceptions
    def showcontents(self, **kwargs):
        if 'markdown' in kwargs:
            label:tk.Label|RichLabel = RichLabel(self.tipwindow, markdown=kwargs['markdown'],
                                                 background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        elif 'html' in kwargs:
            label:tk.Label|RichLabel = RichLabel(self.tipwindow, html=kwargs['html'],
                                                 background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        else:
            label:tk.Label|RichLabel = tk.Label(self.tipwindow, text=kwargs['text'], justify=tk.LEFT,
                                                background="#ffffe0", relief=tk.SOLID, borderwidth=1)

        label.pack()

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class Tooltip(TooltipBase):

    def __init__(self, button, text:str='', **kwargs):
        TooltipBase.__init__(self, button)
        self.set_text(text, **kwargs)

    def set_text(self, text:str='', **kwargs) -> None:
        """ Update the tooltip's content without re-binding to the widget. """
        self.args = kwargs
        if text != '':
            self.args['text'] = text

    def showcontents(self, **kwargs):
        super().showcontents(**{**self.args, **kwargs})


class TreeTooltip:
    """Simple tooltip helper for Treeview widgets."""

    def __init__(self, tree:ttk.Treeview) -> None:
        self._tree = tree
        self._tip: Optional[tk.Toplevel] = None
        self._cell_texts: dict[Tuple[str, str], str] = {}
        self._heading_texts: dict[str, str] = {}
        self._current_key: Optional[Tuple[str, str]] = None

        tree.bind("<Motion>", self._on_motion, add="+")
        tree.bind("<Leave>", self._hide_tip, add="+")
        tree.bind("<ButtonPress>", self._hide_tip, add="+")

    def clear(self) -> None:
        self._cell_texts.clear()
        self._current_key = None
        self._hide_tip()

    def set_heading_tooltip(self, column_name: str, text: Optional[str]) -> None:
        try:
            columns = tuple(self._tree.cget("columns"))
        except tk.TclError:
            return
        try:
            idx = columns.index(column_name)
        except ValueError:
            return
        col_id = f"#{idx + 1}"
        if text:
            self._heading_texts[col_id] = text
        else:
            self._heading_texts.pop(col_id, None)

    def set_cell_text(self, item: str, column: str, text: Optional[str]) -> None:
        key = (item, column)
        if text:
            self._cell_texts[key] = text
        elif key in self._cell_texts:
            del self._cell_texts[key]
        if self._current_key == key and not text:
            self._hide_tip()

    def _on_motion(self, event: tk.Event) -> None:  # type: ignore[override]
        region = self._tree.identify_region(event.x, event.y)
        column = self._tree.identify_column(event.x)

        if region == "heading":
            key = ("", column or "")
            if key == self._current_key:
                return
            self._hide_tip()
            heading_text = self._heading_texts.get(column)
            if heading_text:
                self._current_key = key
                x = event.x_root + 16
                y = event.y_root + 12
                self._show_tip(x, y, heading_text)
            return

        item = self._tree.identify_row(event.y)
        key = (item or "", column or "")
        if key == self._current_key:
            return
        self._hide_tip()
        if not item or key not in self._cell_texts:
            return
        self._current_key = key
        x = event.x_root + 16
        y = event.y_root + 12
        self._show_tip(x, y, self._cell_texts[key])

    def _show_tip(self, x: int, y: int, text: str) -> None:
        try:
            tip = tk.Toplevel(self._tree)
        except tk.TclError:
            return
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        try:
            style = ttk.Style(self._tree)
        except tk.TclError:
            tip.destroy()
            return
        try:
            tree_background = self._tree.cget("background")
        except tk.TclError:
            tree_background = None
        bg = (
            style.lookup("TLabel", "background")
            or style.lookup("TFrame", "background")
            or tree_background
            or "#ffffe0"
        )
        fg = style.lookup("TLabel", "foreground") or "#000000"
        label = tk.Label(
            tip,
            text=text,
            background=bg,
            foreground=fg,
            relief="solid",
            borderwidth=1,
            justify="left",
        )
        label.pack(ipadx=4, ipady=2)
        self._tip = tip

    def _hide_tip(self, *_: object) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None
        self._current_key = None
