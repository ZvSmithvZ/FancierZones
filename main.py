# import win32gui

import config
import hooks
from zones import ZoneManager

# ------------------------------------------------------------
# Create the central manager for all zones/monitors
# ------------------------------------------------------------
zone_manager = ZoneManager()


# Detect monitors currently connected and merge
# any saved zones from config.json. To help with new/disconnected monitors
zone_manager.monitors = config.merge_monitors()

config.save_config(zone_manager.monitors)

# ------------------------------------------------------------
# Install global Windows hooks (mouse/keyboard interception from)
# ------------------------------------------------------------
hooks.install_hooks(zone_manager)

# ------------------------------------------------------------
# Keep program alive and listening for hooks
# ------------------------------------------------------------
hooks.message_loop()
