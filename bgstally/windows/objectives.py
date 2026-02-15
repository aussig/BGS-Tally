import tkinter as tk
from datetime import UTC, datetime
from tkinter import ttk

from bgstally.activity import Activity
from bgstally.constants import COLOUR_HEADING_1, DATETIME_FORMAT_API, FONT_HEADING_1, FONT_HEADING_2, FONT_TEXT, FONT_SMALL
from bgstally.debug import Debug
from bgstally.objectivesmanager import MissionTargetType, MissionType
from bgstally.utils import _, __, get_by_path, human_format
from bgstally.widgets import CollapsibleFrame, TextPlus
from thirdparty.colors import *


class WindowObjectives:
    """
    Handles the Objectives window
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.toplevel: tk.Toplevel = None
        # We need a new canvas and scrollable frame to hold the collapsibles
        self.canvas: tk.Canvas = None
        self.scrollable_frame: ttk.Frame = None

        # List of current collapsible frames
        self.collapsibles: list = []

        # Track state across refreshes
        self.previous_objectives_hash: str = ""  # Hash of objectives data for change detection
        self.collapsible_states: dict = {}  # Maps mission identifier to open/closed state


    def show(self):
        """
        Show our window
        """
        if self.toplevel is not None and self.toplevel.winfo_exists():
            self.toplevel.lift()
            return

        self.toplevel = tk.Toplevel(self.bgstally.ui.frame)
        self.toplevel.title(_("{plugin_name} - Objectives").format(plugin_name=self.bgstally.plugin_name, )) # LANG: Objectives window title
        self.toplevel.iconphoto(False, self.bgstally.ui.image_logo_bgstally_32, self.bgstally.ui.image_logo_bgstally_16)
        self.toplevel.geometry("900x800")

        frm_container: ttk.Frame = ttk.Frame(self.toplevel)
        frm_container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(frm_container, text=self.bgstally.objectives_manager.get_title(), font=FONT_HEADING_1, foreground=COLOUR_HEADING_1).pack(anchor=tk.NW, padx=10, pady=5)

        # Create scrollable canvas for collapsibles
        frm_items: ttk.Frame = ttk.Frame(frm_container)
        frm_items.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        self.canvas = tk.Canvas(frm_items, highlightthickness=0)
        sb_objectives = tk.Scrollbar(frm_items, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure scrollregion when content size changes
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Create window for the scrollable frame
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Update the scrollable frame width to match canvas width
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas.configure(yscrollcommand=sb_objectives.set)

        sb_objectives.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind mousewheel scrolling when mouse enters/leaves the canvas
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Build collapsible objectives
        self._build_objectives()

        # Store initial hash for change detection
        objectives = self.bgstally.objectives_manager.get_objectives()
        self.previous_objectives_hash = self.bgstally.objectives_manager._get_objectives_hash(objectives)

        # Auto-refresh
        self.toplevel.after(5000, self._update_objectives)


    def _bind_mousewheel(self, event):
        """Bind mousewheel scrolling when mouse enters the canvas"""
        # Windows and MacOS
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)


    def _unbind_mousewheel(self, event):
        """Unbind mousewheel scrolling when mouse leaves the canvas"""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")


    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        if event.num == 5 or event.delta < 0:
            # Scroll down
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            # Scroll up
            self.canvas.yview_scroll(-1, "units")


    def _save_collapsible_states(self, objectives: list):
        """Save the current open/closed state of all collapsibles

        Args:
            objectives: List of objective dicts currently displayed
        """
        for idx, collapsible in enumerate(self.collapsibles):
            if idx < len(objectives):
                mission_key = self.bgstally.objectives_manager.get_mission_key(objectives[idx])
                # Prefer a public API on CollapsibleFrame if available, with a fallback
                if hasattr(collapsible, "is_open"):
                    state = collapsible.is_open()
                elif hasattr(collapsible, "get_state"):
                    state = collapsible.get_state()
                elif hasattr(collapsible, "get"):
                    state = collapsible.get()
                else:
                    # Fallback to private attribute for backwards compatibility
                    state = collapsible._variable.get()
                self.collapsible_states[mission_key] = bool(state)


    def _build_objectives(self):
        """Build collapsible sections for each objective"""
        objectives = self.bgstally.objectives_manager.get_objectives()

        # Filter out expired objectives first
        active_objectives = []
        for mission in objectives:
            mission_enddate: datetime = datetime.strptime(
                mission.get('enddate', datetime(3999, 12, 31, 23, 59, 59, 0, UTC).strftime(DATETIME_FORMAT_API)),
                DATETIME_FORMAT_API
            )
            mission_enddate = mission_enddate.replace(tzinfo=UTC)
            if mission_enddate >= datetime.now(UTC):
                active_objectives.append(mission)

        # Save current states before clearing (using the previous list of objectives)
        if hasattr(self, '_displayed_objectives'):
            self._save_collapsible_states(self._displayed_objectives)

        # Clear existing collapsibles
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.collapsibles = []

        if not active_objectives:
            ttk.Label(self.scrollable_frame, text=_("No objectives available"), font=FONT_TEXT).pack(pady=20)
            self._displayed_objectives = []
            return

        # Build collapsibles for each objective
        for idx, mission in enumerate(active_objectives):

            # Get mission details
            mission_title: str|None = mission.get('title')
            mission_priority: str|None = mission.get('priority', '0')
            mission_type: str|None = mission.get('type')

            # Priority stars
            priority_stars = self.bgstally.objectives_manager._get_priority_stars(mission_priority)

            # Build title for collapsible
            if mission_title:
                collapsed_text = f"▶ {priority_stars} {mission_title}"
                expanded_text = f"▼ {priority_stars} {mission_title}"
            else:
                default_title = self._get_default_title(mission_type)
                collapsed_text = f"▶ {priority_stars} {default_title}"
                expanded_text = f"▼ {priority_stars} {default_title}"

            # Determine initial state from saved states
            mission_key = self.bgstally.objectives_manager.get_mission_key(mission)
            initial_open_state = self.collapsible_states.get(mission_key, False)

            # Create collapsible frame
            collapsible = CollapsibleFrame(
                self.scrollable_frame,
                expanded_text=expanded_text,
                collapsed_text=collapsed_text,
                open=initial_open_state  # Restore previous state or default to closed
            )
            collapsible.pack(fill=tk.X, padx=5, pady=3)
            self.collapsibles.append(collapsible)

            # Build content inside collapsible
            self._build_objective_content(collapsible.frame, mission)

        # Store the objectives we just displayed for next refresh
        self._displayed_objectives = active_objectives


    def _get_default_title(self, mission_type: str|None) -> str:
        """Get default title based on mission type"""
        match mission_type:
            case MissionType.RECON: return _("Recon Mission")
            case MissionType.WIN_WAR: return _("Win a War")
            case MissionType.DRAW_WAR: return _("Draw a War")
            case MissionType.WIN_ELECTION: return _("Win an Election")
            case MissionType.DRAW_ELECTION: return _("Draw an Election")
            case MissionType.BOOST: return _("Boost a Faction")
            case MissionType.EXPAND: return _("Expand from a System")
            case MissionType.REDUCE: return _("Reduce a Faction")
            case MissionType.RETREAT: return _("Retreat a Faction from a System")
            case MissionType.EQUALISE: return _("Equalise two Factions")
            case _: return _("Objective")


    def _build_objective_content(self, parent: ttk.Frame, mission: dict):
        """Build the detailed content for an objective"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Mission metadata
        mission_type = mission.get('type', _("Unknown"))
        mission_system = mission.get('system') or _("Unknown")
        mission_faction = mission.get('faction') or _("Unknown")
        mission_description = mission.get('description')

        metadata_text = f"Type: {mission_type} | System: {mission_system} | Faction: {mission_faction}"
        ttk.Label(content_frame, text=metadata_text, font=FONT_SMALL, foreground="gray40").pack(anchor=tk.NW, pady=(0, 5))

        # Dates
        mission_startdate: datetime = datetime.strptime(mission.get('startdate', datetime.now(UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
        mission_startdate = mission_startdate.replace(tzinfo=UTC)
        mission_enddate: datetime = datetime.strptime(mission.get('enddate', datetime(3999, 12, 31, 23, 59, 59, 0, UTC).strftime(DATETIME_FORMAT_API)), DATETIME_FORMAT_API)
        mission_enddate = mission_enddate.replace(tzinfo=UTC)

        start_str = mission_startdate.strftime("%Y-%m-%d") if mission_startdate else "-"
        end_str = mission_enddate.strftime("%Y-%m-%d") if mission_enddate and mission_enddate.year < 3999 else "-"
        if start_str != "-" or end_str != "-":
            date_text = f"Start: {start_str} | End: {end_str}"
            ttk.Label(content_frame, text=date_text, font=FONT_SMALL, foreground="gray40").pack(anchor=tk.NW, pady=(0, 5))

        # Description
        if mission_description:
            ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
            desc_label = tk.Label(content_frame, text=mission_description, font=FONT_TEXT, justify=tk.LEFT, wraplength=800)
            desc_label.pack(anchor=tk.NW, pady=(0, 5))

        # Targets section
        targets = mission.get('targets', [])
        if targets:
            ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
            ttk.Label(content_frame, text=_("Targets:"), font=FONT_HEADING_2).pack(anchor=tk.NW, pady=(0, 5))

            # Get activity for progress calculation
            mission_activity: Activity = self.bgstally.activity_manager.query_activity(mission_startdate)

            for target_idx, target in enumerate(targets):
                target_text = self._format_target(target, mission, mission_activity)
                if target_text:
                    target_label = tk.Label(content_frame, text=target_text, font=FONT_TEXT, justify=tk.LEFT, wraplength=800)
                    target_label.pack(anchor=tk.NW, padx=10, pady=2)
                else:
                    Debug.logger.warning(f"[ObjectivesWindow] Target {target_idx + 1} returned empty text!")


    def _format_target(self, target: dict, mission: dict, mission_activity: Activity) -> str:
        """Format a single target for display"""
        target_system: str|None = target.get('system')
        if target_system == "" or target_system is None:
            target_system = mission.get('system') or "Unknown"

        target_faction: str|None = target.get('faction')
        if target_faction == "" or target_faction is None:
            target_faction = mission.get('faction') or "Unknown"

        target_station: str|None = target.get('station')
        system_activity: dict|None = mission_activity.get_system_by_name(target_system)
        faction_activity: dict|None = None if system_activity is None else get_by_path(system_activity, ['Factions', target_faction])

        status: str = ""
        target_type = target.get('type')

        match target_type:
            case MissionTargetType.VISIT:
                if target_station:
                    status, _ = self.bgstally.objectives_manager._get_status(target, True, numeric=False)
                    return f"{status} Access the market in station '{target_station}' in '{target_system}'"
                else:
                    status, _ = self.bgstally.objectives_manager._get_status(target, True, numeric=False)
                    return f"{status} Visit system '{target_system}'"

            case MissionTargetType.INF:
                progress_individual: int|None = None if faction_activity is None else \
                    sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity.get('MissionPoints', {}).items()) + \
                    sum((1 if k == 'm' else int(k)) * int(v) for k, v in faction_activity.get('MissionPointsSecondary', {}).items())
                status, target_overall = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="INF")
                if target_overall > 0:
                    return f"{status} Boost '{target_faction}' in '{target_system}'"
                elif target_overall < 0:
                    return f"{status} Undermine '{target_faction}' in '{target_system}'"
                else:
                    return f"{status} Boost '{target_faction}' in '{target_system}' with as much INF as possible"

            case MissionTargetType.BV:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('Bounties')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="CR")
                return f"{status} Bounty Vouchers for '{target_faction}' in '{target_system}'"

            case MissionTargetType.CB:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('CombatBonds')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="CR")
                return f"{status} Combat Bonds for '{target_faction}' in '{target_system}'"

            case MissionTargetType.EXPL:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('CartData')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="CR")
                return f"{status} Exploration Data for '{target_faction}' in '{target_system}'"

            case MissionTargetType.TRADE_PROFIT:
                progress_individual: int|None = None if faction_activity is None else sum(int(d.get('profit', 0)) for d in faction_activity.get('TradeSell', []))
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="CR")
                return f"{status} Trade Profit for '{target_faction}' in '{target_system}'"

            case MissionTargetType.BM_PROF:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('BlackMarketProfit')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="CR")
                return f"{status} Black Market Profit for '{target_faction}' in '{target_system}'"

            case MissionTargetType.GROUND_CZ:
                progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('GroundCZ', {}).values())
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="wins")
                return f"{status} Fight for '{target_faction}' at on-ground CZs in '{target_system}'"

            case MissionTargetType.SPACE_CZ:
                progress_individual: int|None = None if faction_activity is None else sum(faction_activity.get('SpaceCZ', {}).values())
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="wins")
                return f"{status} Fight for '{target_faction}' at in-space CZs in '{target_system}'"

            case MissionTargetType.MURDER:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('Murdered')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="kills")
                return f"{status} Murder '{target_faction}' ships in '{target_system}'"

            case MissionTargetType.MISSION_FAIL:
                progress_individual: int|None = None if faction_activity is None else faction_activity.get('MissionFailed')
                status, _ = self.bgstally.objectives_manager._get_status(target, True, progress_individual=progress_individual, label="fails")
                return f"{status} Fail missions against '{target_faction}' in '{target_system}'"

        Debug.logger.warning(f"[ObjectivesWindow] No case matched for target_type: {target_type}, returning empty string")
        return ""


    def _update_objectives(self):
        """Refresh the objectives"""
        if not self.toplevel or not self.toplevel.winfo_exists():
            return

        # Get current objectives data
        objectives = self.bgstally.objectives_manager.get_objectives()

        # Use shared hash function for efficient change detection
        current_objectives_hash = self.bgstally.objectives_manager._get_objectives_hash(objectives)

        # Only rebuild if data has changed
        if current_objectives_hash != self.previous_objectives_hash:
            self._build_objectives()
            self.previous_objectives_hash = current_objectives_hash

        # Schedule next update
        self.toplevel.after(5000, self._update_objectives)
