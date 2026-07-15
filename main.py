# import win32gui
import config
import hooks

# import windows
from editor import ZoneEditor

# from overlay import ZoneOverlay
from zones import ZoneManager

# ------------------------------------------------------------
# Create the central manager for all zones/monitors
# ------------------------------------------------------------
zone_manager = ZoneManager()

# ------------------------------------------------------------
# Detect monitors and merge saved zones (conflict prevention with new/removed monitors)
# ------------------------------------------------------------
zone_manager.monitors = config.merge_monitors()

# Test to check what windows are enumerated with the new autoblock list
# for hwnd in windows.enumerate_windows():
#     info = windows.get_window_info(hwnd)
#     print(info.title, info.exe, info.class_name)
# ------------------------------------------------------------
# Create editor
# ------------------------------------------------------------
editor = ZoneEditor(zone_manager)
# Connect editor to ZoneManager
zone_manager.set_editor(editor)

# overlay = ZoneOverlay(zone_manager.monitors)
# overlay.show()

# ------------------------------------------------------------
# Install global Windows hooks (mouse/keyboard interception from)
# ------------------------------------------------------------
hooks.install_hooks(zone_manager)


# ------------------------------------------------------------
# Keep program alive and listening for hooks
# ------------------------------------------------------------
hooks.message_loop()
