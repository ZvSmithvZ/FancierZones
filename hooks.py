import ctypes
import threading
import time
from ctypes import wintypes

from zones import ZoneManager

# ============================================================================
# WHY PREVIOUS ATTEMPTS FAILED (kept for history / so we don't repeat them)
# ----------------------------------------------------------------------------
#   1. Ctrl-tap via keybd_event, no mouse hook  -> real right-click leaked
#      through to the app under the cursor.
#   2. Swallow only the Win key-UP after combo detected -> Explorer saw a
#      real key-DOWN it was never told was "released". Win got "stuck":
#      right-click kept acting like Win was held, "E" alone opened
#      Explorer, had to tap Win twice more to resync.
#   3. Swallow real Win down+up entirely, replay a synthetic tap via
#      SendInput when no combo happened -> plain Win taps AND Win+E/Win+D
#      stopped working because modern Explorer doesn't fully trust
#      SendInput-injected Win events for driving shortcuts.
#   4. "Flash and close" -- poll for the Start Menu window and send it
#      Escape once it appears -> works but visibly flashes open first,
#      which is distracting.
#   5. Ctrl-TAP (down+up immediately) sent the instant combo is detected,
#      keyboard hook never swallows anything -> STILL opened the Start
#      Menu. Turned out to be a bug, not a dead end: our INPUT ctypes
#      struct only declared the `ki` (KEYBDINPUT) union member. On 64-bit
#      Windows the real INPUT union's largest member is MOUSEINPUT, which
#      is what determines the struct's true size. Our version was smaller
#      than what user32.dll expects, so SendInput's internal size check
#      silently rejected the call -- it returned 0 events sent, meaning
#      the Ctrl tap never happened at all. Fixed below by declaring the
#      full union (mi/ki/hi) exactly like the real Win32 INPUT struct.
#
#      Separately: even with that fixed, a quick tap-and-release of Ctrl
#      has a timing risk -- if it fully completes before Explorer actually
#      evaluates "was Win pressed alone" (which happens when it processes
#      the real Win key-up), Ctrl is no longer down at the moment that
#      matters, so nothing gets suppressed. Fix: HOLD Ctrl down the
#      instant the combo is detected, and only release it shortly after
#      the real Win key-up has passed through -- guaranteeing Ctrl is
#      registered as held at the exact moment Explorer checks.
#
# THE APPROACH NOW:
# - Keyboard hook NEVER swallows anything. Explorer always gets the real,
#   untouched Win down/up pair -- so nothing can ever get "stuck", and
#   every native shortcut (Win+E, Win+D, Win+L, Win+Tab...) always works.
# - The instant Win+RightClick is detected, we send a real Ctrl KEY-DOWN
#   (and hold it -- do not release yet).
# - When the keyboard hook sees the real Win key-up come through, it lets
#   it pass to Explorer as normal, then immediately sends the Ctrl KEY-UP.
#   Because Ctrl was registered "down" in the system key state at the
#   moment Explorer evaluated the Win key-up, Explorer treats it as
#   "Win was used in a combo" and does not open the Start Menu.
# - Right-click down/up are still swallowed outright so the app under the
#   cursor doesn't also get a context menu -- that part was never broken.
# ============================================================================

# ---- Hook type constants ----
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

# ---- Virtual key codes we care about ----
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CONTROL = 0x11
VK_F12 = 0x7B

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

# ---- Flag Windows sets on KBDLLHOOKSTRUCT.flags for synthetic/injected keystrokes ----
# Lets our own hook recognize "this event came from our own SendInput call"
# so we never mistake our own injected Ctrl for a real physical Ctrl press.
LLKHF_INJECTED = 0x10

# ---- SendInput constants ----
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

# ---- How long to wait after the real Win key-up before releasing our held Ctrl ----
# Gives Explorer's internal state machine time to actually evaluate the
# key-up before we let go. A few milliseconds is plenty and is imperceptible.
CTRL_RELEASE_DELAY_SECONDS = 0.03

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


class KEYBDINPUT(ctypes.Structure):
    """Describes a synthetic keystroke we send via SendInput."""

    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    """
    We never send synthetic mouse input, but this MUST be declared as part
    of the INPUT union below -- on 64-bit Windows, MOUSEINPUT is the
    LARGEST member of the real union and determines ctypes.sizeof(INPUT).
    Leaving it out was the bug that made SendInput silently reject every
    call last time (it reported 0 events sent).
    """

    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    """Also required for the union to exactly match the real Win32 INPUT struct."""

    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT(ctypes.Structure):
    """
    Full SendInput envelope, matching the real Win32 INPUT struct exactly:
    a DWORD type field followed by a union of mi/ki/hi. Declaring the full
    union (not just `ki`) is required so ctypes.sizeof(INPUT) matches what
    user32.dll expects -- otherwise SendInput silently no-ops.
    """

    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]


# Hook callback function signature (both mouse and keyboard low-level hooks
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
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

# print(
#     f"[debug] ctypes.sizeof(INPUT) = {ctypes.sizeof(INPUT)} (must be non-zero/match user32's expectation)"
# )

# ---- Shared state ----
zone_manager: ZoneManager | None = None

