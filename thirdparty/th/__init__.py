# -*- coding: utf-8 -*-
from typing import Any

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from theme import theme # type: ignore
from config import config # type: ignore

from ..tkrichtext import RichLabel as _RichLabel, RichText as _RichText, RichScrolledText as _RichScrolledText
from .autocompleter import Autocompleter
from .placeholder import Placeholder, PlaceholderMixin
from .tooltip import Tooltip

__all__ = ["TopLevel", "Frame", "LabelFrame", "Label", "Text", "RichText", "RichScrolledText", "Button", "Radiobutton", "ComboBox",
           "Listbox", "Checkbutton", "Scale", "Spinbox", "ScrollableFrame", "Tooltip", "Autocompleter", "Placeholder", "resolve"]

DEBUG_FRAMES:bool = False # Turn this on to color each frame for debugging
index:int = 0

def _strip_name(kw:dict) -> dict:
    """ Strip an explicit Tk 'name' from kwargs meant for a themed widget's second (alt) half. """
    return {k: v for k, v in kw.items() if k != 'name'}

def _match_label_defaults(kw:dict) -> None:
    """ Matches th.Label's own defaults, or register() sees a raw
    tk.Text as pre-customized and blocks theme switches. """
    kw.setdefault('foreground', tk.Label()['foreground'])
    kw.setdefault('background', tk.Label()['background'])
    kw.setdefault('font', tk.Label()['font'])
    kw.setdefault('insertbackground', kw['foreground']) # caret stays visible against a dark background too

def resolve(widget:Any) -> Any:
    """ Resolve the actual base object for a tk nametowidget() lookup. """
    return getattr(widget, 'themed', widget)

""" A set of UI objects to handle themed widgets for dealing with EDMC dark mode """
class Base:
    """ A base class for themed widgets that can switch between light and dark mode. """
    def __init__(self, obj:ttk.Widget|tk.Widget, alt:ttk.Widget|tk.Widget|None = None) -> None:
        object.__setattr__(self, 'images', [])
        object.__setattr__(self, 'obj', obj)
        object.__setattr__(self, 'alt', alt)
        object.__setattr__(self, '_last_gridopts', None)

        # Back-reference so th.resolve() can recover this wrapper from a nametowidget() lookup.
        setattr(obj, 'themed', self)
        if alt is not None:
            setattr(alt, 'themed', self)

        theme.register(obj)
        if alt is not None:
            theme.register(alt)

    def grid(self, *args, **kw) -> Any:
        """ theme.register_alternate() needs grid options, so we intercept grid() calls to register them.
        Only register when the options actually changed since last time. """
        if self.alt is None:
            return self.obj.grid(*args, **kw)

        gridopts:dict = {}

        if len(args) > 0 and isinstance(args[0], dict):
            gridopts.update(args[0])
        if len(kw) > 0:
            gridopts.update(kw)

        if len(gridopts) > 0 and gridopts != self._last_gridopts:
            theme.register_alternate((self.obj, self.alt, self.alt), gridopts)
            object.__setattr__(self, '_last_gridopts', gridopts)

        # 'theme' (0=default, 1=dark, 2=transparent)
        return self.alt.grid(*args, **kw) if config.get_int('theme') != 0 else self.obj.grid(*args, **kw)

    def configure(self, cnf=None, **kw) -> None:
        """ Override configure to handle themed buttons. """

        if 'image' in kw and self.alt is not None:
            object.__setattr__(self, 'images', getattr(self, 'images', []) + [kw['image']])
        if self.alt is not None:
            self.alt.configure(cnf, **kw)
        self.obj.configure(cnf, **kw)

    def config(self, cnf=None, **kw) -> None:
        """ config/configure are synonyms """
        return self.configure(cnf, **kw)

    def _callable_attr(self, name:str, *args, **kw) -> Any:
        """Call a same-named method on both widgets, returning the primary result."""
        method = getattr(self.obj, name)
        result = method(*args, **kw)

        if self.alt is not None:
            alt_method = getattr(self.alt, name, None)
            if callable(alt_method):
                alt_method(*args, **kw)

        return result

    def __getattr__(self, name:str) -> Any:
        """Fallback proxy so themedItem behaves like its wrapped widget."""
        attr = getattr(self.obj, name, None)
        if attr is None and self.alt is not None:
            attr = getattr(self.alt, name, None)
        if attr is None:
            raise AttributeError(name)
        if callable(attr):
            return lambda *args, **kw: self._callable_attr(name, *args, **kw)

        return attr

    def __setattr__(self, name:str, value:Any) -> None:
        """Fallback proxy so themedItem behaves like its wrapped widget."""
        if getattr(self.obj, name, None) is not None:
            setattr(self.obj, name, value)
        if self.alt is not None and getattr(self.alt, name, None) is not None:
            setattr(self.alt, name, value)

    def __getitem__(self, key):
        """Support subscript notation for themedItem."""
        if key in self.obj.keys():
            return self.obj[key]
        if self.alt is not None and key in self.alt.keys():
            return self.alt[key]
        raise KeyError(key)

    def __setitem__(self, key, value) -> None:
        """Support subscript assignment for themedItem, e.g. widget['fg'] = 'red'."""
        self.configure(**{key: value})

