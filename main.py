# import win32gui

import windows
from hooks import install_hooks, message_loop

# from models import Monitor, Zone
from models import Zone
from zones import ZoneManager

# testing new mon detection
monitors = windows.detect_monitors()

for monitor in monitors:
    print(f"Monitor: {monitor.id}")
    print(f"Position: {monitor.x}, {monitor.y}")
    print(f"Size: {monitor.width}x{monitor.height}")
    print(f"Zones: {monitor.zones}")
    print("----------------")


# ------------------------------------------------------------
# Create the central manager for all zones/monitors
# ------------------------------------------------------------
zone_manager = ZoneManager()


# new logic here to call function that auto detect monitors in class Zone manager
zone_manager.monitors = windows.detect_monitors()

# ------------------------------------------------------------
# TEMP TEST LAYOUT (hardcoded for now)
# Later this will come from a config file
# ------------------------------------------------------------

zone_manager.monitors[0].zones.append(
    Zone(x=0, y=0, width=640, height=480, assignment=None)
)


# ------------------------------------------------------------
# Install global Windows hooks (mouse/keyboard interception from)
# ------------------------------------------------------------
install_hooks(zone_manager)

# ------------------------------------------------------------
# Keep program alive and listening for hooks
# ------------------------------------------------------------
message_loop()
