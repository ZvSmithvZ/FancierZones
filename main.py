# import win32gui
import threading

import config
import hooks
import win_events

# import windows
from editor import ZoneEditor
from tray import TrayManager

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


# ------------------------------------------------------------
# Create editor
# ------------------------------------------------------------
editor = ZoneEditor(zone_manager)
# Connect editor to ZoneManager
zone_manager.set_editor(editor)


# ------------------------------------------------------------
# Install global Windows hooks (mouse/keyboard interception from)
# ------------------------------------------------------------
hooks.install_hooks(zone_manager)
win_events.install_event_hooks(zone_manager)


# ------------------------------------------------------------
# Get tray menuing running
# ------------------------------------------------------------
tray = TrayManager(zone_manager)

threading.Thread(
    target=tray.start,
    daemon=True,
).start()

# ------------------------------------------------------------
# Keep program alive and listening for hooks
# ------------------------------------------------------------
hooks.message_loop()
