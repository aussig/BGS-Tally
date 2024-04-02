import tkinter as tk
from os import path
from tkinter import PhotoImage, ttk

from bgstally.constants import COLOUR_HEADING_1, FOLDER_ASSETS, FONT_HEADING_1


class WindowLegend:
    """
    Handles a window showing the Discord legend / key window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.image_icon_bgs_cz:PhotoImage = PhotoImage(file = path.join(self.bgstally.plugin_dir, FOLDER_ASSETS, "icon_bgs_cz.png"))
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

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(f"{self.bgstally.plugin_name} - Icon Legend")
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.resizable(False, False)

        frame_container:ttk.Frame = ttk.Frame(self.toplevel)
        frame_container.pack(fill=tk.BOTH, padx=5, pady=5, expand=1)

        current_row:int = 0
        ttk.Label(frame_container, text="Icons in BGS Reports", font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        ttk.Label(frame_container, text="🅟", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Primary INF. This is INF gained for the mission issuing faction.").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, text="🅢", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Secondary INF. This is INF gained as a secondary effect of the mission, for example the destination faction for delivery missions.").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, text="➊ ➋ ➌ ➍ ➎", font=("Helvetica", 14)).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Detailed INF split into + / ++ / +++ / ++++ / +++++ received from missions.").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_bgs_cz).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" On-ground Conflict Zone").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, text="🆉 🅻 🅼 🅷", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Zero / Low / Med / High demand level for trade buy / sell").grid(row=current_row, column=1, sticky=tk.W); current_row += 1

        ttk.Label(frame_container, text="Icons in Thargoid War Reports", font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_passengers).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Passenger missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_cargo).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Cargo missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_injured).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Injured evacuation missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_wounded).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Wounded evacuation missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_crit_wounded).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Critically wounded evacuation missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_reactivate).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Reactivation missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_mass_missions).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Massacre missions\n" \
                                        + "   S - Scout\n" \
                                        + "   C - Cyclops\n" \
                                        + "   B - Basilisk\n" \
                                        + "   M - Medusa\n" \
                                        + "   H - Hydra\n" \
                                        + "   O - Orthrus").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_kills).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Kills\n" \
                                        + "   R - Revenant\n" \
                                        + "   S - Scout\n" \
                                        + "   S/G - Scythe / Glaive (Cannot be automatically distinguised)\n" \
                                        + "   C - Cyclops\n" \
                                        + "   B - Basilisk\n" \
                                        + "   M - Medusa\n" \
                                        + "   H - Hydra\n" \
                                        + "   O - Orthrus").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_sr_bbs).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Search & Rescue Black Boxes").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_sr_pods).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Search & Rescue Escape Pods").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_sr_tissue).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Search & Rescue Tissue Samples").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_sr_tps).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Search & Rescue Bio Pods").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
