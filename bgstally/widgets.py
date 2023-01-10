import tkinter as tk
from tkinter import END, ttk
import re
from bgstally.debug import Debug

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


class AnsiColorText(TextPlus):
    """
    class to convert text with ansi color codes to
    text with tkinter color tags

    for now we ignore all but the simplest color directives
    see http://www.termsys.demon.co.uk/vtansi.htm for a list of
    other directives

    it has not been thoroughly tested, but it works well enough for demonstration purposes
    """

    foreground_colors = {
        "bright": {
            "30": "Black",
            "31": "Red",
            "32": "Green",
            "33": "Brown",
            "34": "Blue",
            "35": "Purple",
            "36": "Cyan",
            "37": "White",
        },
        "dim": {
            "30": "DarkGray",
            "31": "LightRed",
            "32": "LightGreen",
            "33": "Yellow",
            "34": "LightBlue",
            "35": "Magenta",
            "36": "Pink",
            "37": "White",
        },
    }

    background_colors = {
        "bright": {
            "40": "Black",
            "41": "Red",
            "42": "Green",
            "43": "Brown",
            "44": "Blue",
            "45": "Purple",
            "46": "Cyan",
            "47": "White",
        },
        "dim": {
            "40": "DarkGray",
            "41": "LightRed",
            "42": "LightGreen",
            "43": "Yellow",
            "44": "LightBlue",
            "45": "Magenta",
            "46": "Pink",
            "47": "White",
        },
    }

    # define some regexes which will come in handy in filtering
    # out the ansi color codes
    color_pat = re.compile("\x01?\x1b(\[[\d+;]*m?)\x02?")
    inner_color_pat = re.compile("^\[(\d+;?)+m$")

    def __init__(self, *args, **kwargs):
        """
        initialize our specialized tkinter Text widget
        """
        TextPlus.__init__(self, *args, **kwargs)
        self.known_tags = set([])
        # register a default color tag
        self.register_tag("30", "White", "Black")
        self.reset_to_default_attribs()

    def reset_to_default_attribs(self):
        self.tag = "30"
        self.bright = "bright"
        self.foregroundcolor = "White"
        self.backgroundcolor = "Gray13"

    def register_tag(self, txt, foreground, background):
        """
        register a tag with name txt and with given
        foreground and background color
        """
        self.tag_config(txt, foreground=foreground, background=background)
        self.known_tags.add(txt)

    def write(self, text, is_editable=False):
        """
        add text to the text widget
        """

        # first split the text at color codes, stripping stuff like the <ESC>
        # and \[ characters and keeping only the inner "0;23"-like codes
        segments = AnsiColorText.color_pat.split(text)
        if segments:
            for text in segments:
                # a segment can be regular text, or it can be a color pattern
                if AnsiColorText.inner_color_pat.match(text):
                    # if it's a color pattern, check if we already have
                    # registered a tag for it
                    text = text[1:-1] # Strip leading '[' and trailing 'm'
                    if text not in self.known_tags:
                        # if tag not yet registered,
                        # extract the foreground and background color
                        # and ignore the other things
                        parts = text.split(";")
                        for part in parts:
                            if part in AnsiColorText.foreground_colors[self.bright]:
                                self.foregroundcolor = AnsiColorText.foreground_colors[
                                    self.bright
                                ][part]
                            elif part in AnsiColorText.background_colors[self.bright]:
                                self.backgroundcolor = AnsiColorText.background_colors[
                                    self.bright
                                ][part]
                            else:
                                for ch in part:
                                    if ch == "0":
                                        # reset all attributes
                                        self.reset_to_default_attribs()
                                    if ch == "1":
                                        # define bright colors
                                        self.bright = "bright"
                                    if ch == "2":
                                        # define dim colors
                                        self.bright = "dim"

                        self.register_tag(
                            text,
                            foreground=self.foregroundcolor,
                            background=self.backgroundcolor,
                        )
                    # remember that we switched to this tag
                    self.tag = text
                elif text == "":
                    # reset tag to black
                    self.tag = "30"  # black
                else:
                    # no color pattern, insert text with the currently selected
                    # tag
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
    w.menu.add_command(label="Cut")
    w.menu.add_command(label="Copy")
    w.menu.add_command(label="Paste")
    w.menu.add_separator()
    w.menu.add_command(label="Select all")

    w.menu.entryconfigure("Cut", command=lambda: w.focus_force() or w.event_generate("<<Cut>>"))
    w.menu.entryconfigure("Copy", command=lambda: w.focus_force() or w.event_generate("<<Copy>>"))
    w.menu.entryconfigure("Paste", command=lambda: w.focus_force() or w.event_generate("<<Paste>>"))
    w.menu.entryconfigure("Select all", command=w.event_select_all)
