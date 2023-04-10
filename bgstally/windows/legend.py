import tkinter as tk
from os import path
from tkinter import PhotoImage, ttk

from bgstally.constants import FOLDER_ASSETS, FONT_HEADING


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
        self.toplevel.resizable(False, False)

        frame_container:ttk.Frame = ttk.Frame(self.toplevel)
        frame_container.pack(fill=tk.BOTH, padx=5, pady=5, expand=1)

        current_row:int = 0
        ttk.Label(frame_container, text="Icons in BGS Reports", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_bgs_cz).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" On-ground Conflict Zone").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, text="🆉🅻🅷", font=("Helvetica", 24)).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Zero / Low / High demand level for trade buy / sell").grid(row=current_row, column=1, sticky=tk.W); current_row += 1

        ttk.Label(frame_container, text="Icons in Thargoid War Reports", font=FONT_HEADING).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, pady=4); current_row += 1
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
        ttk.Label(frame_container, image=self.image_icon_tw_mass_missions).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Massacre missions").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
        ttk.Label(frame_container, image=self.image_icon_tw_kills).grid(row=current_row, column=0)
        ttk.Label(frame_container, text=" Kills").grid(row=current_row, column=1, sticky=tk.W); current_row += 1
