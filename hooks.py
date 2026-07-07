import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui

from zones import ZoneManager

# ============================================================================
# WHY THE OLD VERSION FAILED
# ----------------------------------------------------------------------------
# The Start Menu opens because Explorer listens for a Win key-up event that
# was NOT paired with anything else. It does NOT care whether some other key
# (like Ctrl) was tapped before/after/during — that "send a Ctrl tap" trick
# is a myth on modern Windows and does nothing reliable.
#
# The only real fix: intercept the Win key at the low-level KEYBOARD hook and
# physically swallow the key-up event (return 1 instead of calling
# CallNextHookEx) whenever that Win press was used as part of a combo.
# If Explorer never receives the key-up message at all, it has nothing to
# react to, and the Start Menu cannot open — this is exactly how AHK does it
# under the hood.
#
# The old code ONLY installed a mouse hook (WH_MOUSE_LL). It could detect
# and swallow the right-click fine, but it never touched the keyboard event
# stream, so the Win key-up always reached Explorer untouched. Adding the
# keyboard hook below is the missing piece.
# ============================================================================

# ---- Hook type constants ----
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

# ---- Virtual key codes we care about ----
VK_LWIN = 0x5B
VK_RWIN = 0x5C

# ---- Keyboard hook message constants ----
# SYSKEYDOWN/UP fire instead of the plain versions when Alt (or in some
# cases Win) is involved, so we must check for both.
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# ---- Mouse hook message constants ----
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

# ---- ctypes plumbing ----
LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
ULONG_PTR = (
    ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
)


class MSLLHOOKSTRUCT(ctypes.Structure):
    """Struct Windows fills in for every low-level mouse hook event."""

    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Struct Windows fills in for every low-level keyboard hook event."""

    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


# Hook callback function signatures (both mouse and keyboard low-level hooks
# use this same shape: nCode, wParam, lParam -> LRESULT)
HookProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HookProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]

# ---- Shared state ----
zone_manager: ZoneManager | None = None

# True from the moment we detect Win+RightClick down, until we've swallowed
# the matching RBUTTONUP *and* the matching Win key-up. Both hooks read/write
# this, which is why it's a plain module-level flag rather than something
# local to either hook function.
combo_in_progress = False

# Tracks physical Win key state purely from the keyboard hook itself.
# (We keep using win32api.GetAsyncKeyState as a secondary check too, but the
# keyboard hook is the source of truth for suppression decisions.)
win_key_down = False


def is_win_key_down():
    """Secondary/independent check via the Windows API, used by the mouse hook."""
    left = win32api.GetAsyncKeyState(VK_LWIN) & 0x8000
    right = win32api.GetAsyncKeyState(VK_RWIN) & 0x8000
    result = bool(left or right)
    print(f"[debug] is_win_key_down -> {result}")
    return result


def get_window_under_cursor():
    x, y = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint((x, y))
    root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    print(f"[debug] window under cursor: hwnd={hwnd}, root={root}")
    return root


# ============================================================================
# KEYBOARD HOOK
# ============================================================================
def low_level_keyboard_proc(nCode, wParam, lParam):
    """
    Runs for every keyboard event system-wide, before any application
    (including Explorer) sees it. Returning 1 here means "swallow this
    event" — Explorer/the focused app never receives it.
    """
    global win_key_down, combo_in_progress

    if nCode == 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        if kb.vkCode in (VK_LWIN, VK_RWIN):
            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                if not win_key_down:
                    print("[debug] WIN key DOWN")
                win_key_down = True

            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                print(f"[debug] WIN key UP, combo_in_progress={combo_in_progress}")
                win_key_down = False

                if combo_in_progress:
                    # This is the actual fix: swallow the Win key-up itself
                    # so Explorer never sees it and can't open the Start Menu.
                    print("[debug] -> swallowing WIN key-up to suppress Start Menu")
                    combo_in_progress = False
                    return 1

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# ============================================================================
# MOUSE HOOK
# ============================================================================
def low_level_mouse_proc(nCode, wParam, lParam):
    global combo_in_progress

    if nCode == 0:

        if wParam == WM_RBUTTONDOWN:
            print("[debug] WM_RBUTTONDOWN received")
            if is_win_key_down():
                print("[debug] -> WIN + RIGHT CLICK DOWN detected, handling combo")
                combo_in_progress = True

                if zone_manager:
                    print("[debug] calling zone_manager.tile_under_cursor()")
                    zone_manager.tile_under_cursor()
                else:
                    print("[debug] zone_manager is None!")

                print("[debug] swallowing RBUTTONDOWN")
                return 1  # stop the app under the cursor from seeing the right-click

        if wParam == WM_RBUTTONUP:
            print(
                f"[debug] WM_RBUTTONUP received, combo_in_progress={combo_in_progress}"
            )
            if combo_in_progress:
                print("[debug] swallowing RBUTTONUP (matching combo down)")
                # NOTE: we deliberately do NOT reset combo_in_progress here.
                # It stays True until the keyboard hook consumes it on the
                # Win key-up. That's what makes the two hooks cooperate:
                # mouse hook swallows the click, keyboard hook swallows the
                # key-up that would otherwise trigger the Start Menu.
                return 1

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# Keep strong references alive globally — ctypes does NOT keep a reference
# to CFUNCTYPE callbacks, so if these get garbage collected the hook will
# silently stop working or crash.
_keyboard_hook_proc = HookProc(low_level_keyboard_proc)
_mouse_hook_proc = HookProc(low_level_mouse_proc)


def install_hooks(manager: ZoneManager):
    global zone_manager
    zone_manager = manager

    keyboard_hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, _keyboard_hook_proc, None, 0
    )
    if not keyboard_hook:
        raise OSError(
            f"Failed to install keyboard hook. Error: {ctypes.GetLastError()}"
        )
    print(f"[debug] Keyboard hook installed (handle={keyboard_hook})")

    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, _mouse_hook_proc, None, 0)
    if not mouse_hook:
        # Clean up the keyboard hook if the mouse hook fails, so we don't
        # leak a hook if this function raises.
        user32.UnhookWindowsHookEx(keyboard_hook)
        raise OSError(f"Failed to install mouse hook. Error: {ctypes.GetLastError()}")
    print(f"[debug] Mouse hook installed (handle={mouse_hook})")

    install_hooks.keyboard_hook = keyboard_hook
    install_hooks.mouse_hook = mouse_hook


def unhook_hooks():
    """Call this in a finally block on shutdown to cleanly remove both hooks."""
    kb_hook = getattr(install_hooks, "keyboard_hook", None)
    ms_hook = getattr(install_hooks, "mouse_hook", None)

    if kb_hook:
        user32.UnhookWindowsHookEx(kb_hook)
        print("[debug] Keyboard hook removed")
    if ms_hook:
        user32.UnhookWindowsHookEx(ms_hook)
        print("[debug] Mouse hook removed")


def message_loop():
    """
    Low-level hooks require a live message pump on the same thread that
    installed them — Windows delivers hook events through the thread's
    message queue. Without this loop running, the hooks never actually fire.
    """
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
