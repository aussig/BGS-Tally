import tkinter as tk
from functools import partial
from typing import Any, TYPE_CHECKING
from theme import theme  # type: ignore
from config import config  # type: ignore

class PlaceholderMixin:
    """
        Adds placeholder text and a right-click cut/copy/paste menu to a themed widget.
    """
    if TYPE_CHECKING:
        # Declared for the type checker only -- the actual attributes are set dynamically in
        # init_placeholder() (via object.__setattr__, see the docstring above) and these methods
        # come from whichever host class (tk.Entry, utils.th.Base) this mixin is combined with.
        placeholder:str
        placeholder_color:str
        error_color:str
        var:tk.StringVar
        menu:tk.Menu

        def bind(self, *args:Any, **kwargs:Any) -> Any: ...
        def configure(self, cnf:Any = None, **kw) -> Any: ...
        def __getitem__(self, key:str) -> Any: ...
        def __setitem__(self, key:str, value:Any) -> None: ...

    def init_placeholder(self, parent, placeholder:str, menu:dict|None = None,
                          placeholder_color:str = "grey", error_color:str = "red") -> None:
        """
            :param placeholder: The placeholder text to show when the widget is empty
            :param menu: A dictionary of right click menu items in the form {'Menu Item': (function, arg1, arg2, ...)}
            :param placeholder_color: The color of the placeholder text (default: grey)
            :param error_color: The color of the text when in error state (default: red)
        """
        object.__setattr__(self, 'placeholder', placeholder)
        object.__setattr__(self, 'placeholder_color', placeholder_color)
        object.__setattr__(self, 'error_color', error_color)

        var:tk.StringVar = tk.StringVar()
        object.__setattr__(self, 'var', var)
        self['textvariable'] = var

        # Create right click menu
        object.__setattr__(self, 'menu', tk.Menu(parent, tearoff=0))
        self.set_menu(menu or {})
        self.bind('<Button-3>', partial(self.show_menu))

        self.bind("<FocusIn>", self.focus_in)
        self.bind("<FocusOut>", self.focus_out)
        self.bind('<Control-KeyRelease-a>', self.select_all)
        self.bind('<Control-KeyRelease-c>', self.copy)
        self.put_placeholder()

        # return the host object to which this mixin is attached
        host = getattr(self, 'obj', None)
        if host is not None:
            host.var = self.var
            host.placeholder = self.placeholder
            for m in ('set_text', 'set_menu', 'put_placeholder', 'force_placeholder_color',
                      'set_default_style', 'set_error_style'):
                setattr(host, m, getattr(self, m))

    def set_menu(self, menu:dict = {}) -> None:
        self.menu.delete(0, "end")
        self.menu.add_command(label="Cut")
        self.menu.add_command(label="Copy")
        self.menu.add_command(label="Paste")
        if len(menu):
            self.menu.add_separator()
        for m, f in menu.items():
            self.menu.add_command(label=m, command=partial(*f, m))

    def show_menu(self, e) -> None:
        self.focus_in(e)
        w = e.widget
        self.menu.entryconfigure("Cut", command=lambda: w.event_generate("<<Cut>>"))
        self.menu.entryconfigure("Copy", command=lambda: w.event_generate("<<Copy>>"))
        self.menu.entryconfigure("Paste", command=lambda: w.event_generate("<<Paste>>"))

        self.menu.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def put_placeholder(self) -> None:
        if self.var.get() != self.placeholder:
            self.set_text(self.placeholder, True)

    def set_text(self, text, placeholder_style=True) -> None:
        self.var.set(text)
        if placeholder_style or text == self.placeholder:
            self['foreground'] = self.placeholder_color
        else:
            self.set_default_style()

    def force_placeholder_color(self) -> None:
        self['foreground'] = self.placeholder_color

    def set_default_style(self) -> None:
        self['foreground'] = config.get_str('dark_text') if config.get_int('theme') > 0 else "black"

    def set_error_style(self, error=True) -> None:
        if error:
            self['foreground'] = self.error_color
        else:
            self.set_default_style()

    def focus_in(self, e, *args) -> None:
        if self['foreground'] == "red" or self['foreground'] == self.placeholder_color:
            self.set_default_style()
            if self.var.get() == self.placeholder:
                self.var.set('')
            return
        self.select_all(e)

    def focus_out(self, *args) -> None:
        if not self.var.get():
            self.put_placeholder()

    def select_all(self, event) -> None:
        event.widget.event_generate('<<SelectAll>>')

    def copy(self, event) -> None:
        event.widget.event_generate('<<Copy>>')


class Placeholder(PlaceholderMixin, tk.Entry):
    """
        A reusable Entry widget with placeholder text and dropdown menu functionality.
        Borrowed/stolen and modified from https://github.com/CMDR-Kiel42/EDMC_SpanshRouter

        It takes the same parameters as a tk.Entry object plus the placeholder/menu/
        placeholder_color/error_color kwargs described in PlaceholderMixin.init_placeholder.
    """
    def __init__(self, parent, placeholder, **kw) -> None:
        menu:dict = kw.pop('menu', {})
        placeholder_color:str = kw.pop('placeholder_color', "grey")
        error_color:str = kw.pop('error_color', "red")

        if 'relief' not in kw:
            kw['relief'] = tk.GROOVE

        if parent is not None:
            tk.Entry.__init__(self, parent, **kw)
            theme.register(self)

        self.init_placeholder(parent, placeholder, menu, placeholder_color, error_color)
