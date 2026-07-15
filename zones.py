import win32api
import win32con
import win32gui

import windows
from enums import AssignmentType
from models import Monitor, Zone


# ------------------------Defining Zone Manager Class------------------------
class ZoneManager:
    def __init__(self):
        self.monitors: list[Monitor] = []
        # ------------------------------------------------------------
        # Tracks whether we are currently creating/editing zones
        # ------------------------------------------------------------
        self.editor_mode = False
        # ------------------------------------------------------------
        # Reference to ZoneEditor
        # This gets assigned later in main.py:
        # zone_manager.editor = editor
        # We set it here so VS Code knows this attribute exists.
        # ------------------------------------------------------------
        self.editor = None

    # ------------------------finding defined zone and priority------------------------

    def find_best_zone(self, hwnd):
        """
        Finds the best available zone.

        Priority:
        1. Current monitor assigned zone (TITLE/EXE/CLASS)
        2. Any monitor assigned zone (TITLE/EXE/CLASS)
        3. Current monitor unassigned zone
        4. Any monitor unassigned zone
        """

        window_info = windows.get_window_info(hwnd)

        preferred_monitor = windows.get_monitor_for_window(hwnd)

        preferred = []
        others = []

        for monitor in self.monitors:
            if monitor.id == preferred_monitor:
                preferred.append(monitor)
            else:
                others.append(monitor)

        def find_assigned(monitors):
            for monitor in monitors:
                for zone in monitor.zones:

                    if zone.occupied_hwnd is not None:
                        continue

                    if zone.assignment is None:
                        continue

                    # assignment = zone.assignment

                    if self.zone_matches_window(zone, window_info):
                        return zone

            return None

        def find_unassigned(monitors):
            for monitor in monitors:
                for zone in monitor.zones:

                    if zone.occupied_hwnd is not None:
                        continue

                    if zone.assignment is None:
                        return zone

            return None

        # 1. Current monitor assigned
        zone = find_assigned(preferred)
        if zone:
            return zone

        # 2. Any monitor assigned
        zone = find_assigned(others)
        if zone:
            return zone

        # 3. Current monitor unassigned
        zone = find_unassigned(preferred)
        if zone:
            return zone

        # 4. Any monitor unassigned
        zone = find_unassigned(others)
        if zone:
            return zone

        print(f"No available zones for {window_info.title}")
        return None

    def zone_matches_window(self, zone, window_info):
        """
        Returns True if this zone assignment matches this window.
        """

        if zone.assignment is None:
            return False

        assignment = zone.assignment

        if assignment.type == AssignmentType.TITLE:
            return window_info.title == assignment.name

        elif assignment.type == AssignmentType.EXE:
            return window_info.exe == assignment.name

        elif assignment.type == AssignmentType.CLASS:
            return window_info.class_name == assignment.name

        return False

    def get_window_under_cursor(self):
        """
        Returns the root_hwnd from the window under the cursor.
        """
        x, y = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint((x, y))
        # WindowFromPoint often returns a child control, not the actual app window —
        # walk up to the top-level window
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        return root_hwnd

    def tile_under_cursor(self):
        """
        Main AHK-style action:
        Win + Right Click → tile window under cursor
        """

        # 1. Clean stale zones first, then rebuild occupied zones
        self.free_invalid_zones()

        self.sync_occupied_zones()

        # 2. Get target window
        hwnd = self.get_window_under_cursor()
        if not hwnd:
            return
        info = windows.get_window_info(hwnd)
        if not windows.is_tileable_window(hwnd):
            print(
                f"Title={info.title} Exe={info.exe} Class={info.class_name} is not tileable"
            )
            return
        # 3. If this window already occupies a zone, leave it alone.
        #    free_invalid_zones() above already cleared occupied_hwnd
        #    for any window that moved out of its zone or closed, so
        #    if we still find one here, it's genuinely still correctly
        #    placed — no need to touch it.
        current_zone = self.get_zone_for_hwnd(hwnd)
        if current_zone is not None:
            current_zone = self.get_zone_for_hwnd(hwnd)

            if current_zone is not None:

                if self.is_window_correctly_placed(hwnd, current_zone):
                    print(f"Window already correctly placed: {current_zone}")
                    return

                else:
                    print("Window belongs to zone but ZONE position changed. ")
                    print(f"Retiling to {current_zone}")

                    windows.move_window(
                        hwnd,
                        current_zone.x,
                        current_zone.y,
                        current_zone.width,
                        current_zone.height,
                    )

                    return

        # 4. Find the best zone for this window
        zone = self.find_best_zone(hwnd)

        if zone is None:
            return

        # 5. Move window
        print(
            f"Tiling <> Title={info.title} Exe={info.exe} Class={info.class_name} -> {zone}"
        )
        windows.move_window(hwnd, zone.x, zone.y, zone.width, zone.height)

        # 6. Mark zone as occupied
        zone.occupied_hwnd = hwnd
        self.debug_occupied_zones()

    def tile_all_windows(self):
        """
        Attempts to place every open application window
        into available zones.
        """

        # Clean stale occupancy first
        self.free_invalid_zones()
        windows_list = windows.enumerate_windows()

        for hwnd in windows_list:

            # Skip our own editor
            if self.editor and self.editor.overlay:
                if hwnd == self.editor.overlay.root.winfo_id():
                    continue

            # Already tiled?
            if self.get_zone_for_hwnd(hwnd):
                continue

            zone = self.find_best_zone(hwnd)

            if zone is None:
                print("No more zones available")
                break

            info = windows.get_window_info(hwnd)

            print(
                f"Tiling <> Title={info.title} Exe={info.exe} Class={info.class_name} -> {zone}"
            )

            windows.move_window(
                hwnd,
                zone.x,
                zone.y,
                zone.width,
                zone.height,
            )

            zone.occupied_hwnd = hwnd

    def is_window_alive(self, hwnd: int) -> bool:
        """
        Returns True if the window still exists in Windows.
        If a window is closed, minimized-to-death, or invalid,
        this returns False.
        """
        if hwnd is None:
            return False
        return win32gui.IsWindow(hwnd) != 0

    def free_invalid_zones(self):
        """
        Cleans BOTH:
        1. Dead windows (closed apps)
        2. Moved windows (no longer matching zone rules)
        """
        for monitor in self.monitors:
            for zone in monitor.zones:

                if zone.occupied_hwnd is None:
                    continue

                hwnd = zone.occupied_hwnd

                # 1. window closed
                if not self.is_window_alive(hwnd):
                    zone.occupied_hwnd = None
                    continue

                # 2. window moved out of zone
                if not self.window_is_in_zone(hwnd, zone):
                    zone.occupied_hwnd = None

    def sync_occupied_zones(self):
        """
        Rebuilds occupied_hwnd by checking what windows are currently
        physically inside zones.

        HWNDs are not saved, so this restores runtime state after launch.
        """
        all_windows = windows.enumerate_windows()

        for monitor in self.monitors:
            for zone in monitor.zones:

                # Don't overwrite an already tracked valid window
                if zone.occupied_hwnd is not None:
                    continue

                for hwnd in all_windows:

                    if self.window_is_in_zone(hwnd, zone):
                        zone.occupied_hwnd = hwnd

                        info = windows.get_window_info(hwnd)

                        print(
                            f"Synced zone occupied: " f"{info.title} -> {zone}"
                        )

                        break

    def window_is_in_zone(self, hwnd, zone):
        left, top, right, bottom = windows.get_window_rect(hwnd)

        zx1 = zone.x
        zy1 = zone.y
        zx2 = zone.x + zone.width
        zy2 = zone.y + zone.height

        # simple overlap check
        return left >= zx1 and top >= zy1 and right <= zx2 and bottom <= zy2

    def is_window_correctly_placed(self, hwnd, zone):
        """
        Returns True if the window position and size match the zone.
        """

        if hwnd is None:
            return False

        if not self.is_window_alive(hwnd):
            return False

        left, top, right, bottom = windows.get_window_rect(hwnd)

        window_width = right - left
        window_height = bottom - top

        tolerance = 10

        return (
            abs(left - zone.x) <= tolerance
            and abs(top - zone.y) <= tolerance
            and abs(window_width - zone.width) <= tolerance
            and abs(window_height - zone.height) <= tolerance
        )

    def get_zone_for_hwnd(self, hwnd):
        """
        Returns the zone currently occupied by this window, if any.
        Searches ALL zones (not just ones matching assignment rules) —
        if the window already lives somewhere, that's what matters here.
        """
        for monitor in self.monitors:
            for zone in monitor.zones:
                if zone.occupied_hwnd == hwnd:
                    return zone
        return None

    def debug_occupied_zones(self):
        """
        Prints current zone ownership.
        """
        for monitor in self.monitors:
            for zone in monitor.zones:
                if zone.occupied_hwnd:
                    print(
                        "ZONE OCCUPIED:",
                        zone.x,
                        zone.y,
                        "HWND:",
                        zone.occupied_hwnd,
                    )
                else:
                    print(
                        "ZONE EMPTY:",
                        zone.x,
                        zone.y,
                    )

    def add_zone(self, monitor, x, y, width, height, assignment=None):
        """
        Creates a new zone and adds it to a monitor.
        """

        zone = Zone(x=x, y=y, width=width, height=height, assignment=assignment)

        monitor.zones.append(zone)

        return zone

    def toggle_editor(self):
        """
        Enables/disables zone creation mode.
        """

        self.editor_mode = not self.editor_mode

        print("Editor mode:", self.editor_mode)

        if self.editor:
            self.editor.set_mode(self.editor_mode)

    def set_editor(self, editor):
        """
        Connects the ZoneManager to the ZoneEditor.

        ZoneManager handles the zone data.
        ZoneEditor handles the visual editing.
        They need a reference to communicate.
        """

        self.editor = editor

    def apply_assignments(self):
        """
        Finds windows matching zone assignments
        and moves them into their assigned zones.
        """

        print("Applying zone assignments...")

        self.free_invalid_zones()
        self.sync_occupied_zones()

        open_windows = windows.enumerate_windows()

        for monitor in self.monitors:
            for zone in monitor.zones:

                # Skip zones without assignments
                if zone.assignment is None:
                    continue

                # Skip occupied zones
                if zone.occupied_hwnd is not None:
                    continue

                for hwnd in open_windows:

                    info = windows.get_window_info(hwnd)

                    matches = False

                    if zone.assignment.type == AssignmentType.TITLE:
                        matches = info.title == zone.assignment.name

                    elif zone.assignment.type == AssignmentType.EXE:
                        matches = info.exe == zone.assignment.name

                    elif zone.assignment.type == AssignmentType.CLASS:
                        matches = info.class_name == zone.assignment.name

                    if matches:

                        print(f"Assignment match: " f"{info.title} -> {zone}")

                        windows.move_window(
                            hwnd,
                            zone.x,
                            zone.y,
                            zone.width,
                            zone.height,
                        )

                        zone.occupied_hwnd = hwnd

                        break
