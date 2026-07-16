from zones import ZoneManager


class EventRouter:
    def __init__(self, zone_manager: ZoneManager):
        self.zone_manager = zone_manager

    def handle(self, event_name: str):
        """
        Central place where input events map to actions
        """


# WIP
