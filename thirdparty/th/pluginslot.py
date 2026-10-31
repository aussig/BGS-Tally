""" Move a plugin's panel up or down among EDMC's plugin panels, and restore its saved slot on load. """
import re
import tkinter as tk
from typing import Any

from config import config # type: ignore

_PLUGIN_RE:re.Pattern = re.compile(r"plugin_\d+")

class PluginSlot:
    """ Persist and restore this plugin's position among EDMC's plugin panels. """
    def __init__(self, widget:tk.Misc, key:str) -> None:
        self.key:str = key
        self.frame:tk.Misc|None = widget
        while self.frame is not None and not _PLUGIN_RE.fullmatch(self.frame.winfo_name()):
            self.frame = self.frame.master
        if self.frame is None or self.frame.master is None:
            self.frame = None
            return

        self.box:tk.Misc = self.frame.master
        # A Tcl var rather than a virtual event: Tk drops events to unmapped windows. It also works across th copies.
        self.frame.setvar(f"th_slot{self.frame}", self.frame.register(self._save))
        self.box.after_idle(self._restore)

    def move(self, step:int) -> bool:
        """ Move up (step<0) or down (step>0) one slot at a time, then save. """
        if self.frame is None: return False

        moved:list = []
        for _ in range(abs(step)):
            slots:list = self._slots()
            i:int = slots.index(self.frame) + (1 if step > 0 else -1)
            if not 0 <= i < len(slots): break
            self._swap(self.frame, slots[i])
            moved.append(slots[i])

        if not moved: return False

        self._save()
        for w in moved:
            cmd:str = self._cmd(w)
            if cmd: w.tk.call(cmd)
        return True

    def _save(self) -> None:
        config.set(self.key, self._slots().index(self.frame))

    def _cmd(self, w:tk.Misc) -> str:
        """ The save command another PluginSlot registered for this plugin frame, or '' for plain plugins. """
        var:str = f"th_slot{w}"
        return w.getvar(var) if int(w.tk.call('info', 'exists', var)) else ''

    def _slots(self) -> list:
        """ Gridded plugin frames in display order. """
        frames:list = [w for w in self.box.winfo_children() if _PLUGIN_RE.fullmatch(w.winfo_name()) and w.winfo_manager() == 'grid']
        return sorted(frames, key=lambda w: int(w.grid_info()['row']))

    def _place(self, w:Any, row:int) -> None:
        w.grid_configure(row=row)
        self.box.nametowidget(w.winfo_name().replace('plugin_', 'plugin_hr_')).grid_configure(row=row - 1)

    def _swap(self, a:Any, b:Any) -> None:
        ra:int = int(a.grid_info()['row'])
        self._place(a, int(b.grid_info()['row']))
        self._place(b, ra)

    def _restore(self, tries:int = 50) -> None:
        """ Jump to the saved slot, then put plugins that don't use PluginSlot back in load order. """
        # Plugins flush idle tasks during plugin_app; EDMC adds its update button once every plugin is gridded
        if 'update_button' not in self.box.children and tries > 0:
            self.box.after(100, self._restore, tries - 1)
            return

        slots:list = self._slots()
        target:int = config.get_int(self.key, default=-1)
        if target < 0 or self.frame not in slots: return

        target = min(target, len(slots) - 1)
        if slots[target] is not self.frame: self._swap(self.frame, slots[target])

        plain:list = [w for w in self._slots() if not self._cmd(w)]
        rows:list = sorted(int(w.grid_info()['row']) for w in plain)
        for w, row in zip(sorted(plain, key=lambda w: int(w.winfo_name()[7:])), rows):
            self._place(w, row)
