import tkinter as tk

class HarnessClipboard:
    """In-memory clipboard mock so tests never touch the real system clipboard, and can
    assert on what copy_to_clipboard() actually wrote instead of mocking it at each call site."""

    def __init__(self) -> None:
        self._content:str = ''
        self._installed:bool = False
        self._orig_clear = None
        self._orig_append = None
        self._orig_get = None

    def install(self) -> None:
        """Install Tk clipboard monkeypatches."""
        if self._installed:
            return

        self._orig_clear = tk.Misc.clipboard_clear
        self._orig_append = tk.Misc.clipboard_append
        self._orig_get = tk.Misc.clipboard_get

        clipboard = self

        def patched_clear(self, *args, **kwargs):
            clipboard._content = ''

        def patched_append(self, string, *args, **kwargs):
            clipboard._content += string

        def patched_get(self, *args, **kwargs):
            return clipboard._content

        tk.Misc.clipboard_clear = patched_clear  # type: ignore[assignment]
        tk.Misc.clipboard_append = patched_append  # type: ignore[assignment]
        tk.Misc.clipboard_get = patched_get  # type: ignore[assignment]
        self._installed = True

    def uninstall(self) -> None:
        """Restore original Tk clipboard behavior."""
        if not self._installed:
            return

        if self._orig_clear is not None:
            tk.Misc.clipboard_clear = self._orig_clear
        if self._orig_append is not None:
            tk.Misc.clipboard_append = self._orig_append
        if self._orig_get is not None:
            tk.Misc.clipboard_get = self._orig_get

        self._installed = False

    def get(self) -> str:
        """Return whatever's currently in the mock clipboard."""
        return self._content

    def clear(self) -> None:
        self._content = ''
