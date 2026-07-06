import psutil
import win32con
import win32gui
import win32process


# ------------------------getting info of the window------------------------
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


# ------------------------getting the state of the window------------------------


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


# ------------------------moving 1 window------------------------
def move_window(hwnd, x, y, w, h):
    state = get_window_state(hwnd)
    if state in ("maximized", "minimized"):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # win32gui.SetForegroundWindow(hwnd)
    win32gui.MoveWindow(hwnd, x, y, w, h, True)


# ------------------------getting windows current position------------------------
def get_window_rect(hwnd):
    return win32gui.GetWindowRect(hwnd)


# ------------------------------ old manual logic
# def find_window_by_title(partial_title):
#     result = []

#     def callback(hwnd, _):
#         # does the window exist
#         if not win32gui.IsWindowVisible(hwnd):
#             return
#         # grabbing title of window
#         title = win32gui.GetWindowText(hwnd)
#         # matching partial title and normalizing
#         if partial_title.lower() in title.lower():
#             result.append(hwnd)

#     # enumerate through all existing windows
#     win32gui.EnumWindows(callback, None)
#     return result
