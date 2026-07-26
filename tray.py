import pystray
from PIL import Image

import config


class TrayManager:

    def __init__(self, zone_manager):
        self.zone_manager = zone_manager
        self.icon = None

    def start(self):

        image = Image.new(
            "RGB",
            (64, 64),
            "black",
        )

        menu = pystray.Menu(
            pystray.MenuItem(
                "Auto Tile on Launch",
                self.toggle_auto_tile,
                checked=lambda item: (
                    self.zone_manager.settings.auto_tile_on_launch
                ),
            ),
        )

        self.icon = pystray.Icon(
            "FancierZones",
            image,
            "FancierZones",
            menu,
        )

        self.icon.run()

    def toggle_auto_tile(self, icon, item):

        self.zone_manager.settings.auto_tile_on_launch = (
            not self.zone_manager.settings.auto_tile_on_launch
        )

        config.save_config(
            self.zone_manager.monitors,
            self.zone_manager.settings,
        )
