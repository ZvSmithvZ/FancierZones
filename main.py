# import win32gui

from hooks import install_hooks, message_loop
from models import Monitor, Zone
from zones import ZoneManager

# ------------------------------------------------------------
# Create the central manager for all zones/monitors
# ------------------------------------------------------------
zone_manager = ZoneManager()


# ------------------------------------------------------------
# TEMP TEST LAYOUT (hardcoded for now)
# Later this will come from a config file
# ------------------------------------------------------------
zone_manager.monitors = [
    Monitor(
        id="monitor1",
        x=0,
        y=0,
        width=1920,
        height=1080,
        zones=[
            Zone(x=0, y=0, width=640, height=480, assignment="notepad.exe"),
            Zone(x=640, y=0, width=640, height=480),
            Zone(x=50, y=500, width=840, height=680, assignment="chrome.exe"),
            Zone(x=1040, y=700, width=540, height=880),
        ],
    )
]

# ------------------------------------------------------------
# Install global Windows hooks (mouse/keyboard interception from)
# ------------------------------------------------------------
install_hooks(zone_manager)

# ------------------------------------------------------------
# Keep program alive and listening for hooks
# ------------------------------------------------------------
message_loop()
