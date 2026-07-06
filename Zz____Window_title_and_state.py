import win32con
import win32gui


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


def tile_window(hwnd, x, y, w, h):
    state = get_window_state(hwnd)
    if state in ("maximized", "minimized"):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    win32gui.SetForegroundWindow(hwnd)
    win32gui.MoveWindow(hwnd, x, y, w, h, True)


matches = find_window_by_title("Notepad")
if matches:
    tile_window(matches[0], 100, 100, 640, 480)
else:
    print("not found")
