import tkinter as tk
from tkinter import CURRENT, END, ttk
from functools import partial
from datetime import datetime
import re
import json
import queue
import threading
import requests

from config import config # type: ignore

from bgstally.constants import FONT_TEXT, FONT_TEXT_BOLD, FONT_TEXT_UNDERLINE, FONT_TEXT_BOLD_UNDERLINE
from bgstally.debug import Debug
from bgstally.utils import _, catch_exceptions, parse_human_format
class TextPlus(tk.Text):
    """
    Subclass of tk.Text to install a context-sensitive menu on right-click
    """

    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        _rc_menu_install(self)
        # overwrite default class binding so we don't need to return "break"
        self.bind_class("Text", "<Control-a>", self.event_select_all)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)

    def event_select_all(self, *args):
        self.focus_force()
        self.tag_add("sel","1.0","end")

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)


# author: stefaan.himpe@gmail.com
# license: MIT

class DiscordAnsiColorText(tk.Text):
    """
    class to convert text with a limited set of Discord-supported ansi color codes to
    text with tkinter color tags
    """
    foreground_colors = {
        "30": "gray20",
        "31": "firebrick1",
        "32": "olive drab",
        "33": "DarkGoldenrod3",
        "34": "DodgerBlue2",
        "35": "magenta4",
        "36": "cyan4",
        "37": "White",
    }

    background_colors = {
        "40": "DodgerBlue4",
        "41": "orange red",
        "42": "gray30",
        "43": "gray40",
        "44": "gray50",
        "45": "LightBlue",
        "46": "gray60",
        "47": "White",
    }

    # define some regexes which will come in handy in filtering
    # out the ansi color codes
    color_pat = re.compile(r'\x01?\x1b(\[[\d;]*m?)\x02?')
    inner_color_pat = re.compile(r'^\[([\d;]*)m$')

    def __init__(self, *args, **kwargs):
        """
        initialize our specialized tkinter Text widget
        """
        tk.Text.__init__(self, *args, **kwargs)
        self.known_tags = set([])

        # register a default color tag
        self.register_tag("0", "White", "Gray13", FONT_TEXT)
        self.tag_config("sel", background="Gray13") # Make the selected text colour the same as the widget background
        self.configure(cursor='arrow')
        self.reset_to_default_attribs()

    def reset_to_default_attribs(self):
        self.tag = "0"
        self.foregroundcolor = "White"
        self.backgroundcolor = "Gray13"
        self.font = FONT_TEXT

    def register_tag(self, txt, foreground, background, font):
        """
        register a tag with name txt and with given
        foreground and background color
        """
        self.tag_config(txt, foreground=foreground, background=background, font=font)
        self.known_tags.add(txt)

    def write(self, text, is_editable=False):
        """
        add text to the text widget
        """
        # Remove the Discord ansi block terminators
        text = text.replace("```ansi", "").replace("```", "")

        # Split the text at color codes, stripping stuff like the <ESC>
        # and \[ characters and keeping only the inner "0;23"-like codes
        segments = DiscordAnsiColorText.color_pat.split(text)
        if segments:
            for text in segments:
                # a segment can be regular text, or it can be a color pattern
                if DiscordAnsiColorText.inner_color_pat.match(text):
                    # if it's a color pattern, check if we already have
                    # registered a tag for it
                    text = text[1:-1] # Strip leading '[' and trailing 'm'
                    if text not in self.known_tags:
                        # if tag not yet registered, start with defaults and
                        # extract the colour and style
                        self.reset_to_default_attribs()
                        parts = text.split(";")
                        for part in parts:
                            if part in DiscordAnsiColorText.foreground_colors:
                                self.foregroundcolor = DiscordAnsiColorText.foreground_colors[part]
                            elif part in DiscordAnsiColorText.background_colors:
                                self.backgroundcolor = DiscordAnsiColorText.background_colors[part]
                            elif part == "1":
                                if self.font == FONT_TEXT: self.font = FONT_TEXT_BOLD
                                else: self.font = FONT_TEXT_BOLD_UNDERLINE
                            elif part == "4":
                                if self.font == FONT_TEXT: self.font = FONT_TEXT_UNDERLINE
                                else: self.font = FONT_TEXT_BOLD_UNDERLINE

                        self.register_tag(
                            text,
                            foreground=self.foregroundcolor,
                            background=self.backgroundcolor,
                            font=self.font
                        )
                    # Remember that we switched to this tag
                    self.tag = text
                elif text == "":
                    # Reset tag to default
                    self.tag = "0"
                else:
                    # Not a color pattern, insert text with the currently selected tag
                    self.insert(END, text, self.tag)


