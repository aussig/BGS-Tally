import tkinter as tk
from os import path
from tkinter import PhotoImage, ttk

from bgstally.constants import COLOUR_HEADING_1, FOLDER_ASSETS, FONT_HEADING_1, FONT_TEXT
from bgstally.utils import _, __


class WindowLegend:
    """
    Handles a window showing the Discord legend / key window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.image_icon_bgs_cz:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz.png"))
        self.image_icon_bgs_cz_cs:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz_cs.png"))
        self.image_icon_bgs_cz_so:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz_so.png"))
        self.image_icon_bgs_cz_cp:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz_cp.png"))
        self.image_icon_bgs_cz_pr:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz_pr.png"))
        self.image_icon_tw_cargo:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_cargo.png"))
        self.image_icon_tw_crit_wounded:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_crit_wounded.png"))
        self.image_icon_tw_injured:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_injured.png"))
        self.image_icon_tw_passengers:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_passengers.png"))
        self.image_icon_tw_wounded:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_wounded.png"))
        self.image_icon_tw_mass_missions:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_mass_missions.png"))
        self.image_icon_tw_kills:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_kills.png"))
        self.image_icon_tw_sr_bbs:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_sr_bbs.png"))
        self.image_icon_tw_sr_pods:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_sr_pods.png"))
        self.image_icon_tw_sr_tissue:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_sr_tissue.png"))
        self.image_icon_tw_sr_tps:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_sr_tps.png"))
        self.image_icon_tw_reactivate:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_tw_reactivate.png"))

        self.toplevel:tk.Toplevel = None


    def show(self):
        """
        Show the window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        self.toplevel: tk.Toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - Icon Legend").format(plugin_name=self.bgstally.plugin_name)) # LANG: Legend window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("1050x800")
        self.toplevel.resizable(False, True)

        frame_container: ttk.Frame = ttk.Frame(self.toplevel)
        frame_container.pack(fill=tk.BOTH, padx=5, pady=5, expand=tk.YES)

        self.cnv_contents: tk.Canvas = tk.Canvas(frame_container)
        self.cnv_contents.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        scr_contents: ttk.Scrollbar = ttk.Scrollbar(frame_container, orient=tk.VERTICAL, command=self.cnv_contents.yview)
        scr_contents.pack(side=tk.RIGHT, fill=tk.Y)

        self.cnv_contents.configure(yscrollcommand=scr_contents.set)
        self.cnv_contents.bind('<Configure>', lambda e: self.cnv_contents.configure(scrollregion=self.cnv_contents.bbox("all")))
        self.cnv_contents.bind('<Enter>', self._bind_mousewheel)
        self.cnv_contents.bind('<Leave>', self._unbind_mousewheel)

        frame_contents: ttk.Frame = ttk.Frame(self.cnv_contents, width=1000, height=1000)
        frame_contents.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        current_row:int = 0
        ttk.Label(frame_contents, text=_("Icons in BGS Reports"), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1 # LANG: Heading on legend window
        ttk.Label(frame_contents, text="🅟", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Primary INF. This is INF gained for the mission issuing faction.")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, text="🅢", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Secondary INF. This is INF gained as a secondary effect of the mission, for example the destination faction for delivery missions.")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, text="1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣", font=FONT_TEXT).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Detailed INF split into + / ++ / +++ / ++++ / +++++ received from missions.")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_bgs_cz).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("On-ground Conflict Zone")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, text="🆉 🅻 🅼 🅷", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Zero / Low / Med / High demand level for trade buy / sell")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_bgs_cz_cs).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("In-space Conflict Zone Side Objective: Cap ship")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_bgs_cz_so).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("In-space Conflict Zone Side Objective: Spec ops wing")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_bgs_cz_cp).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("In-space Conflict Zone Side Objective: Enemy captain")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_bgs_cz_pr).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("In-space Conflict Zone Side Objective: Propaganda wing")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window

        ttk.Label(frame_contents, text=_("Icons in Thargoid War Reports"), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1 # LANG: Heading on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_passengers).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Passenger missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_cargo).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Cargo missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_injured).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Injured evacuation missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_wounded).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Wounded evacuation missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_crit_wounded).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Critically wounded evacuation missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_reactivate).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Reactivation missions")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_mass_missions).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Massacre missions") + "\n" \
                                        + "   S - Scout" + "\n" \
                                        + "   C - Cyclops" + "\n" \
                                        + "   B - Basilisk" + "\n" \
                                        + "   M - Medusa" + "\n" \
                                        + "   H - Hydra" + "\n" \
                                        + "   O - Orthrus").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_contents, image=self.image_icon_tw_kills).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Kills") + "\n" \
                                        + "   R - Revenant\n" \
                                        + "   S - Scout\n" \
                                        + "   S/G - Scythe / Glaive " + _("(Cannot be automatically distinguished)") + "\n" \
                                        + "   C - Cyclops\n" \
                                        + "   B - Basilisk\n" \
                                        + "   M - Medusa\n" \
                                        + "   H - Hydra\n" \
                                        + "   O - Orthrus").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_contents, image=self.image_icon_tw_sr_bbs).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Search & Rescue Black Boxes")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_sr_pods).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Search & Rescue Escape Pods")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_sr_tissue).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Search & Rescue Tissue Samples")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window
        ttk.Label(frame_contents, image=self.image_icon_tw_sr_tps).grid(row=current_row, column=0)
        ttk.Label(frame_contents, text=" " + _("Search & Rescue Bio Pods")).grid(row=current_row, column=1, sticky=tk.W); current_row += 1 # LANG: Label on legend window

        self.cnv_contents.create_window((0, 0), window=frame_contents, anchor=tk.NW)


    def _bind_mousewheel(self, event: tk.Event):
        """Handles an `<Enter>` event. Bind the mousewheel.

        Args:
            event (tk.Event): The triggering event
        """
        self.cnv_contents.bind_all("<MouseWheel>", self._on_mousewheel)


    def _unbind_mousewheel(self, event: tk.Event):
        """Handles a `<Leave>` event. Unbind the mousewheel.

        Args:
            event (tk.Event): The triggering event
        """
        self.cnv_contents.unbind_all("<MouseWheel>")


    def _on_mousewheel(self, event: tk.Event):
        """Handles a `<MouseWheel>` event. Scroll the canvas.

        Args:
            event (tk.Event): The triggering event
        """
        self.cnv_contents.yview_scroll(int(-1*(event.delta/120)), "units")
