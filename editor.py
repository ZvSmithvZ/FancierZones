# import win32api
# import win32gui

# import config
# from models import Zone

# class ZoneEditor:

#     def __init__(self, zone_manager):
#         self.zone_manager = zone_manager

#     def create_test_zone(self):
#         """
#         Temporary test function.
#         Later this becomes mouse drag logic.
#         """

#         monitor = self.zone_manager.monitors[0]

#         monitor.zones.append(
#             Zone(
#                 x=100,
#                 y=100,
#                 width=500,
#                 height=500,
#                 assignment=None
#             )
#         )

#         config.save_config(self.zone_manager.monitors)

#         print("Created zone")
