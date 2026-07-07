from models import Zone


class ZoneEditor:

    def __init__(self, zone_manager):
        self.zone_manager = zone_manager

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
