"""
A themed frame with a vertically scrollable interior.

The scrollbar only appears once packed/gridded content in `.interior` exceeds `maxheight`
pixels; while content fits, the widget looks and behaves like a plain frame.
"""
import tkinter as tk
from tkinter import ttk

from theme import theme # type: ignore

class ScrollableFrame(tk.Frame):
    """
    A themed frame whose content -- packed or gridded into `.interior` -- scrolls vertically once it exceeds `maxheight` pixels.
    """
    def __init__(self, master:tk.Widget, maxheight:int|None = None, **kw) -> None:
        tk.Frame.__init__(self, master, **kw)
        theme.update(self)

        self._maxheight = maxheight
        self._scrollbar_visible = False
        self._resize_pending = False
        self._last_height:int|None = None
        self._last_scrollregion:tuple|None = None
        self._last_item_width:int|None = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        theme.register(self._canvas)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        # Not gridded yet -- shown/hidden by _update_scrollbar_visibility() as content changes.

        from . import Frame # local import: avoids a hard circular import at module load time
        self.interior:tk.Frame = Frame(self._canvas)
        theme.register(self.interior) # else stuck light forever -- canvas children aren't walked
        self._interior_id = self._canvas.create_window((0, 0), window=self.interior, anchor="nw")

        self.interior.bind("<Configure>", self._on_interior_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_interior_configure(self, event:tk.Event|None = None) -> None:
        """ Content changed -- schedule (don't do inline) a scroll-region/scrollbar recompute. """
        if self._resize_pending:
            return
        self._resize_pending = True
        self.after_idle(self._apply_resize)

    def _apply_resize(self) -> None:
        self._resize_pending = False
        if not self._canvas.winfo_exists():
            return

        for child in self.interior.winfo_children():
            theme.update(child) # colors it if the theme is already known...
            theme.register(child) # ...and covers it for a later apply() if not

        bbox = self._canvas.bbox("all")
        # Compare against the value *we* last applied, not the widget's own read-back: under
        # non-100% Tk UI scaling, configure(x) and cget() don't always round-trip to the same
        # value, so comparing against a read-back can look "different" every single pass even
        # when nothing meaningful changed -- which is exactly the kind of oscillation that
        # feeds an unbounded <Configure> storm once a real update() (not just
        # update_idletasks()) is draining events, rather than the harmless one-time settle a
        # genuine content change should produce.
        if bbox is not None and bbox != self._last_scrollregion:
            self._last_scrollregion = bbox
            self._canvas.configure(scrollregion=bbox)
        content_height:int = self._content_height()
        self._update_scrollbar_visibility(content_height)

    def _content_height(self) -> int:
        """ Sum the children's own requested heights rather than trust `.interior.winfo_reqheight()` """
        return sum(child.winfo_reqheight() for child in self.interior.winfo_children())

    def _on_canvas_configure(self, event:tk.Event) -> None:
        """ Keep the interior frame's width matched to the canvas's visible width. """
        if self._last_item_width != event.width:
            self._last_item_width = event.width
            self._canvas.itemconfigure(self._interior_id, width=event.width)

    def configure(self, cnf=None, **kw) -> None: # type: ignore[override] -- never queries one option
        """ Route the synthetic `maxheight` option through our own recompute """
        merged:dict = dict(cnf or {})
        merged.update(kw)
        if 'maxheight' in merged:
            value = merged.pop('maxheight')
            if value != self._maxheight:
                self._maxheight = value
                self._apply_resize() # not a <Configure>-driven change, so no storm risk applying inline
        if merged:
            tk.Frame.configure(self, **merged)

    config = configure

    def cget(self, key:str):
        if key == 'maxheight':
            return self._maxheight
        return tk.Frame.cget(self, key)

    __getitem__ = cget

    def clear(self) -> None:
        """ Remove all content from `.interior` in one shot. """
        self.interior.unbind("<Configure>")
        for child in self.interior.winfo_children():
            child.destroy()
        self.interior.bind("<Configure>", self._on_interior_configure)
        self._on_interior_configure()

    def _update_scrollbar_visibility(self, content_height:int) -> None:
        needs_scroll:bool = self._maxheight is not None and content_height > self._maxheight

        if needs_scroll and not self._scrollbar_visible:
            self._scrollbar.grid(row=0, column=1, sticky="ns")
            self._scrollbar_visible = True
        elif not needs_scroll and self._scrollbar_visible:
            self._scrollbar.grid_forget()
            self._scrollbar_visible = False

        display_height:int = min(content_height, self._maxheight) if self._maxheight else content_height
        if self._last_height != display_height:
            self._last_height = display_height
            self._canvas.configure(height=display_height)

    def _bind_mousewheel(self, event:tk.Event|None = None) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event:tk.Event|None = None) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event:tk.Event) -> None:
        if not self._scrollbar_visible:
            return
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(delta, "units")