class TopLevel(tk.Toplevel):
    """
    A plain themed toplevel window. Deliberately does NOT call theme.update()/register() on
    itself
    """
    def __init__(self, master:tk.Widget, **kw) -> None:
        tk.Toplevel.__init__(self, master, **kw)

class Frame(tk.Frame):
    """ A themed frame that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        global index
        tk.Frame.__init__(self, master, **kw)
        if DEBUG_FRAMES:
            colors = ["lightcoral", "lightgreen", "lightblue", "lightyellow", "plum"]
            self.configure(background=colors[index])
            index += 1
            if index >= len(colors): index = 0

        theme.update(self)

    def nametowidget(self, name:str) -> Any: # type: ignore
        """ A recursive descendant search for nametowidget(), resolved to the themed wrapper. """
        try:
            return resolve(super().nametowidget(name))
        except KeyError:
            pass

        for child in self.winfo_children():
            find = getattr(child, 'nametowidget', None)
            if find is None:
                continue
            try:
                return resolve(find(name))
            except (KeyError, AttributeError):
                continue
        raise KeyError(name)

class LabelFrame(tk.LabelFrame):
    """ A themed label frame that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        tk.LabelFrame.__init__(self, master, **kw)
        theme.update(self)

class Label(tk.Label):
    """ A themed label that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        tk.Label.__init__(self, master, **kw)
        theme.update(self)

class Text(tk.Text):
    """ A themed text box that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        _match_label_defaults(kw)
        tk.Text.__init__(self, master, **kw)
        theme.update(self)

class _RichBgSync:
    """ Re-renders set_html() output on bg change -- tags bake in the old bg otherwise. """
    _last_html:str|None = None

    def set_html(self, html:str, strip:bool = True) -> None:
        self._last_html = html
        super().set_html(html, strip=strip) # type: ignore

    def configure(self, cnf=None, **kw) -> Any:
        result = super().configure(cnf, **kw) # type: ignore
        changed_bg:bool = (isinstance(cnf, dict) and 'background' in cnf) or 'background' in kw
        if changed_bg and self._last_html is not None:
            self.set_html(self._last_html)
        return result

class RichScrolledText(_RichBgSync, _RichScrolledText):
    """ A themed, scrollable HTML/markdown text box. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        _match_label_defaults(kw)
        _RichScrolledText.__init__(self, master, **kw)
        # .frame is a bare tk.Frame; nothing else themes it, so
        # it'd show through as an unthemed border around the Text.
        self.frame.configure(background=kw['background'])
        theme.register(self.frame)
        theme.update(self)

class RichText(_RichBgSync, _RichText):
    """ RichScrolledText, minus its (always-hidden) scrollbar. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        _match_label_defaults(kw)
        _RichText.__init__(self, master, **kw)
        self.frame.configure(background=kw['background'])
        theme.register(self.frame)
        theme.update(self)

