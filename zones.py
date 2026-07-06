import win32api
import win32con
import win32gui

import windows
from models import Monitor


# ------------------------Defining Zone Manager Class------------------------
class ZoneManager:
    def __init__(self):
        self.monitors: list[Monitor] = []

    # ------------------------finding defined zone and priority------------------------

    def find_best_zone(self, window_info):
        """
        Logic to loop through zones to find a matching zone if one exists
        """
        all_zones = []
        for m in self.monitors:
            all_zones.extend(m.zones)
        unoccupied = [z for z in all_zones if z.occupied_hwnd is None]

        # priority 1: exact title match
        for zone in unoccupied:
            if zone.assignment == window_info["title"]:
                return zone

        # priority 2: exact exe/app match
        for zone in unoccupied:
            if zone.assignment == window_info["exe"]:
                return zone

        # priority 3: exact class match
        for zone in unoccupied:
            if zone.assignment == window_info["class"]:
                return zone

        # priority 4: "any" zone (assignment == None)
        for zone in unoccupied:
            if zone.assignment is None:
                return zone

        print(f"No available zone for {window_info['title']}")
        return None  # no zone available

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

        # 1. Clean stale zones first
        self.free_invalid_zones()

        # 2. Get target window
        hwnd = self.get_window_under_cursor()
        if not hwnd:
            return

        # 3. If this window already occupies a zone, leave it alone.
        #    free_invalid_zones() above already cleared occupied_hwnd
        #    for any window that moved out of its zone or closed, so
        #    if we still find one here, it's genuinely still correctly
        #    placed — no need to touch it.
        current_zone = self.get_zone_for_hwnd(hwnd)
        if current_zone is not None:
            print(f"Window is already tiled in {current_zone}")
            return

        # 3. Get window info
        info = windows.get_window_info(hwnd)

        # 4. Find best zone
        zone = self.find_best_zone(info)
        if zone is None:
            return

        # number 3 already covers this
        # 5. Skip if already correctly tiled
        # if self.is_window_correctly_placed(hwnd, zone):
        #     print(f"{info} Window is already placed")
        #     return
        # 6. Move window
        print(f"Moving {info} to {zone}")
        windows.move_window(hwnd, zone.x, zone.y, zone.width, zone.height)

        # 7. Mark zone as occupied
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


# ---------------- old function in zonemanager

# def tile_window_to_best_zone(self, hwnd):
#     """
#     Don't think I'm using this logic anymore
#     """
#     info = windows.get_window_info(hwnd)
#     zone = self.find_best_zone(info)

#     if zone is None:
#         print(f"No available zone for {info['title']}")
#         return

#     windows.move_window(hwnd, zone.x, zone.y, zone.width, zone.height)
#     zone.occupied_hwnd = hwnd
#     print(f"Tiled '{info['title']}' into zone at ({zone.x}, {zone.y})")


# def window_still_matches_zone(self, zone, hwnd):
#     """
#     Checks whether a window still belongs in its assigned zone.
#     """

#     if hwnd is None:
#         return False

#     if not self.is_window_alive(hwnd):
#         return False

#     # Get current window info
#     info = windows.get_window_info(hwnd)

#     # Compare against zone assignment rules
#     if zone.assignment is None:
#         return True  # "any zone" always valid

#     return (
#         zone.assignment == info["title"]
#         or zone.assignment == info["exe"]
#         or zone.assignment == info["class"]
#     )
