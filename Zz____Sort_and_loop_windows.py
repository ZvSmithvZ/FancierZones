import win32con
import win32gui


def enum_windows():
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        rect = win32gui.GetWindowRect(hwnd)
        windows.append((hwnd, title, rect))

    win32gui.EnumWindows(callback, None)
    return windows


results = enum_windows()


def get_width(window):
    hwnd, title, rect = window
    left, top, right, bottom = rect
    return right - left


results_sorted = sorted(results, key=get_width)

for hwnd, title, rect in results_sorted:
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    print(f"{title}: {width} x {height}")


def find_window_by_title(partial_title):
    result = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if partial_title.lower() in title.lower():
            result.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return result


matches = find_window_by_title("Notepad")

if not matches:
    print("No matching window found")
else:
    hwnd = matches[0]
    print(f"Moving window: {win32gui.GetWindowText(hwnd)}")
    # win32gui.SetActiveWindow(hwnd)
    # if win32gui.IsZoomed(hwnd):
    #    print("It's maximized")
    win32gui.MoveWindow(hwnd, 100, 100, 640, 480, True)


# GetWindowPlacement returns a tuple with several pieces of info; index [1] is the show-state. This maps to your AHK MinMaxState (1 = max, -1 = min, 0 = normal)
def get_window_state(hwnd):
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]
    if show_cmd == win32con.SW_SHOWMAXIMIZED:
        return "maximized"
    elif show_cmd == win32con.SW_SHOWMINIMIZED:
        return "minimized"
    else:
        return "normal"


def move_window_safely(hwnd, x, y, w, h):
    if win32gui.IsZoomed(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.MoveWindow(hwnd, x, y, w, h, True)

    # activates window
    win32gui.SetForegroundWindow(hwnd)


def activate_window(hwnd):
    if win32gui.IsIconic(hwnd):  # IsIconic = "is minimized"
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