class RichLabel(_RichBgSync, _RichLabel):
    """ Label version of RichText widget """
    def __init__(self, master:tk.Widget, **kw) -> None:
        _match_label_defaults(kw)
        _RichLabel.__init__(self, master, **kw)
        self.frame.configure(background=kw['background'])
        theme.register(self.frame)
        theme.update(self)

class Entry(Base):
    """ A themed entry that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        ent:ttk.Entry = ttk.Entry(master, **kw)
        kw.setdefault('relief', tk.GROOVE)
        alt:tk.Entry = tk.Entry(master, **_strip_name(kw))
        super().__init__(ent, alt)
        theme.update(self)

class Button(Base):
    """ A themed button that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        # EDMC's theme has a bug if the cursor is set on a ttk.Button with an image so we use a tk.Button
        btn:ttk.Button|tk.Button = tk.Button(master, **kw) if 'cursor' in kw else ttk.Button(master, **kw)

        alt:tk.Button = tk.Button(master, **_strip_name(kw))

        super().__init__(btn, alt)

        # ttk.Button width is characters. tk.Button width is pixels.
        w = kw.get('width')
        object.__setattr__(self, '_char_width', int(w) if w is not None else None)

    def configure(self, cnf=None, **kw) -> None:
        """ Override configure to also counteract tk.Button's width-unit switch on image attach. """
        if 'cursor' in kw and isinstance(self.obj, ttk.Button):
            # obj was built ttk.Button adding a cursor now would break EDMC's theme code.
            raise ValueError("th.Button: pass cursor= at creation, not via a later configure()")

        super().configure(cnf, **kw)

        if self._char_width is None or 'image' not in kw:
            return

        for w in (self.obj, self.alt):
            if isinstance(w, tk.Button):
                px:int = tkfont.Font(font=w.cget('font')).measure('0' * self._char_width)
                w.configure(width=px)

class Radiobutton(Base):
    """ A themed radiobutton that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        tkrb:tk.Radiobutton = tk.Radiobutton(master, **_strip_name(kw))
        tkrb.configure(foreground=config.get_str('dark_text'), highlightthickness=0, activebackground='black', highlightbackground='black',
                        selectcolor='black', border=0, borderwidth=0)
        super().__init__(ttk.Radiobutton(master, **kw), tkrb)

class ComboBox(Base):
    """ A themed combobox that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, v:tk.StringVar, **kw) -> None:
        ttkcb:ttk.Combobox = ttk.Combobox(master, textvariable=v, state='readonly', **kw)

        value:str = ''
        values:list = []
        if len(kw.get('values', [])) > 0:
            value = kw['values'][0]
        if len(kw.get('values', [])) > 1:
            values = kw['values'][1:]

        tkcb:tk.OptionMenu = tk.OptionMenu(master, v, value, *values)
        tkcb.configure(activeforeground=config.get_str('dark_text'), highlightbackground='black', activebackground='black', border=0,
                        borderwidth=1, highlightthickness=0)
        tkcb["menu"].config(bg='black', fg=config.get_str('dark_text'), activebackground=config.get_str('dark_text'), activeforeground="BLACK")

        super().__init__(ttkcb, tkcb)
        object.__setattr__(self, '_variable', v)
        object.__setattr__(self, '_select_func', None)

    def _wire_alt_menu(self) -> None:
        """ (Re-)apply the bound <<ComboboxSelected>> callback, if any, to every entry in the alt's menu. """
        func = self._select_func
        if self.alt is None or func is None:
            return
        menu = self.alt["menu"]
        last:int|None = menu.index("end")
        if last is None:
            return
        for i in range(last + 1):
            label = menu.entrycget(i, "label")
            menu.entryconfigure(i, command=lambda label=label: (self._variable.set(label), func(None)))

    def set_menu(self, menu:list[str]) -> None:
        """ Set the menu for the themed combobox. """
        self.obj["values"] = menu
        if self.alt is not None:
            self.alt['menu'].delete(0, 'end')
            for item in menu:
                self.alt['menu'].add_command(label=item, command=tk._setit(self._variable, item))
            self._variable.set(menu[0])
            self._wire_alt_menu()

    def bind(self, sequence:str, func, **kw) -> None:
        """ workaround tk.OptionMenu not having a <<ComboboxSelected>> like ttk.Combobox """
        self.obj.bind(sequence, func, **kw)
        if self.alt is None:
            return
        if sequence == "<<ComboboxSelected>>":
            object.__setattr__(self, '_select_func', func)
            self._wire_alt_menu()
        else:
            self.alt.bind(sequence, func, **kw)

