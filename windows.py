import psutil
import win32api
import win32con
import win32gui
import win32process

from models import Monitor, WindowInfo


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

    return WindowInfo(
        hwnd=hwnd,
        title=title,
        exe=exe_name,  # type: ignore
        class_name=class_name,  # type: ignore
    )


def enumerate_windows():
    """
    Returns every visible top-level window.
    """
    windows = []

    def callback(hwnd, _):

        if not is_tileable_window(hwnd):
            return

        # windows.append(get_window_info(hwnd))
        windows.append(hwnd)

    win32gui.EnumWindows(callback, None)

    return windows


def is_tileable_window(hwnd):
    """
    Determines whether a window should appear in Tile All.

    Filters out:
    - Desktop
    - Windows system UI
    - Hidden windows
    - Empty titles
    - Minimized windows
    """

    if not win32gui.IsWindowVisible(hwnd):
        return False

    # ignoring minimized windows for now
    if win32gui.IsIconic(hwnd):
        return False

    title = win32gui.GetWindowText(hwnd)

    if not title.strip():
        return False

    class_name = win32gui.GetClassName(hwnd)

    ignored_classes = {
        "Progman",
        "WorkerW",
        "Windows.UI.Core.CoreWindow",
        "ApplicationFrameWindow",
    }

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        # grabs the process name from pid
        process = psutil.Process(pid)
        exe_name = process.name()  # e.g. "notepad.exe"
    except psutil.NoSuchProcess:
        exe_name = None

    ignored_exes = {"code.exe"}

    if class_name in ignored_classes or exe_name in ignored_exes:
        return False

    return True


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


# ------------------------auto grabbing all mon coords------------------------
def detect_monitors():
    """
    Detect every monitor currently connected to Windows.
    Returns:
        list[Monitor]
    """
    monitors = []

    # EnumDisplayMonitors returns:
    # (monitor_handle, monitor_area, work_area)
    for hmonitor, monitor_rect, work_rect in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(int(hmonitor))
        left, top, right, bottom = info["Monitor"]

        monitors.append(
            Monitor(
                id=info["Device"],
                x=left,
                y=top,
                width=right - left,
                height=bottom - top,
                zones=[],
            )
        )

    return monitors


def get_monitor_for_window(hwnd):
    """
    Returns the Windows monitor that contains
    the center of this window.
    """

    hmonitor = win32api.MonitorFromWindow(
        hwnd, win32con.MONITOR_DEFAULTTONEAREST
    )

    info = win32api.GetMonitorInfo(hmonitor)

    return info["Device"]


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
