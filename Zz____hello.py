name = "daniel"
zone_count = 5
is_active = True

# print(f"{name} has {zone_count} windows that are configured")


# window_names = ["Chrome", "firefox", "vscode"]

# print(window_names[1])

# window_names.append("safari")

# print(window_names)

# monitor = {"width": 1920, "height": 1080, "taskbar": "Bottom"}

# second_mon: dict[str, int | str | None] = {
#     "width": 1920,
#     "height": 1080,
#     "taskbar": "Bottom",
# }

# second_mon["fullscrene"] = "Yes"

# zones = [
#     {"ZoneID": 1, "WindowName": "Chrome", "Xcord": 10, "Ycord": 30},
#     {"ZoneID": 2, "WindowName": "Safari", "Xcord": 50, "Ycord": 100},
# ]

# print(monitor["width"])

# for w in window_names:
#     print(f"{w}")

# for key, value in monitor.items():
#     print(f"{value}")

# for index, value in enumerate(window_names):
#     print(f"{index}: {value}")

# test_zone = {"x": 100, "y": 100, "w": 400, "h": 300}


# def is_point_in_zone(px, py, test_zone):
#     if (px > test_zone["x"]) and (px < (test_zone["x"] + test_zone["w"])):
#         if (py > test_zone["y"]) and (py < (test_zone["y"] + test_zone["h"])):
#             return True
#         else:
#             return False
#     else:
#         return False


# cleaner version
# in_x = zone["x"] < px < zone["x"] + zone["w"]
# in_y = zone["y"] < py < zone["y"] + zone["h"]
# return in_x and in_y

# print(is_point_in_zone(50, 50, test_zone))

z = Zone(x=100, y=100, w=400, h=300)
print(z)
print(z.x)
z.assignment = "notepad"
print(z)


@dataclass
class Zone:
    x: int
    y: int
    w: int
    h: int
    assignment: str | None = None
    occupied_hwnd: int | None = None


@dataclass
class Monitor:
    zones: list[Zone] = field(default_factory=list)


mon = Monitor()
# print(mon)
mon.zones.append(Zone(x=0, y=0, w=640, h=480))
mon.zones.append(Zone(x=640, y=0, w=640, h=480))
mon.zones.append(Zone(x=740, y=0, w=340, h=280))
# print(mon)

test_zone = {"x": 100, "y": 100, "w": 400, "h": 300}


def is_point_in_zone(px, py, zone):
    in_x = px < zone.x < zone.x + zone.w
    in_y = py < zone.y < zone.y + zone.h
    return in_x and in_y


for each in mon.zones:
    print(f"X Value:{each.x} W Value: {each.w} ")


with open("monitor.json", "w") as f:
    json.dump(asdict(mon), f, indent=2)

with open("monitor.json", "r") as f:
    data = json.load(f)

    print(data)

zones = [Zone(**z) for z in data["zones"]]

print(zones)

zones = []
for z in data["zones"]:
    zones.append(Zone(**z))


def end():
    return
