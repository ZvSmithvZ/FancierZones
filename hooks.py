import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui

from zones import ZoneManager

# ------------------------------------------------------------
# Windows Hook Types
# ------------------------------------------------------------

WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13

# ------------------------------------------------------------
# Virtual Key Codes
# ------------------------------------------------------------

VK_LWIN = 0x5B
VK_RWIN = 0x5C

# ------------------------------------------------------------
# Mouse event constants
# ------------------------------------------------------------

WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

# ------------------------------------------------------------
# Keyboard event constants
# ------------------------------------------------------------

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104  # Win-key events sometimes arrive as SYS variants
WM_SYSKEYUP = 0x0105

# ------------------------------------------------------------
# Cross-version safe Windows pointer types
# ------------------------------------------------------------

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
ULONG_PTR = (
    ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
)


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


MouseProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
KeyboardProc = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32 = ctypes.windll.user32
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = LRESULT

zone_manager: ZoneManager | None = None

# ------------------------------------------------------------
# Combo state tracking
#
# combo_in_progress:
#     True from the moment we swallow a Win+RightButtonDown,
#     until we've also swallowed the matching RightButtonUp.
#     This is what lets us block BOTH halves of the click.
#
# win_used_as_modifier:
#     True once we've actually fired a tile action using Win
#     as a modifier. Only in this case do we swallow the next
#     Win key-up — this is what prevents the Start Menu from
#     opening afterward. A plain Win tap (no click involved)
#     never sets this, so it's never affected.
# ------------------------------------------------------------

combo_in_progress = False
win_used_as_modifier = False


def is_win_key_down():
    left = win32api.GetAsyncKeyState(VK_LWIN) & 0x8000
    right = win32api.GetAsyncKeyState(VK_RWIN) & 0x8000
    return bool(left or right)


def get_window_under_cursor():
    x, y = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    return win32gui.GetAncestor(hwnd, win32con.GA_ROOT)


# ------------------------------------------------------------
# Mouse Hook Callback
# ------------------------------------------------------------


def low_level_mouse_proc(nCode, wParam, lParam):
    global combo_in_progress, win_used_as_modifier

    if nCode == 0:

        if wParam == WM_RBUTTONDOWN and is_win_key_down():
            print("WIN + RIGHT CLICK (down)")
            combo_in_progress = True
            win_used_as_modifier = True

            if zone_manager:
                zone_manager.tile_under_cursor()
            else:
                print("Zone manager missing")

            return 1  # swallow the down-half of the click

        if wParam == WM_RBUTTONUP and combo_in_progress:
            print("WIN + RIGHT CLICK (up) - swallowing to prevent context menu")
            combo_in_progress = False
            return 1  # swallow the up-half too, so no context menu appears

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# ------------------------------------------------------------
# Keyboard Hook Callback
#
# This hook does almost nothing — it only ever swallows a Win
# key-up, and only immediately after that Win press was actually
# used as a modifier for our hotkey. A normal, lone Win tap never
# triggers win_used_as_modifier, so it's completely untouched and
# the Start Menu opens exactly as it would with no hook installed.
# ------------------------------------------------------------


def low_level_keyboard_proc(nCode, wParam, lParam):
    global win_used_as_modifier

    if nCode == 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        if kb.vkCode in (VK_LWIN, VK_RWIN):
            if wParam in (WM_KEYUP, WM_SYSKEYUP):
                if win_used_as_modifier:
                    print("Swallowing Win key-up to suppress Start Menu")
                    win_used_as_modifier = False
                    return 1  # block only this keyup

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# ------------------------------------------------------------
# Install hooks
# ------------------------------------------------------------


def install_hooks(manager: ZoneManager):
    global zone_manager
    zone_manager = manager

    mouse_callback = MouseProc(low_level_mouse_proc)
    keyboard_callback = KeyboardProc(low_level_keyboard_proc)

    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, None, 0)
    keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, keyboard_callback, None, 0)

    if not mouse_hook:
        raise OSError(f"Failed to install mouse hook. Error: {ctypes.GetLastError()}")
    if not keyboard_hook:
        raise OSError(
            f"Failed to install keyboard hook. Error: {ctypes.GetLastError()}"
        )

    print(f"Mouse hook installed (handle={mouse_hook})")
    print(f"Keyboard hook installed (handle={keyboard_hook})")

    # Keep references alive so Python doesn't garbage-collect
    # the callbacks while Windows still expects to call them.
    install_hooks.mouse_hook = mouse_hook
    install_hooks.keyboard_hook = keyboard_hook
    install_hooks.mouse_callback = mouse_callback
    install_hooks.keyboard_callback = keyboard_callback


def message_loop():
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