class Listbox(Base):
    """ A themed listbox that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, items:list, **kw) -> None:
        # @TODO: Switch the plain mode for a treeview?
        rows:int = min(len(items), 10)
        kw.setdefault('selectmode', tk.MULTIPLE)
        kw.setdefault('exportselection', False)

        lb1:tk.Listbox = tk.Listbox(master, height=rows, **kw)
        lb1.configure(border=0, borderwidth=0, activestyle=tk.NONE, highlightthickness=0)

        lb2:tk.Listbox = tk.Listbox(master, height=rows, **_strip_name(kw))
        lb2.configure(borderwidth=1, border=1, activestyle=tk.NONE, highlightthickness=0, relief=tk.GROOVE,
                      selectbackground='gray25', highlightbackground='black', background='black')

        for i in range(len(items)):
            lb1.insert(tk.END, items[i])
            lb2.insert(tk.END, items[i])

        def sync(source:tk.Listbox, target:tk.Listbox) -> None:
            """ Mirror a user-driven selection change on the visible widget onto its hidden twin. """
            target.selection_clear(0, tk.END)
            for i in source.curselection():
                target.selection_set(i)

        lb1.bind('<<ListboxSelect>>', lambda e: sync(lb1, lb2))
        lb2.bind('<<ListboxSelect>>', lambda e: sync(lb2, lb1))

        super().__init__(lb1, lb2)

class Checkbutton(Base):
    """ A themed checkbutton that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        super().__init__(tk.Checkbutton(master, **kw), tk.Checkbutton(master, **_strip_name(kw)))

class Scale(Base):
    """ A themed scale that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, **kw) -> None:
        tksc1:tk.Scale = tk.Scale(master, **kw, border=0, borderwidth=0, highlightthickness=0)
        tksc2:tk.Scale = tk.Scale(master, **_strip_name(kw), border=0, borderwidth=0, highlightthickness=0)
        tksc2.configure(troughcolor='gray25', highlightbackground='black', activebackground='black')
        super().__init__(tksc1, tksc2)

class Spinbox(PlaceholderMixin, Base):
    """ A themed spinbox that can switch between light and dark mode. """
    def __init__(self, master:tk.Widget, placeholder:str = "", **kw) -> None:
        menu:dict = kw.pop('menu', {})
        placeholder_color:str = kw.pop('placeholder_color', "grey")
        error_color:str = kw.pop('error_color', "red")

        rgb = master.winfo_rgb(master['background'])
        background:str = '#{:02x}{:02x}{:02x}'.format(rgb[0] // 256, rgb[1] // 256, rgb[2] // 256)

        sb1:ttk.Spinbox = ttk.Spinbox(master, **kw, background=background, foreground='black')
        sb2:tk.Spinbox = tk.Spinbox(master, **_strip_name(kw), border=0, borderwidth=1, highlightthickness=0)
        sb2.configure(background='black', foreground=config.get_str('dark_text'), highlightbackground='black',
                      buttonbackground='black', fg=config.get_str('dark_text'), insertbackground=config.get_str('dark_text'))
        super().__init__(sb1, sb2)

        self.init_placeholder(master, placeholder, menu, placeholder_color, error_color)

# Imported last: scrollableframe.py does `from . import Frame`, which needs Frame already
# defined on this module before it runs.
from .scrollableframe import ScrollableFrame