class EntryPlus(ttk.Entry):
    """
    Subclass of ttk.Entry to install a context-sensitive menu on right-click
    """
    def __init__(self, *args, **kwargs):
        ttk.Entry.__init__(self, *args, **kwargs)
        _rc_menu_install(self)
        # overwrite default class binding so we don't need to return "break"
        self.bind_class("Entry", "<Control-a>", self.event_select_all)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)

    def event_select_all(self, *args):
        self.focus_force()
        self.selection_range(0, tk.END)

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)


def _rc_menu_install(w):
    """
    Create a context sensitive menu for a text widget
    """
    w.menu = tk.Menu(w, tearoff=0)
    w.menu.add_command(label=_("Cut")) # LANG: Right-click menu option
    w.menu.add_command(label=_("Copy")) # LANG: Right-click menu option
    w.menu.add_command(label=_("Paste")) # LANG: Right-click menu option
    w.menu.add_separator()
    w.menu.add_command(label=_("Select all")) # LANG: Right-click menu option

    w.menu.entryconfigure(_("Cut"), command=lambda: w.focus_force() or w.event_generate("<<Cut>>")) # LANG: Right-click menu option
    w.menu.entryconfigure(_("Copy"), command=lambda: w.focus_force() or w.event_generate("<<Copy>>")) # LANG: Right-click menu option
    w.menu.entryconfigure(_("Paste"), command=lambda: w.focus_force() or w.event_generate("<<Paste>>")) # LANG: Right-click menu option
    w.menu.entryconfigure(_("Select all"), command=w.event_select_all) # LANG: Right-click menu option



class HyperlinkManager:
    """
    Utility class to enable embedded hyperlinks in Text fields.

    Usage:

    text = Text(win)
    hyperlink = HyperlinkManager(text)
    text.insert(END, "Click me", hyperlink.add(partial(webbrowser.open, "https://example.com")))
    """
    def __init__(self, text):
        self.text = text

        self.text.tag_config("hyper", foreground="blue", underline=1)

        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)

        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action):
        # Add an action to the manager.  returns tags to use in associated text widget
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = action
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return


class CollapsibleFrame(ttk.Frame):
    """
     -----USAGE-----
    CollapsibleFrame = CollapsibleFrame(parent,
                          expanded_text =[string],
                          collapsed_text =[string])

    CollapsibleFrame.pack()
    button = Button(CollapsibleFrame.frame).pack()
    """

    def __init__(self, parent, show_button = True, expanded_text = "Collapse <<",
                               collapsed_text = "Expand >>", open = False):

        ttk.Frame.__init__(self, parent)

        # These are the class variable
        # see a underscore in expanded_text and _collapsed_text
        # this means these are private to class
        self.parent = parent
        self._show_button = show_button
        self._expanded_text = expanded_text
        self._collapsed_text = collapsed_text

        # Tkinter variable storing integer value
        self._variable = tk.IntVar(value=open)

        # Checkbutton is created but will behave as Button
        # cause in style, Button is passed
        # main reason to do this is Button do not support
        # variable option but checkbutton do
        if self._show_button:
            # Here weight implies that it can grow it's
            # size if extra space is available
            # default weight is 0
            self.columnconfigure(1, weight=1)

            self._button = ttk.Checkbutton(self, variable=self._variable,
                                command=self._activate, style="TButton")
            self._button.grid(row=0, column=0)

            # This will create a separator
            # A separator is a line, we can also set thickness
            self._separator = ttk.Separator(self, orient=tk.HORIZONTAL)
            self._separator.grid(row=0, column=1, sticky=tk.EW)
        else:
            # We need any widget to be in our top-level grid, otherwise
            # the window won't contract when the panel is closed. Place
            # an invisible frame
            self._separator = tk.Frame(self, height=0)
            self._separator.grid(row=0, column=0, sticky=tk.EW)

        # The internal sub-frame is gridded and ungridded to show/hide contents
        self.frame = ttk.Frame(self)

        # This will call activate function of class
        self._activate()

    def _activate(self):
        if not self._variable.get():
            # As soon as button is pressed it removes this widget
            # but is not destroyed means can be displayed again
            self.frame.grid_forget()

            # This will change the text of the checkbutton
            if self._show_button:
                self._button.configure(text=self._collapsed_text)

        elif self._variable.get():
            # increasing the frame area so new widgets
            # could reside in this container
            if self._show_button:
                self.frame.grid(row=1, column=0, columnspan=2)
                self._button.configure(text=self._expanded_text)
            else:
                self.frame.grid(row=0, column=0)

    def toggle(self):
        """Switches the label frame to the opposite state."""
        self._variable.set(not self._variable.get())
        self._activate()

    def open(self):
        self._variable.set(1)
        self._activate()

    def close(self):
        self._variable.set(0)
        self._activate()


