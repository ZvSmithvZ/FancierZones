from zones import ZoneManager


class EventRouter:
    def __init__(self, zone_manager: ZoneManager):
        self.zone_manager = zone_manager

    def handle(self, event_name: str):
        """
        Central place where input events map to actions
        """

        if event_name == "tile_under_cursor":
            hwnd = self.zone_manager.get_window_under_cursor()
            if hwnd:
                self.zone_manager.tile_window_to_best_zone(hwnd)
