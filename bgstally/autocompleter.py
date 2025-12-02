import json
import queue
import threading
import tkinter as tk
import requests
#from bgstally.bgstally import BGSTally
from config import config # type: ignore
from bgstally.debug import Debug
from bgstally.utils import catch_exceptions

"""
Module providing an autocompleter Entry widget for system names.
Borrowed/stolen and modified from https://github.com/CMDR-Kiel42/EDMC_SpanshRouter
"""
class Placeholder(tk.Entry):
    """ An Entry widget with placeholder text functionality """
    def __init__(self, parent, placeholder, **kw) -> None:
        if parent is not None:
            tk.Entry.__init__(self, parent, **kw)
        self.var = tk.StringVar()
        self["textvariable"] = self.var

        self.placeholder = placeholder
        self.placeholder_color = "grey"

        self.bind("<FocusIn>", self.focus_in)
        self.bind("<FocusOut>", self.focus_out)

        self.put_placeholder()

    def put_placeholder(self) -> None:
        if self.get() != self.placeholder:
            self.set_text(self.placeholder, True)

    def set_text(self, text, placeholder_style=True) -> None:
        if placeholder_style:
            self['fg'] = self.placeholder_color
        else:
            self.set_default_style()
        self.delete(0, tk.END)
        self.insert(0, text)

    def force_placeholder_color(self) -> None:
        self['fg'] = self.placeholder_color

    def set_default_style(self) -> None:
        #theme = config.get_int('theme')
        #self['fg'] = config.get_str('dark_text') if theme else "black"
        self['fg'] = 'black'

    def set_error_style(self, error=True) -> None:
        if error:
            self['fg'] = "red"
        else:
            self.set_default_style()

    def focus_in(self, *args) -> None:
        if self['fg'] == "red" or self['fg'] == self.placeholder_color:
            self.set_default_style()
            if self.get() == self.placeholder:
                self.delete('0', 'end')

    def focus_out(self, *args) -> None:
        if not self.get():
            self.put_placeholder()



