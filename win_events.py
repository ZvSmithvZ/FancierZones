import ctypes
from ctypes import wintypes

import windows
from zones import ZoneManager

# -----------------------------------------------------------------------------
# Win32 user32.dll
# -----------------------------------------------------------------------------
user32 = ctypes.windll.user32

# -----------------------------------------------------------------------------
# Shared ZoneManager reference
# Assigned once during install_event_hooks() so the callback can access
# the application's zone logic.
# -----------------------------------------------------------------------------
zone_manager: ZoneManager | None = None


# -----------------------------------------------------------------------------
# WinEvent callback signature
# Unlike keyboard/mouse hooks, WinEvent hooks call a different callback.
# Parameters:
#   hWinEventHook   -> Handle returned by SetWinEventHook
#   event           -> Which Windows accessibility event fired
#   hwnd            -> Window associated with the event
#   idObject        -> Object identifier (OBJID_WINDOW for top-level windows)
#   idChild         -> Child object identifier
#   dwEventThread   -> Thread that generated the event
#   dwmsEventTime   -> Timestamp
# -----------------------------------------------------------------------------
WinEventProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)

user32.SetWinEventHook.restype = wintypes.HANDLE
user32.SetWinEventHook.argtypes = [
    wintypes.DWORD,  # eventMin
    wintypes.DWORD,  # eventMax
    wintypes.HMODULE,  # hmodWinEventProc
    WinEventProc,  # callback
    wintypes.DWORD,  # idProcess
    wintypes.DWORD,  # idThread
    wintypes.DWORD,  # flags
]

user32.UnhookWinEvent.argtypes = [
    wintypes.HANDLE,
]

# -----------------------------------------------------------------------------
# Event constants
# EVENT_OBJECT_SHOW
#     Fired whenever a UI object becomes visible.
# WINEVENT_OUTOFCONTEXT
#     Callback runs inside our own process instead of injecting into
#     every application.
# -----------------------------------------------------------------------------
EVENT_OBJECT_SHOW = 0x8002

WINEVENT_OUTOFCONTEXT = 0x0000

OBJID_WINDOW = 0


# -----------------------------------------------------------------------------
# WinEvent callback
# Called by Windows whenever an EVENT_OBJECT_SHOW notification occurs.
# -----------------------------------------------------------------------------
def win_event_proc(
    hWinEventHook,
    event,
    hwnd,
    idObject,
    idChild,
    dwEventThread,
    dwmsEventTime,
):
    if not zone_manager:
        return

    if not is_valid_window_event(hwnd):
        return

    if idObject != OBJID_WINDOW:
        return

    if not windows.is_tileable_window(hwnd):
        return

    info = windows.get_window_info(hwnd)

    print(
        "--Valid window shown--",
        f"HWND: {hwnd}",
        f"Title: {info.title}",
        f"Exe: {info.exe}",
        f"Class: {info.class_name}",
    )
    zone_manager.auto_assign_window(hwnd)


# -----------------------------------------------------------------------------
# ctypes callbacks MUST stay referenced or
# Python's garbage collector can free them, causing the hook to stop working.
# -----------------------------------------------------------------------------
_win_event_proc = WinEventProc(win_event_proc)


# -----------------------------------------------------------------------------
# Install WinEvent hook
# Registers with Windows to receive EVENT_OBJECT_SHOW notifications.
# -----------------------------------------------------------------------------
def install_event_hooks(manager: ZoneManager):
    global zone_manager

    zone_manager = manager

    hook = user32.SetWinEventHook(
        EVENT_OBJECT_SHOW,
        EVENT_OBJECT_SHOW,
        0,
        _win_event_proc,
        0,
        0,
        WINEVENT_OUTOFCONTEXT,
    )

    if not hook:
        raise OSError("Failed to install WinEvent hook")

    install_event_hooks.hook = hook

    print("[debug] WinEvent hook installed.")


# -----------------------------------------------------------------------------
# Remove WinEvent hook
# Call on application shutdown to cleanly unregister from Windows.
# -----------------------------------------------------------------------------
def uninstall_event_hooks():
    hook = getattr(install_event_hooks, "hook", None)

    if hook:
        user32.UnhookWinEvent(hook)


def is_valid_window_event(hwnd):
    """
    Determines whether a WinEvent callback belongs to a window
    FancierZones cares about.

    WinEvent fires for many UI objects, not just application windows,
    so we filter aggressively here.
    """

    if not hwnd:
        return False

    # Does this HWND still exist?
    if not user32.IsWindow(hwnd):
        return False

    # Ignore invisible objects
    if not user32.IsWindowVisible(hwnd):
        return False

    # Ignore child controls
    # A top-level app window has itself as its GA_ROOT ancestor.
    root = user32.GetAncestor(hwnd, 2)  # GA_ROOT = 2

    if root != hwnd:
        return False

    return True
