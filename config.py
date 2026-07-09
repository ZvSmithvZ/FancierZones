import json
from pathlib import Path

import windows
from enums import AssignmentType
from models import Assignment, Monitor, Zone

CONFIG_PATH = Path("config.json")


def load_config() -> list[Monitor]:
    """
    Loads config.json and returns a list of Monitor objects.
    """

    with open(CONFIG_PATH, "r") as file:
        data = json.load(file)

    monitors = []

    for monitor_data in data["monitors"]:

        monitor = Monitor(
            id=monitor_data["id"],
            x=monitor_data["x"],
            y=monitor_data["y"],
            width=monitor_data["width"],
            height=monitor_data["height"],
        )

        for zone_data in monitor_data["zones"]:

            assignment = None

            if zone_data.get("assignment"):
                assignment_data = zone_data["assignment"]
                assignment = Assignment(
                    type=AssignmentType(assignment_data["type"]),
                    name=assignment_data["name"],
                )

            monitor.zones.append(
                Zone(
                    x=zone_data["x"],
                    y=zone_data["y"],
                    width=zone_data["width"],
                    height=zone_data["height"],
                    assignment=assignment,
                )
            )

        monitors.append(monitor)

    return monitors


def merge_monitors():
    """
    Detects the monitors currently connected to Windows and
    merges in any saved zones from config.json.
    Returns:
        list[Monitor]
    """

    # Physical monitors connected right now
    detected_monitors = windows.detect_monitors()

    # Saved monitors/zones from config.json
    saved_monitors = load_config()

    # Match monitors by their Windows device ID
    saved_lookup = {monitor.id: monitor for monitor in saved_monitors}

    for detected in detected_monitors:

        saved = saved_lookup.get(detected.id)

        if saved:
            # Keep the newly detected monitor position/size,
            # but restore all saved zones.
            detected.zones = saved.zones

    return detected_monitors


def save_config(monitors: list[Monitor]) -> None:
    """
    Saves the current monitor and zone layout to config.json.
    """

    data = {"monitors": []}

    for monitor in monitors:

        monitor_data = {
            "id": monitor.id,
            "x": monitor.x,
            "y": monitor.y,
            "width": monitor.width,
            "height": monitor.height,
            "zones": [],
        }

        for zone in monitor.zones:

            assignment_data = None

            if zone.assignment:
                assignment_data = {
                    "type": (
                        zone.assignment.type.value
                        if zone.assignment.type
                        else None
                    ),
                    "name": zone.assignment.name,
                }
            zone_data = {
                "x": zone.x,
                "y": zone.y,
                "width": zone.width,
                "height": zone.height,
                "assignment": assignment_data,
            }

            monitor_data["zones"].append(zone_data)

        data["monitors"].append(monitor_data)

    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)