class AutoCompleter(Placeholder):
    """ An Entry widget with autocompletion functionality for system names """
    def __init__(self, bgstally, parent:tk.Frame, placeholder:str, **kw) -> None:

        self.bgstally:BGSTally = bgstally # type: ignore
        self.parent:tk.Frame = parent

        self.popup:tk.Toplevel = tk.Toplevel(self.parent.winfo_toplevel())
        self.popup.wm_overrideredirect(True)
        self.lb:tk.Listbox = tk.Listbox(self.popup, selectmode=tk.SINGLE, **kw)
        self.lb.pack(fill=tk.BOTH, expand=True)
        self.popup.withdraw()
        #self.lb:tk.Listbox = tk.Listbox(self.parent, selectmode=tk.SINGLE, **kw)
        self.lb_up = False
        self.has_selected = False
        self.queue:queue.Queue = queue.Queue()

        Placeholder.__init__(self, parent, placeholder, **kw)
        #self.var.traceid = self.var.trace('w', self.changed)
        self.traceid = self.var.trace_add('write', self.changed)

        # Create right click menu
        self.menu:tk.Menu = tk.Menu(self.parent, tearoff=0)
        self.menu.add_command(label="Cut")
        self.menu.add_command(label="Copy")
        self.menu.add_command(label="Paste")

        self.bind("<Any-Key>", self.keypressed)
        self.lb.bind("<Any-Key>", self.keypressed)
        self.bind('<Control-KeyRelease-a>', self.select_all)
        self.bind('<Button-3>', self.show_menu)
        self.lb.bind("<ButtonRelease-1>", self.selection)
        self.bind("<FocusOut>", self.ac_focus_out)
        self.lb.bind("<FocusOut>", self.ac_focus_out)

        self.update_me()

    def ac_focus_out(self, event=None) -> None:
        x, y = self.parent.winfo_pointerxy()
        widget_under_cursor = self.parent.winfo_containing(x, y)
        if (widget_under_cursor != self.lb and widget_under_cursor != self) or event is None:
            self.focus_out()
            self.hide_list()

    def show_menu(self, e) -> None:
        self.focus_in()
        w = e.widget
        self.menu.entryconfigure("Cut", command=lambda: w.event_generate("<<Cut>>"))
        self.menu.entryconfigure("Copy", command=lambda: w.event_generate("<<Copy>>"))
        self.menu.entryconfigure("Paste", command=lambda: w.event_generate("<<Paste>>"))
        self.menu.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def keypressed(self, event) -> None:
        key = event.keysym
        if key == 'Down':
            self.down(event.widget.widgetName)
        elif key == 'Up':
            self.up(event.widget.widgetName)
        elif key in ['Return', 'Right']:
            if self.lb_up:
                self.selection()
        elif key in ['Escape', 'Tab', 'ISO_Left_Tab'] and self.lb_up:
            self.hide_list()

    def select_all(self, event) -> None:
        event.widget.event_generate('<<SelectAll>>')

    def changed(self, name=None, index=None, mode=None) -> None:
        value = self.var.get()
        if value.__len__() < 3 and self.lb_up or self.has_selected:
            self.hide_list()
            self.has_selected = False
        else:
            t = threading.Thread(target=self.query_systems, args=[value])
            t.start()

    def selection(self, event=None) -> None:
        if self.lb_up:
            self.has_selected = True
            index = self.lb.curselection()

            #self.var.trace_vdelete("w", self.var.traceid)
            self.var.trace_remove("write", self.traceid)

            self.var.set(self.lb.get(index))
            self.hide_list()
            self.icursor(tk.END)
            #self.traceid = self.var.trace('w', self.changed)
            self.traceid = self.var.trace_add('write', self.changed)

    def up(self, widget) -> None:
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != '0':
                self.lb.selection_clear(first=index)
                index = str(int(index) - 1)
                self.lb.selection_set(first=index)
                if widget != "listbox":
                    self.lb.activate(index)

    def down(self, widget) -> None:
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
                if int(index + 1) != tk.END:
                    self.lb.selection_clear(first=index)
                    index = str(int(index + 1))

            self.lb.selection_set(first=index)
            if widget != "listbox":
                self.lb.activate(index)
        else:
            self.changed()

    def show_results(self, results):
        if results:
            self.lb.delete(0, tk.END)
            for w in results:
                self.lb.insert(tk.END, w)

            self.show_list(len(results))
        else:
            if self.lb_up:
                self.hide_list()

    @catch_exceptions
    def show_list(self, height) -> None:
        self.lb["height"] = height
        if not self.lb_up and self.parent.focus_get() is self:
            x:int = self.winfo_rootx()
            y:int = self.winfo_rooty() + self.winfo_height()
            self.popup.wm_geometry(f"+{x}+{y}")
            self.popup.deiconify() # Show the popup
            self.lb_up = True

    def hide_list(self) -> None:
        if self.lb_up:
            #self.lb.grid_remove()
            self.popup.withdraw()
            self.lb_up = False

    def query_systems(self, inp:str) -> None:
        inp = inp.strip()
        if inp != self.placeholder and inp.__len__() >= 3:
            url = "https://spansh.co.uk/api/systems?"
            results:requests.Response = requests.get(url,
                                    params={'q': inp},
                                    headers={'User-Agent': f"BGSTally/{self.bgstally.version}"},
                                    timeout=3)

            lista = json.loads(results.content)
            if lista:
                self.queue.put(lista)

    def update_me(self) -> None:
        try:
            while 1:
                lista = self.queue.get_nowait()
                self.show_results(lista)
                self.update_idletasks()
        except queue.Empty:
            pass
        self.after(100, self.update_me)

    def set_text(self, text, placeholder_style=True) -> None:
        if placeholder_style:
            self['fg'] = self.placeholder_color
        else:
            self.set_default_style()

        try:
            #self.var.trace_vdelete("w", self.var.traceid)
            self.var.trace_remove("write", self.traceid)
        except:
            pass
        finally:
            self.delete(0, tk.END)
            self.insert(0, text)
            #self.var.traceid = self.var.trace('w', self.changed)
            self.traceid = self.var.trace_add('write', self.changed)
