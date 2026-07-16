import tkinter as tk
from tkinter import ttk

import config
from enums import AssignmentType, EditorMode, HandleType
from models import Assignment


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

        # Setting assignment to None to start
        self.assignment_zone = None

        # ------------------------------------------------------------
        # Distance from the mouse cursorto the zone's upper-left corner.
        # Keeps the zone from jumping when dragging starts.
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Stores canvas objects for zones
        # Allows moving/resizing without redrawing everything
        self.zone_canvas_items = {}

        # ------------------------------------------------------------
        # Bind key events
        # Button-1 = left mouse button
        # ------------------------------------------------------------
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.root.bind("<Delete>", self.delete_selected_zone)
        # Hover detection
        self.canvas.bind("<Motion>", self.mouse_move)
        # Click 'e' for zone assignment
        self.root.bind("<e>", self.open_assignment_editor)

    def draw(self):
        """
        Full redraw.

        Used when:
        - Opening editor
        - Loading config
        - Major state changes

        Does NOT get called while dragging.
        """

        self.canvas.delete("all")
        self.zone_canvas_items.clear()

        for monitor in self.monitors:

            # Draw monitor outline
            mx1 = monitor.x - self.min_x
            my1 = monitor.y - self.min_y

            mx2 = mx1 + monitor.width
            my2 = my1 + monitor.height

            self.canvas.create_rectangle(
                mx1,
                my1,
                mx2,
                my2,
                outline="cyan",
                width=2,
                fill="",
            )

            self.canvas.create_text(
                mx1 + 10,
                my1 + 10,
                text=monitor.id,
                anchor="nw",
                fill="white",
            )

            # Draw each zone on this monitor
            for zone in monitor.zones:
                self.draw_zone(zone)

    def draw_zone(self, zone):
        """
        Creates all canvas objects for one zone.

        Stores the canvas IDs in zone_canvas_items
        so they can be updated later without redrawing everything.
        """

        x1, y1 = self.windows_to_canvas_coords(zone.x, zone.y)

        x2 = x1 + zone.width
        y2 = y1 + zone.height

        # -----------------------------------------------
        # Zone appearance
        # -----------------------------------------------

        if zone == self.selected_zone:
            outline = "yellow"
            width = 5
            fill = "gray40"
        else:
            outline = "red"
            width = 3
            fill = "gray20"

        zone_items = {}

        # -----------------------------------------------
        # Main zone rectangle
        # -----------------------------------------------

        zone_items["rectangle"] = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=outline,
            width=width,
            fill=fill,
            stipple="gray50",
        )

        # -----------------------------------------------
        # Label
        # -----------------------------------------------
        assignment_text = "None"
        assignment_type_text = "None"

        if zone.assignment:
            assignment_text = zone.assignment.name

            if zone.assignment.type:
                assignment_type_text = zone.assignment.type.value

        zone_items["label"] = self.canvas.create_text(
            x1 + 10,
            y1 + 10,
            text=(
                f"Xcoord:{zone.x} "
                f"Ycoord:{zone.y} "
                f"Dimensions:{zone.width}x{zone.height} "
                f"Assigned:{assignment_text}"
                f"Type:{assignment_type_text} "
            ),
            anchor="nw",
            fill="white",
        )

        # -----------------------------------------------
        # Move handle
        # -----------------------------------------------

        handle_size = 18

        handle_x, handle_y = self.get_move_handle_position(zone)

        canvas_x, canvas_y = self.windows_to_canvas_coords(
            handle_x,
            handle_y,
        )

        zone_items["move_handle"] = self.canvas.create_oval(
            canvas_x - handle_size / 2,
            canvas_y - handle_size / 2,
            canvas_x + handle_size / 2,
            canvas_y + handle_size / 2,
            fill="dodgerblue",
            outline="white",
            width=2,
        )

        # -----------------------------------------------
        # Resize handles
        # -----------------------------------------------

        zone_items["resize_handles"] = []

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

                handle_id = self.canvas.create_rectangle(
                    px - indicator_size / 2,
                    py - indicator_size / 2,
                    px + indicator_size / 2,
                    py + indicator_size / 2,
                    fill=indicator_color,
                    outline="black",
                )

                zone_items["resize_handles"].append(handle_id)

        # -----------------------------------------------
        # Store canvas references
        # -----------------------------------------------

        self.zone_canvas_items[id(zone)] = zone_items

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
            self.root.update_idletasks()
            self.root.update()

    def mouse_down(self, event):

        # ---------------------------------------------------------------
        # Pick a window for a zone assignment
        # ---------------------------------------------------------------
        if self.editor_mode == EditorMode.PICK_ASSIGNMENT:

            print(self.zone_manager.get_window_under_cursor())
            hwnd = self.zone_manager.get_window_under_cursor()

            if hwnd:
                print(hwnd)

            return

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
            self.refresh_zone()

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

            # print("MOVING:", self.selected_zone.x, self.selected_zone.y)
            self.refresh_zone()

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
            print("No zone selected")
            return

        zone = self.selected_zone

        print("Deleting zone:", zone)

        # Remove visible canvas objects first
        self.delete_zone_canvas_items(zone)

        # Remove from data structure
        self.zone_manager.editor.remove_zone(zone)

        # Clear selection
        self.selected_zone = None
        self.active_handle = HandleType.NONE
        self.editor_mode = EditorMode.IDLE

        # Save JSON
        config.save_config(self.zone_manager.monitors)

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
        the caller is currently using. Usually canvas.
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

    def refresh_zone(self):
        """
        Updates only the selected zone's canvas objects.
        Does not redraw the entire editor.
        """
        zone = self.selected_zone

        if zone is None:
            return

        items = self.zone_canvas_items.get(id(zone))

        if not items:
            return

        # ------------------------------------------------
        # Calculate new canvas coordinates
        # ------------------------------------------------
        x1, y1 = self.windows_to_canvas_coords(zone.x, zone.y)

        x2 = x1 + zone.width
        y2 = y1 + zone.height

        # ------------------------------------------------
        # Update main rectangle
        # ------------------------------------------------
        self.canvas.coords(items["rectangle"], x1, y1, x2, y2)

        # ------------------------------------------------
        # Update move handle
        # ------------------------------------------------
        handle_x, handle_y = self.get_move_handle_position(zone)

        canvas_handle_x, canvas_handle_y = self.windows_to_canvas_coords(
            handle_x, handle_y
        )

        handle_size = 18

        self.canvas.coords(
            items["move_handle"],
            canvas_handle_x - handle_size / 2,
            canvas_handle_y - handle_size / 2,
            canvas_handle_x + handle_size / 2,
            canvas_handle_y + handle_size / 2,
        )

        # ------------------------------------------------
        # Update resize handles
        # ------------------------------------------------
        resize_positions = self.get_resize_handle_positions(x1, y1, x2, y2)

        indicator_size = 10

        for handle_id, (_, (px, py)) in zip(
            items["resize_handles"], resize_positions.items()
        ):

            self.canvas.coords(
                handle_id,
                px - indicator_size / 2,
                py - indicator_size / 2,
                px + indicator_size / 2,
                py + indicator_size / 2,
            )

        # ------------------------------------------------
        # Update label
        # ------------------------------------------------
        assignment_text = "None"
        assignment_type_text = "None"

        if zone.assignment:
            assignment_text = zone.assignment.name

            if zone.assignment.type:
                assignment_type_text = zone.assignment.type.value

        self.canvas.coords(items["label"], x1 + 10, y1 + 10)

        self.canvas.itemconfig(
            items["label"],
            text=(
                f"Xcoord:{zone.x} "
                f"Ycoord:{zone.y} "
                f"Dimensions:{zone.width}x{zone.height} "
                f"Assigned:{assignment_text}"
                f"Type:{assignment_type_text} "
            ),
        )

    def delete_zone_canvas_items(self, zone):
        """
        Removes all canvas objects belonging to a zone.
        """

        items = self.zone_canvas_items.get(id(zone))

        if not items:
            return

        # Delete main rectangle
        self.canvas.delete(items["rectangle"])

        # Delete text label
        self.canvas.delete(items["label"])

        # Delete move handle
        self.canvas.delete(items["move_handle"])

        # Delete resize handles
        for handle_id in items["resize_handles"]:
            self.canvas.delete(handle_id)

        # Remove stored references
        del self.zone_canvas_items[id(zone)]

    def open_assignment_editor(self, event=None):
        """
        Opens a small popup for editing the selected zone assignment.
        """
        if self.selected_zone is None:
            print("No zone selected")
            return

        zone = self.selected_zone

        self.assignment_popup = tk.Toplevel(self.root)
        popup = self.assignment_popup

        popup.title("Zone Assignment")
        popup.geometry("300x200")

        # Keep popup above the overlay
        popup.attributes("-topmost", True)

        self.root.attributes("-disabled", True)
        # Make it the active window
        popup.focus_force()

        # ----------------------------
        # Assignment type dropdown
        # ----------------------------
        tk.Label(popup, text="Assignment Type").pack()

        self.assignment_type_var = tk.StringVar()
        type_var = self.assignment_type_var

        type_dropdown = ttk.Combobox(
            popup,
            textvariable=type_var,
            values=[
                AssignmentType.TITLE.value,
                AssignmentType.EXE.value,
                AssignmentType.CLASS.value,
            ],
            state="readonly",
        )

        type_dropdown.pack()

        # Existing assignment
        if zone.assignment:
            type_var.set(zone.assignment.type.value)
        else:
            type_var.set(AssignmentType.EXE.value)

        # ----------------------------
        # Assignment name
        # ----------------------------
        tk.Label(popup, text="Name").pack()

        self.assignment_name_entry = tk.Entry(popup)
        name_entry = self.assignment_name_entry

        name_entry.pack()

        if zone.assignment:
            name_entry.insert(0, zone.assignment.name)

        # ----------------------------
        # Save button
        # ----------------------------

        def save_assignment():

            name = name_entry.get().strip()

            if not name:
                error_label.config(text="Please enter an assignment name.")
                return

            error_label.config(text="")

            selected_type = AssignmentType(type_var.get())

            zone.assignment = Assignment(
                type=selected_type,
                name=name,
            )
            print()
            finish()

        error_label = tk.Label(popup, text="", fg="red")
        error_label.pack()

        tk.Button(
            popup,
            text="Save",
            command=save_assignment,
        ).pack(pady=10)

        # ---------------------------
        # Clear entry button
        # ---------------------------
        def remove_assignment():
            zone.assignment = None
            finish()

        tk.Button(
            popup,
            text="Clear Entry",
            command=remove_assignment,
        ).pack(pady=(5))

        # ---------------------------
        # Pick Window Assignment button
        # ---------------------------
        def pick_window():

            print("Pick Window clicked")
            self.assignment_zone = zone
            self.editor_mode = EditorMode.PICK_ASSIGNMENT

            popup.withdraw()
            print("Click a window to assign")
            print(self.editor_mode)

        tk.Button(
            popup,
            text="Pick Window",
            command=pick_window,
        ).pack(pady=(5))

        def finish():
            print(
                f"Zone Assigned to Type:{Assignment.type} Name:{Assignment.name}"
            )
            config.save_config(self.zone_manager.monitors)
            self.root.attributes("-disabled", False)
            popup.destroy()
            self.draw()

        # ----------------------------
        # Close popup (after finish this will close the popup)
        # ----------------------------

        def close_popup():
            self.root.attributes("-disabled", False)
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", close_popup)
