from models import Zone
from overlay import ZoneOverlay


class ZoneEditor:

    def __init__(self, zone_manager):
        """
        The editor receives the ZoneManager.

        ZoneManager owns:
        - monitors
        - zones
        - saving/loading

        ZoneEditor owns:
        - editing state
        - future mouse drawing
        """
        self.zone_manager = zone_manager

        # Tracks whether editor mode is active
        self.enabled = False

        # The visual overlay
        self.overlay = None

    def set_mode(self, enabled: bool):
        """
        Called by ZoneManager when F12 is pressed.

        True:
            Enable zone editing

        False:
            Disable zone editing
        """

        self.enabled = enabled

        if self.enabled:
            print("Zone Editor ENABLED")
            self.open_overlay()

        else:
            print("Zone Editor DISABLED")
            self.close_overlay()

    def open_overlay(self):
        """
        Opens the zone editing canvas.
        """

        self.overlay = ZoneOverlay(self.zone_manager.monitors)

        self.overlay.show()

    def close_overlay(self):
        """
        Closes the editor overlay.
        """

        if self.overlay:

            self.overlay.root.destroy()

            self.overlay = None

    def add_zone(self, monitor_id, x, y, width, height, assignment=None):
        """
        Creates a new zone and adds it to a monitor.
        """

        for monitor in self.zone_manager.monitors:

            if monitor.id == monitor_id:

                zone = Zone(x=x, y=y, width=width, height=height, assignment=assignment)

                monitor.zones.append(zone)

                print(f"Added zone to {monitor.id}: " f"{x},{y} {width}x{height}")

                return zone

        print(f"Monitor {monitor_id} not found")
        return None

    def remove_zone(self, monitor_id, zone_index):
        """
        Removes a zone by index.
        """

        for monitor in self.zone_manager.monitors:

            if monitor.id == monitor_id:

                if zone_index < len(monitor.zones):

                    removed = monitor.zones.pop(zone_index)

                    print(f"Removed zone {removed}")

                    return True

        return False