class TreeviewPlus(ttk.Treeview):
    def __init__(self, parent, callback, datetime_format, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)
        self.callback = callback
        self.datetime_format = datetime_format
        self.bind('<ButtonRelease-1>', self._select_item)


    def heading(self, column, sort_by=None, **kwargs):
        if sort_by and not hasattr(kwargs, 'command'):
            func = getattr(self, f"_sort_by_{sort_by}", None)
            if func:
                kwargs['command'] = partial(func, column, False)

        return super().heading(column, **kwargs)

    def _select_item(self, event):
        clicked_item = self.item(self.focus())
        clicked_column_ref = self.identify_column(event.x)
        if type(clicked_item['values']) is not list: return

        clicked_column = int(clicked_column_ref[1:]) - 1
        if clicked_column < 0: return

        iid:str = self.identify('item', event.x, event.y)

        if self.callback is not None:
            self.callback(clicked_item['values'], clicked_column, self, iid)

    def _sort(self, column, reverse, data_type, callback):
        l = [(self.set(k, column), k) for k in self.get_children('')]
        l.sort(key=lambda t: data_type(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(l):
            self.move(k, '', index)

        self.heading(column, command=partial(callback, column, not reverse))

    def _sort_by_num(self, column, reverse):
        def _str_to_int(string) -> int:
            v:int = parse_human_format(string, True)
            return int(v) if v != '' else 0

        self._sort(column, reverse, _str_to_int, self._sort_by_num)

    def _sort_by_name(self, column, reverse):
        self._sort(column, reverse, str, self._sort_by_name)

    def _sort_by_datetime(self, column, reverse):
        def _str_to_datetime(string):
            return datetime.strptime(string, self.datetime_format)

        self._sort(column, reverse, _str_to_datetime, self._sort_by_datetime)



class Placeholder(tk.Entry):
    """
        An Entry widget with placeholder text functionality
        Borrowed/stolen and modified from https://github.com/CMDR-Kiel42/EDMC_SpanshRouter
    """
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
    """
        An Entry widget with autocompletion functionality for system names
        Borrowed/stolen and modified from https://github.com/CMDR-Kiel42/EDMC_SpanshRouter

        @TODO: Modify to support a configurable function to query an API and return a list
    """
    def __init__(self, bgstally, parent:tk.Frame, placeholder:str, **kw) -> None:
        self.bgstally:BGSTally = bgstally # type: ignore
        self.parent:tk.Frame = parent

        self.popup:tk.Toplevel = tk.Toplevel(self.parent.winfo_toplevel())
        self.popup.wm_overrideredirect(True)
        self.lb:tk.Listbox = tk.Listbox(self.popup, selectmode=tk.SINGLE, **kw)
        self.lb.pack(fill=tk.BOTH, expand=True)
        self.popup.withdraw()
        self.lb_up = False
        self.has_selected = False
        self.queue:queue.Queue = queue.Queue()

        Placeholder.__init__(self, parent, placeholder, **kw)
        self.traceid = self.var.trace_add('write', self.changed)

        # Create right click menu
        # @TODO: Use the _rc_menu_install function instead but generalize it for this and EntryPlus use
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

            self.var.trace_remove("write", self.traceid)

            self.var.set(self.lb.get(index))
            self.hide_list()
            self.icursor(tk.END)
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
            self.var.trace_remove("write", self.traceid)
        except:
            pass
        finally:
            self.delete(0, tk.END)
            self.insert(0, text)
            self.traceid = self.var.trace_add('write', self.changed)
