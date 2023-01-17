import tkinter as tk
from tkinter import CURRENT, END, ttk
import re
from bgstally.constants import FONT_TEXT, FONT_TEXT_BOLD, FONT_TEXT_UNDERLINE, FONT_TEXT_BOLD_UNDERLINE
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
    color_pat = re.compile("\x01?\x1b(\[[\d+;]*m?)\x02?")
    inner_color_pat = re.compile("^\[(\d+;?)+m$")

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
    w.menu.add_command(label="Cut")
    w.menu.add_command(label="Copy")
    w.menu.add_command(label="Paste")
    w.menu.add_separator()
    w.menu.add_command(label="Select all")

    w.menu.entryconfigure("Cut", command=lambda: w.focus_force() or w.event_generate("<<Cut>>"))
    w.menu.entryconfigure("Copy", command=lambda: w.focus_force() or w.event_generate("<<Copy>>"))
    w.menu.entryconfigure("Paste", command=lambda: w.focus_force() or w.event_generate("<<Paste>>"))
    w.menu.entryconfigure("Select all", command=w.event_select_all)



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
