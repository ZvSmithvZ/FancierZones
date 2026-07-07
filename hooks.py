import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui

from zones import ZoneManager

# ------------------------------------------------------------
# Windows Hook Types
#
# We only use a MOUSE hook now. No keyboard hook at all.
#
# Why: a keyboard hook that ever blocks (return 1) a real key
# event can desync Explorer's own internal Win-key tracking,
# since that tracking is driven by the message stream — if a
# key-up message never arrives, the shell can end up believing
# a key is still held even though it's physically been released.
# That's what caused the "stuck Win key" bug.
#
# Instead, we prevent the Start Menu from popping using a
# different, non-destructive trick: sending a real (but harmless)
# dummy keystroke — a Ctrl tap — the instant our hotkey fires.
# This interrupts the shell's "Win pressed-and-released alone"
# detection without ever blocking or faking any part of the real
# Win key's own message stream. Nothing about Win's state is
# ever touched, so it can never get stuck.
# ------------------------------------------------------------

WH_MOUSE_LL = 14

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CONTROL = 0x11

WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

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


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


MouseProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = LRESULT

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT


zone_manager: ZoneManager | None = None

# ------------------------------------------------------------
# combo_in_progress:
#     True from the moment we swallow a Win+RightButtonDown,
#     until we've also swallowed the matching RightButtonUp.
#     This is what lets us block BOTH halves of the click so
#     no context menu appears.
# ------------------------------------------------------------

combo_in_progress = False


def is_win_key_down():
    left = win32api.GetAsyncKeyState(VK_LWIN) & 0x8000
    right = win32api.GetAsyncKeyState(VK_RWIN) & 0x8000
    return bool(left or right)


def suppress_start_menu():
    """
    Sends a real Ctrl down+up via SendInput.

    This gives the shell a genuine "something else happened" signal
    between Win-down and Win-up, which interrupts its "Win pressed
    and released alone" detection — without ever touching a real
    Win key event, so Win's own state can never get stuck.
    """
    down = INPUT(
        type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0))
    )
    up = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0)),
    )

    inputs = (INPUT * 2)(down, up)
    user32.SendInput(2, inputs, ctypes.sizeof(INPUT))


def get_window_under_cursor():
    x, y = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    return win32gui.GetAncestor(hwnd, win32con.GA_ROOT)


def low_level_mouse_proc(nCode, wParam, lParam):
    global combo_in_progress

    if nCode == 0:

        if wParam == WM_RBUTTONDOWN and is_win_key_down():
            print("WIN + RIGHT CLICK (down)")
            combo_in_progress = True

            suppress_start_menu()  # do this immediately, before anything else

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


def install_hooks(manager: ZoneManager):
    global zone_manager
    zone_manager = manager

    mouse_callback = MouseProc(low_level_mouse_proc)
    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, None, 0)

    if not mouse_hook:
        raise OSError(f"Failed to install mouse hook. Error: {ctypes.GetLastError()}")

    print(f"Mouse hook installed (handle={mouse_hook})")

    install_hooks.mouse_hook = mouse_hook
    install_hooks.mouse_callback = mouse_callback


def message_loop():
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
