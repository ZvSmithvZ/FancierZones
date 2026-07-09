import tkinter as tk

import config
from enums import EditorMode, HandleType


class ZoneOverlay:

    def __init__(self, zone_manager):

        self.zone_manager = zone_manager
        self.monitors = zone_manager.monitors

        # setting enum variables
        self.editor_mode = EditorMode.IDLE
        self.active_handle = HandleType.NONE

        # The minimum size a window can be resized or created at:
        self.minimum_zone_size = 20

        # ------------------------------------------------------------
        # Find the full Windows virtual desktop bounds
        # Example with 3 monitors:
        # DISPLAY3       DISPLAY1       DISPLAY2
        # -1920            0             1920
        # min_x becomes -1920, max_x becomes 3840
        # This gives us one giant coordinate space.
        # ------------------------------------------------------------

        self.min_x = min(m.x for m in self.monitors)
        self.min_y = min(m.y for m in self.monitors)
        self.max_x = max(m.x + m.width for m in self.monitors)
        self.max_y = max(m.y + m.height for m in self.monitors)

        # Total size of all monitors combined
        self.virtual_width = self.max_x - self.min_x
        self.virtual_height = self.max_y - self.min_y

        # ------------------------------------------------------------
        # Create overlay window
        # ------------------------------------------------------------
        self.root = tk.Tk()
        # Remove normal window borders/title bar
        self.root.overrideredirect(True)
        # Keep overlay above everything
        self.root.attributes("-topmost", True)

        # ------------------------------------------------------------
        # Overlay background
        # Use alpha transparency so:
        # - Desktop remains visible
        # - Mouse input still works
        # - Editor can capture clicks/drags
        # ------------------------------------------------------------
        self.root.configure(bg="black")
        # Make overlay semi-transparent
        # Adjust this value: 0.0 = invisible - 1.0 = fully opaque
        self.root.attributes("-alpha", 0.35)
        # self.root.attributes("-alpha", 1)

        # ------------------------------------------------------------
        # Position overlay over the entire virtual desktop
        # Windows coordinates: DISPLAY3: x = -1920 | DISPLAY1: x = 0 | DISPLAY2: x = 1920
        # The overlay starts at min_x. Zone coordinates are converted later.
        # ------------------------------------------------------------

        # Tkinter handles negative X positions incorrectly sometimes.
        # Use geometry() first, then manually move the window.

        geometry = f"{self.virtual_width}x" f"{self.virtual_height}" "+0+0"

        # print("Initial geometry:", geometry)
        self.root.geometry(geometry)

        # Force Tkinter to actually apply the geometry
        self.root.update_idletasks()

        # Now move it separately
        self.root.geometry(f"+{self.min_x}+{self.min_y}")

        # ------------------------------------------------------------
        # DEBUG:
        # This tells us where Windows REALLY placed the overlay.
        # If this prints:   -1920 0 the overlay is correct.
        # If it prints: 0 0 Tkinter ignored the negative position.
        # ------------------------------------------------------------
        # print("Actual overlay position:")
        # print(self.root.winfo_x(), self.root.winfo_y())
        # print("Actual overlay size:")
        # print(self.root.winfo_width(), self.root.winfo_height())
        # ------------------------------------------------------------
        # Canvas where zones are drawn
        # ------------------------------------------------------------
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        # ------------------------------------------------------------
        # These store the rectangle currently being drawn.
        # Canvas position where the user started drawing a new zone.
        # Used only while creating.
        # ------------------------------------------------------------
        self.create_start_x = None
        self.create_start_y = None
        self.current_rectangle = None

        # ------------------------------------------------------------
        # Setting no currently selected zone
        # ------------------------------------------------------------
        self.selected_zone = None
        self.current_cursor = None

        # ------------------------------------------------------------
        # Distance from the mouse cursorto the zone's upper-left corner.
        # Keeps the zone from jumping when dragging starts.
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Stores canvas objects for zones
        # Allows moving/resizing without redrawing everything
        self.zone_canvas_items = {}

        # ------------------------------------------------------------
        # Bind mouse events
        # Button-1 = left mouse button
        # ------------------------------------------------------------
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.root.bind("<Delete>", self.delete_selected_zone)
        # Hover detection
        self.canvas.bind("<Motion>", self.mouse_move)

    def draw(self):
        # print("DRAW CALLED")
        self.canvas.delete("all")

        for monitor in self.monitors:

            # print("MONITOR:", monitor.id, "position:", monitor.x, monitor.y)
            mx1 = monitor.x - self.min_x
            my1 = monitor.y - self.min_y

            mx2 = mx1 + monitor.width
            my2 = my1 + monitor.height
            self.canvas.create_rectangle(
                mx1, my1, mx2, my2, outline="cyan", width=2, fill=""
            )

            self.canvas.create_text(
                mx1 + 10,
                my1 + 10,
                text=monitor.id,
                anchor="nw",
                fill="white",
            )
            for zone in monitor.zones:

                # ----------------------------------------------------
                # Convert absolute Windows coordinates
                # Example: Monitor 2 zone: x = 2120
                # Overlay starts at min_x = -1920
                # Canvas coordinate: 2120 - (-1920) = 4040
                # ----------------------------------------------------
                # Converting from win to canvas coords
                # x1, y1 = self.windows_to_canvas_coords(zone.x, zone.y)
                x1, y1 = self.windows_to_canvas_coords(zone.x, zone.y)
                x2 = x1 + zone.width
                y2 = y1 + zone.height

                # print("ZONE:", zone.x, zone.y, "canvas:", x1, y1)
                # ------------------------------------------------------
                # Draw rectangle
                if zone == self.selected_zone:
                    outline = "yellow"
                    width = 5
                    fill = "gray40"
                else:
                    outline = "red"
                    width = 3
                    fill = "gray20"

                # Create rectangle zone and store ID
                zone_id = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline=outline,
                    width=width,
                    fill=fill,
                    stipple="gray50",
                )

                self.zone_canvas_items[zone] = zone_id

                # ------------------------------------------------
                # Move handle size
                handle_size = 18

                handle_x, handle_y = self.get_move_handle_position(zone)
                canvas_x, canvas_y = self.windows_to_canvas_coords(
                    handle_x,
                    handle_y,
                )

                # Rendering the move handle
                self.canvas.create_oval(
                    canvas_x - handle_size / 2,
                    canvas_y - handle_size / 2,
                    canvas_x + handle_size / 2,
                    canvas_y + handle_size / 2,
                    fill="dodgerblue",
                    outline="white",
                    width=2,
                )

                # ------------------------------------------------
                # Label zone size
                self.canvas.create_text(
                    x1 + 10,
                    y1 + 10,
                    text=f"Xcoord:{zone.x} Ycoord:{zone.y} Dimensions:{zone.width}x{zone.height} Assigned:{zone.assignment}",
                    anchor="nw",
                    fill="white",
                )

                # Drawing resize indicators for selected zones
                if zone == self.selected_zone:

                    indicator_size = 10
                    indicator_color = "white"
                    handles = self.get_resize_handle_positions(
                        x1,
                        y1,
                        x2,
                        y2,
                    )

                    for px, py in handles.values():

                        self.canvas.create_rectangle(
                            px - indicator_size / 2,
                            py - indicator_size / 2,
                            px + indicator_size / 2,
                            py + indicator_size / 2,
                            fill=indicator_color,
                            outline="black",
                        )

        # self.root.update()
        # self.root.update_idletasks()

    def show(self):
        """
        Opens the overlay.

        Does NOT start tkinter mainloop because
        the application already has its own Windows hook loop.
        """
        self.draw()
        self.root.deiconify()

    def update(self):
        """
        Gives tkinter time to process:
        - mouse clicks
        - mouse movement
        - redraws
        """
        if self.root:
            self.root.update()

    # def process_events(self):
    #     """
    #     Allows Tkinter to process:
    #     - mouse clicks
    #     - mouse movement
    #     - redraw events
    #     without starting a second event loop.
    #     """

    #     if self.root:
    #         self.root.update()

    def mouse_down(self, event):

        hit = self.get_handle_at(event.x, event.y)
        # ---------------------------------------------------------------
        # Moving/ selecting existing zone branch
        # M1 over selecting a zone area
        if hit:
            # print("Border selected:", hit)
            handle, zone = hit

            self.selected_zone = zone
            self.active_handle = handle

            if handle == HandleType.MOVE:
                # fixing the select staying yellow when drawing a new zone
                # self.draw()

                self.editor_mode = EditorMode.MOVING

                # Convert canvas coordinates to Windows coordinates
                windows_x = event.x + self.min_x
                windows_y = event.y + self.min_y

                # tells us where inside the zone we grabbed it at
                self.drag_offset_x = windows_x - zone.x
                self.drag_offset_y = windows_y - zone.y

            elif handle != HandleType.NONE:
                self.editor_mode = EditorMode.RESIZING

            self.draw()
            return
        # ------------------------------------------------------------------
        # CREATION BRANCH
        # M1 in Empty space = create new zone

        self.selected_zone = None
        self.active_handle = HandleType.NONE

        self.editor_mode = EditorMode.CREATING

        self.create_start_x = event.x
        self.create_start_y = event.y

        self.draw()

        print("Creating zone")

    def mouse_drag(self, event):
        """
        Handles mouse movement while the left mouse button is held.
        Depending on the current editor mode this will either:
            - Move an existing zone
            - Draw the preview for a new zone
        """
        # print("DRAG")
        # print("MOUSE DRAG RECEIVED")
        # Convert canvas coordinates to Windows coordinates

        windows_x, windows_y = self.canvas_to_windows_coords(event.x, event.y)
        # ------------------------------------------------------------
        # Resizing an existing zone
        # ------------------------------------------------------------
        if self.editor_mode == EditorMode.RESIZING:

            if self.selected_zone is None:
                return

            zone = self.selected_zone

            if self.active_handle == HandleType.LEFT:
                self.resize_left(zone, windows_x)

            elif self.active_handle == HandleType.RIGHT:
                self.resize_right(zone, windows_x)

            elif self.active_handle == HandleType.TOP:
                self.resize_top(zone, windows_y)

            elif self.active_handle == HandleType.BOTTOM:
                self.resize_bottom(zone, windows_y)

            elif self.active_handle == HandleType.TOP_LEFT:
                self.resize_left(zone, windows_x)
                self.resize_top(zone, windows_y)

            elif self.active_handle == HandleType.TOP_RIGHT:
                self.resize_right(zone, windows_x)
                self.resize_top(zone, windows_y)

            elif self.active_handle == HandleType.BOTTOM_LEFT:
                self.resize_left(zone, windows_x)
                self.resize_bottom(zone, windows_y)

            elif self.active_handle == HandleType.BOTTOM_RIGHT:
                self.resize_right(zone, windows_x)
                self.resize_bottom(zone, windows_y)

            # Instead of drawing everything we're just going to redraw the affected zone
            # self.draw()
            self.refresh_selected_zone()

            return

        # -------------------------------------------------------------
        # Moving/Dragging an existing layout window
        # -------------------------------------------------------------
        if self.editor_mode == EditorMode.MOVING:

            if self.selected_zone is None:
                return

            self.selected_zone.x = windows_x - self.drag_offset_x
            self.selected_zone.y = windows_y - self.drag_offset_y

            # Instead of drawing everything we're just going to redraw the affected zone
            # self.draw()
            self.refresh_selected_zone()

            return

        # -------------------------------------------------------------
        # Creating a new zone
        # -------------------------------------------------------------
        if self.editor_mode != EditorMode.CREATING:
            return

        # The type checker doesn't know these aren't None, so
        # copying them into local variables after the check.
        if self.create_start_x is None or self.create_start_y is None:
            return

        # tell Python/type checker these are definitely numbers.
        start_x = self.create_start_x
        start_y = self.create_start_y

        # Remove old preview rectangle
        if self.current_rectangle:
            self.canvas.delete(self.current_rectangle)

        # Draw new preview rectangle
        self.current_rectangle = self.canvas.create_rectangle(
            start_x, start_y, event.x, event.y, outline="yellow", width=3
        )

    def mouse_up(self, event):
        """
        Finishes creating a zone or moving a selected zone.
        """

        # ------------------------------------------------------------
        # Finished moving an existing zone
        # ------------------------------------------------------------
        if self.editor_mode == EditorMode.MOVING:

            config.save_config(self.zone_manager.monitors)

            self.editor_mode = EditorMode.IDLE
            self.active_handle = HandleType.NONE

            self.draw()

            return

        # ------------------------------------------------------------
        # Finished resizing an existing zone
        # ------------------------------------------------------------
        if self.editor_mode == EditorMode.RESIZING:

            print(
                "FINISHED RESIZE:",
                # self.selected_zone.x,
                # self.selected_zone.y,
                # self.selected_zone.width,
                # self.selected_zone.height
            )

            config.save_config(self.zone_manager.monitors)

            self.editor_mode = EditorMode.IDLE
            self.active_handle = HandleType.NONE

            self.draw()

            return
        # ------------------------------------------------------------
        # Finished creating a new zone
        # ------------------------------------------------------------

        if self.editor_mode == EditorMode.CREATING:
            if self.create_start_x is None or self.create_start_y is None:
                return
            # ------------------------------------------------------------
            # Normalize drag direction
            # Allows dragging:top-left -> bottom-right
            # OR bottom-right -> top-left
            # ------------------------------------------------------------

            canvas_x1 = min(self.create_start_x, event.x)
            canvas_y1 = min(self.create_start_y, event.y)

            canvas_x2 = max(self.create_start_x, event.x)
            canvas_y2 = max(self.create_start_y, event.y)

            width = canvas_x2 - canvas_x1
            height = canvas_y2 - canvas_y1

            # Ignore accidental tiny clicks
            if (
                width < self.minimum_zone_size
                or height < self.minimum_zone_size
            ):
                print("Zone too small")
                if self.current_rectangle:
                    self.canvas.delete(self.current_rectangle)
                    self.current_rectangle = None
                return

            # ------------------------------------------------------------
            # Convert canvas coordinates into Windows coordinates
            # ------------------------------------------------------------

            windows_x, windows_y = self.canvas_to_windows_coords(
                canvas_x1, canvas_y1
            )

            print("New zone:", windows_x, windows_y, width, height)

            # ------------------------------------------------------------
            # Find which monitor this belongs to
            # ------------------------------------------------------------

            monitor = self.find_monitor_for_zone(windows_x, windows_y)

            if monitor is None:
                print("No monitor found")
            else:
                print("Assigned to monitor:", monitor.id)

                self.zone_manager.editor.add_zone(
                    monitor.id, windows_x, windows_y, width, height
                )
                config.save_config(self.zone_manager.monitors)

            # Remove preview rectangle
            if self.current_rectangle:
                self.canvas.delete(self.current_rectangle)

                self.current_rectangle = None

        # Reset editor and handle state
        self.editor_mode = EditorMode.IDLE
        self.active_handle = HandleType.NONE

        # Reset drag state
        self.create_start_x = None
        self.create_start_y = None

        # Redraw zones
        self.draw()

    def canvas_to_windows_coords(self, x, y):
        """
        Converts Tkinter canvas coordinates back into
        Windows virtual desktop coordinates.

        Example:

        Left monitor:
            canvas x = 100
            min_x = -1920

        Windows x:
            100 + (-1920)
            = -1820
        """

        return (x + self.min_x, y + self.min_y)

    def windows_to_canvas_coords(self, windows_x, windows_y):
        """
        Converts Windows desktop coordinates
        into overlay canvas coordinates.
        """

        return (
            windows_x - self.min_x,
            windows_y - self.min_y,
        )

    def find_monitor_for_zone(self, x, y):
        """
        Finds which monitor contains the top-left
        corner of the new zone.
        """

        for monitor in self.monitors:

            if (
                monitor.x <= x < monitor.x + monitor.width
                and monitor.y <= y < monitor.y + monitor.height
            ):
                return monitor

        return None

    def delete_selected_zone(self, event=None):
        """
        Deletes the currently selected zone.
        """

        if self.selected_zone is None:
            return

        self.zone_manager.editor.remove_zone(self.selected_zone)

        self.selected_zone = None

        self.draw()

    def get_handle_at(self, canvas_x, canvas_y):
        """
        Checks if the mouse is on a zone edit handle.

        Returns:
            (HandleType, Zone)
            None otherwise
        """

        windows_x, windows_y = self.canvas_to_windows_coords(
            canvas_x,
            canvas_y,
        )

        handle_size = 12

        for monitor in self.monitors:
            for zone in monitor.zones:

                # --------------------------------------------
                # Zone edges in Windows coordinates
                # --------------------------------------------

                x1 = zone.x
                y1 = zone.y

                x2 = zone.x + zone.width
                y2 = zone.y + zone.height

                # --------------------------------------------
                # Get resize handle positions
                # These are Windows coordinates because
                # x1/y1/x2/y2 are Windows coordinates.
                # --------------------------------------------

                handles = self.get_resize_handle_positions(
                    x1,
                    y1,
                    x2,
                    y2,
                )

                for handle, (hx, hy) in handles.items():

                    if (
                        abs(windows_x - hx) <= handle_size
                        and abs(windows_y - hy) <= handle_size
                    ):
                        return (handle, zone)

                # --------------------------------------------
                # Move handle
                # --------------------------------------------

                move_x, move_y = self.get_move_handle_position(zone)

                if (
                    abs(windows_x - move_x) <= handle_size
                    and abs(windows_y - move_y) <= handle_size
                ):
                    return (HandleType.MOVE, zone)

        return None

    def get_move_handle_position(self, zone):
        """
        Returns the center of the move handle
        in Windows coordinates.
        """
        handle_x = zone.x + zone.width / 2
        handle_y = zone.y - 25
        return handle_x, handle_y

    def get_resize_handle_positions(self, x1, y1, x2, y2):
        """
        Returns the center point of every resize handle.

        Coordinates are passed in whatever coordinate system
        the caller is currently using.
        """

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        return {
            HandleType.TOP_LEFT: (x1, y1),
            HandleType.TOP: (mid_x, y1),
            HandleType.TOP_RIGHT: (x2, y1),
            HandleType.LEFT: (x1, mid_y),
            HandleType.RIGHT: (x2, mid_y),
            HandleType.BOTTOM_LEFT: (x1, y2),
            HandleType.BOTTOM: (mid_x, y2),
            HandleType.BOTTOM_RIGHT: (x2, y2),
        }

    def mouse_move(self, event):
        """
        Changes the mouse cursor depending on
        what editor handle is under the mouse.
        """

        # import time

        # start = time.perf_counter()

        # hit = self.get_handle_at(event.x, event.y)

        # elapsed = time.perf_counter() - start

        # if elapsed > 0.005:
        #     print("mouse_move slow:", elapsed)

        hit = self.get_handle_at(event.x, event.y)
        # print(f"Mouse move hit:{hit}")

        if hit is None:
            if self.current_cursor != "":
                self.canvas.configure(cursor="")
                self.current_cursor = ""

            return

        handle, zone = hit
        # print(f"{handle} {zone} = hit")
        cursor_map = {
            HandleType.MOVE: "fleur",
            HandleType.TOP_LEFT: "size_nw_se",
            HandleType.TOP: "size_ns",
            HandleType.TOP_RIGHT: "size_ne_sw",
            HandleType.LEFT: "size_we",
            HandleType.RIGHT: "size_we",
            HandleType.BOTTOM_LEFT: "size_ne_sw",
            HandleType.BOTTOM: "size_ns",
            HandleType.BOTTOM_RIGHT: "size_nw_se",
        }

        new_cursor = cursor_map.get(handle, "")

        if new_cursor != self.current_cursor:
            self.canvas.configure(cursor=new_cursor)
            self.current_cursor = new_cursor

    def resize_left(self, zone, windows_x):
        """
        Moves the left edge while keeping the right edge fixed.
        """
        old_right = zone.x + zone.width
        new_width = old_right - windows_x

        if new_width >= self.minimum_zone_size:
            zone.x = windows_x
            zone.width = new_width

    def resize_right(self, zone, windows_x):
        """
        Moves the right edge while keeping the left edge fixed.
        """
        zone.width = max(self.minimum_zone_size, windows_x - zone.x)

    def resize_top(self, zone, windows_y):
        """
        Moves the top edge while keeping the bottom edge fixed.
        """
        old_bottom = zone.y + zone.height
        new_height = old_bottom - windows_y

        if new_height >= self.minimum_zone_size:
            zone.y = windows_y
            zone.height = new_height

    def resize_bottom(self, zone, windows_y):
        """
        Moves the bottom edge while keeping the top edge fixed.
        """
        zone.height = max(self.minimum_zone_size, windows_y - zone.y)

    def refresh_selected_zone(self):
        """
        Updates only the selected zone rectangle.
        Does not redraw the entire canvas.
        """

        if self.selected_zone is None:
            return

        zone = self.selected_zone

        if zone not in self.zone_canvas_items:
            return

        x1, y1 = self.windows_to_canvas_coords(zone.x, zone.y)

        x2 = x1 + zone.width
        y2 = y1 + zone.height

        self.canvas.coords(self.zone_canvas_items[zone], x1, y1, x2, y2)
