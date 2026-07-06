from dataclasses import dataclass, field

import keyboard
import mouse
import psutil
import win32api
import win32con
import win32gui
import win32process


# ------------------------defining our dataclasses for import/export to json functionality------------------------
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


# ------------------------getting window information------------------------
def find_window_by_title(partial_title):
    result = []

    def callback(hwnd, _):
        # does the window exist
        if not win32gui.IsWindowVisible(hwnd):
            return
        # grabbing title of window
        title = win32gui.GetWindowText(hwnd)
        # matching partial title and normalizing
        if partial_title.lower() in title.lower():
            result.append(hwnd)

    # enumerate through all existing windows
    win32gui.EnumWindows(callback, None)
    return result


def get_window_info(hwnd):
    title = win32gui.GetWindowText(hwnd)
    class_name = win32gui.GetClassName(hwnd)

    # only keeping the process id not the thread id
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        # grabs the process name from pid
        process = psutil.Process(pid)
        exe_name = process.name()  # e.g. "notepad.exe"
    except psutil.NoSuchProcess:
        exe_name = None

    return {"title": title, "exe": exe_name, "class": class_name}


def get_window_state(hwnd):
    # takes hwnd and returns flags, showCmd, (minposX, minposY), (maxposX, maxposY), (normalposX, normalposY) ----minamized, maximized and restored
    placement = win32gui.GetWindowPlacement(hwnd)
    # showCmd from placement returns -1 for min, 0 for restored, 1 for max
    show_cmd = placement[1]
    #############################    This seems reduntant
    if show_cmd == win32con.SW_SHOWMAXIMIZED:
        return "maximized"
    elif show_cmd == win32con.SW_SHOWMINIMIZED:
        return "minimized"
    else:
        return "normal"


# ------------------------activating window------------------------
def activate_window(hwnd):
    if win32gui.IsIconic(hwnd):  # IsIconic = "is minimized"
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


# ------------------------finding defined zone------------------------
def find_best_zone(window_info, zones):
    # zones is a list of Zone objects, each with an `assignment` and `occupied_hwnd`

    unoccupied = [z for z in zones if z.occupied_hwnd is None]

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

    return None  # no zone available


# ------------------------tile 1 window------------------------
def tile_window(hwnd, x, y, w, h):
    state = get_window_state(hwnd)
    if state in ("maximized", "minimized"):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    win32gui.SetForegroundWindow(hwnd)
    win32gui.MoveWindow(hwnd, x, y, w, h, True)


def tile_window_to_best_zone(hwnd, zones):
    info = get_window_info(hwnd)
    zone = find_best_zone(info, zones)

    if zone is None:
        print(f"No available zone for {info['title']}")
        return

    tile_window(hwnd, zone.x, zone.y, zone.w, zone.h)
    zone.occupied_hwnd = hwnd
    print(f"Tiled '{info['title']}' into zone at ({zone.x}, {zone.y})")


# ------------------------manually testing------------------------
zones = [
    Zone(x=0, y=0, w=640, h=480, assignment="notepad.exe"),
    Zone(x=640, y=0, w=640, h=480, assignment=None),  # "any" zone
]

# matches = find_window_by_title("Notepad")
# if matches:
#     tile_window_to_best_zone(matches[0], zones)

# print(zones)

# ------------------------win + right click to tile------------------------


def get_window_under_cursor():
    x, y = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    # WindowFromPoint often returns a child control, not the actual app window —
    # walk up to the top-level window
    root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    return root_hwnd


# def suppress_start_menu():
#     # Tricks Windows into thinking Win was used in a combo,
#     # so it won't open the Start Menu when Win is released.
#     win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
#     win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


# def on_right_click():
#     win_key_down = win32api.GetAsyncKeyState(win32con.VK_LWIN) & 0x8000
#     if not win_key_down:
#         return  # right-click without Win held — ignore, let it act normally

#     suppress_start_menu()

#     hwnd = get_window_under_cursor()
#     if hwnd == 0:
#         return

#     tile_window_to_best_zone(hwnd, zones)


# mouse.on_right_click(on_right_click)

# print("Listening for Win + Right Click... press Ctrl+C to stop")

# while True:
#     time.sleep(0.1)


def on_right_click():
    if keyboard.is_pressed("windows"):
        print("Windows + Right Click")
        hwnd = get_window_under_cursor()
        if hwnd == 0:
            return
        tile_window_to_best_zone(hwnd, zones)


mouse.on_right_click(on_right_click)
print("Waiting for ctrl + alt + ` to stop")
keyboard.wait("ctrl+alt+`")