# True while we believe the physical Win key is currently held down.
# Purely for OUR OWN combo detection -- we never act on this to block/allow
# real Win events; those always pass through Explorer untouched, always.
win_key_down = False

# True from the moment we detect Win+RightClick until we've released our
# held-down Ctrl key. Tells the keyboard hook "a combo is in flight, release
# Ctrl once you see the real Win key-up."
combo_in_progress = False


# def get_window_under_cursor():
#     print("get_window_under_cursor in hooks.py")
#     x, y = win32api.GetCursorPos()
#     hwnd = win32gui.WindowFromPoint((x, y))
#     root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
#     # print(f"[debug] window under cursor: hwnd={hwnd}, root={root}")
#     return root


def _send_ctrl_down():
    """Sends a real Ctrl KEY-DOWN and leaves it held (no matching up yet)."""
    down = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=0, time=0, dwExtraInfo=0),
    )
    user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    # sent = user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    # print(
    #     f"[debug] sent CTRL key-down (holding), SendInput reported {sent} event(s) (expected 1)"
    # )


def _send_ctrl_up():
    """Releases the Ctrl key we previously sent down."""
    up = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=VK_CONTROL, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0
        ),
    )
    user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    # sent = user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    # print(
    #     f"[debug] sent CTRL key-up (releasing), SendInput reported {sent} event(s) (expected 1)"
    # )


def _release_ctrl_after_delay():
    """
    Runs on a background thread. Waits a few milliseconds after the real
    Win key-up has passed through, giving Explorer's internal state machine
    time to actually evaluate the key-up while Ctrl is still registered as
    held, then releases Ctrl. The delay is short enough to be imperceptible.
    """
    time.sleep(CTRL_RELEASE_DELAY_SECONDS)
    _send_ctrl_up()


# ============================================================================
# KEYBOARD HOOK
# ============================================================================
def low_level_keyboard_proc(nCode, wParam, lParam):
    """
    Runs for every keyboard event system-wide, before any application
    (including Explorer) sees it.

    This hook NEVER returns 1 (never swallows anything). It only WATCHES
    the Win key state so the mouse hook knows whether Win is currently
    held, and releases our held Ctrl once the real Win key-up passes
    through. Explorer always sees the real Win down/up pair completely
    untouched -- that's what guarantees nothing can ever get "stuck" and
    every native shortcut keeps working all the time.
    """
    global win_key_down, combo_in_progress

    if nCode == 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        # Ignore our own injected Ctrl events -- don't let them confuse
        # any future logic that might inspect Ctrl state here.
        if kb.flags & LLKHF_INJECTED:
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        if kb.vkCode in (VK_LWIN, VK_RWIN):
            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # if not win_key_down:
                # print(
                #     "[debug] WIN key DOWN (physical) -- passing through untouched"
                # )
                win_key_down = True

            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                # print(
                #     f"[debug] WIN key UP (physical) -- passing through untouched, combo_in_progress={combo_in_progress}"
                # )
                win_key_down = False

                if combo_in_progress:
                    # Real Win key-up is about to reach Explorer via
                    # CallNextHookEx below. Release our held Ctrl shortly
                    # after -- not before -- so Ctrl is still registered
                    # as down at the moment Explorer evaluates this event.
                    # print("[debug] -> combo was in progress; scheduling Ctrl release")
                    combo_in_progress = False
                    threading.Thread(
                        target=_release_ctrl_after_delay, daemon=True
                    ).start()

    if wParam == 0x0100:  # F12 key down
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        if kb.vkCode == VK_F12:

            if zone_manager:
                zone_manager.toggle_editor()

            return 1

    # Always pass every real keyboard event through untouched. We never
    # suppress here -- suppression is achieved via the held Ctrl key, not
    # by blocking anything in this hook.
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# ============================================================================
# MOUSE HOOK
# ============================================================================
def low_level_mouse_proc(nCode, wParam, lParam):
    global combo_in_progress

    if nCode == 0:

        if wParam == WM_RBUTTONDOWN:
            # print(f"[debug] WM_RBUTTONDOWN received, win_key_down={win_key_down}")
            if win_key_down:
                # print("[debug] -> WIN + RIGHT CLICK detected, handling combo")

                # Hold Ctrl down NOW, immediately -- before the user even
                # releases Win. It stays held until the keyboard hook sees
                # the real Win key-up and schedules its release.
                combo_in_progress = True
                _send_ctrl_down()

                if zone_manager:
                    # print("[debug] calling zone_manager.tile_under_cursor()")
                    zone_manager.tile_under_cursor()
                # else:
                # print("[debug] zone_manager is None!")

                # print("[debug] swallowing RBUTTONDOWN")
                return 1  # stop the app under the cursor from seeing the right-click

        if wParam == WM_RBUTTONUP:
            # print(f"[debug] WM_RBUTTONUP received, win_key_down={win_key_down}")
            if win_key_down:
                # Still holding Win when the button comes up -- this was
                # part of our combo, swallow the matching up too so the
                # app under the cursor never sees a full click.
                # print("[debug] swallowing RBUTTONUP (matching combo down)")
                return 1

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# Keep strong references alive globally -- ctypes does NOT keep a reference
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
    installed them -- Windows delivers hook events through the thread's
    message queue. Without this loop running, the hooks never actually fire.
    """
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
