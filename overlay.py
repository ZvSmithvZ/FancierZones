import tkinter as tk


class ZoneOverlay:

    def __init__(self, monitors):

        self.monitors = monitors

        # ------------------------------------------------------------
        # Find the full Windows virtual desktop bounds
        #
        # Example with 3 monitors:
        #
        # DISPLAY3       DISPLAY1       DISPLAY2
        # -1920            0             1920
        #
        # min_x becomes -1920
        # max_x becomes 3840
        #
        # This gives us one giant coordinate space.
        # ------------------------------------------------------------

        self.min_x = min(m.x for m in monitors)
        self.min_y = min(m.y for m in monitors)

        self.max_x = max(m.x + m.width for m in monitors)

        self.max_y = max(m.y + m.height for m in monitors)

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

        # Make overlay semi-transparent
        # self.root.attributes("-alpha", 0.35)

        # ------------------------------------------------------------
        # Transparent background
        #
        # The black pixels disappear.
        # The zone outlines remain visible.
        # ------------------------------------------------------------

        # self.root.configure(bg="black")
        # self.root.wm_attributes("-transparentcolor", "black")
        self.root.configure(bg="red")

        # ------------------------------------------------------------
        # Position overlay over the entire virtual desktop
        #
        # IMPORTANT:
        #
        # Windows coordinates:
        #
        # DISPLAY3:
        # x = -1920
        #
        # DISPLAY1:
        # x = 0
        #
        # DISPLAY2:
        # x = 1920
        #
        # The overlay starts at min_x.
        # Zone coordinates are converted later.
        # ------------------------------------------------------------

        # Tkinter handles negative X positions incorrectly sometimes.
        # Use geometry() first, then manually move the window.

        geometry = f"{self.virtual_width}x" f"{self.virtual_height}" "+0+0"

        print("--------------------------------")
        print("Overlay bounds:")
        print("min_x:", self.min_x)
        print("min_y:", self.min_y)
        print("width:", self.virtual_width)
        print("height:", self.virtual_height)
        print("geometry:", geometry)
        print("--------------------------------")

        print("Initial geometry:", geometry)
        self.root.geometry(geometry)

        # Force Tkinter to actually apply the geometry
        self.root.update_idletasks()

        # Now move it separately
        self.root.geometry(f"+{self.min_x}+{self.min_y}")

        # ------------------------------------------------------------
        # DEBUG:
        #
        # This tells us where Windows REALLY placed the overlay.
        #
        # If this prints:
        #     -1920 0
        #
        # the overlay is correct.
        #
        # If it prints:
        #     0 0
        #
        # Tkinter ignored the negative position.
        # ------------------------------------------------------------

        print("Actual overlay position:")
        print(self.root.winfo_x(), self.root.winfo_y())

        print("Actual overlay size:")
        print(self.root.winfo_width(), self.root.winfo_height())

        # ------------------------------------------------------------
        # Canvas where zones are drawn
        # ------------------------------------------------------------

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)

        self.canvas.pack(fill="both", expand=True)
        # ------------------------------------------------------------
        # Mouse editing state
        #
        # These store the rectangle currently being drawn.
        # ------------------------------------------------------------

        self.drag_start_x = None
        self.drag_start_y = None

        self.current_rectangle = None

        # ------------------------------------------------------------
        # Bind mouse events
        #
        # Button-1 = left mouse button
        # ------------------------------------------------------------

        self.canvas.bind("<ButtonPress-1>", self.mouse_down)

        self.canvas.bind("<B1-Motion>", self.mouse_drag)

        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)

    def draw(self):

        print("--------------------------------")
        print("Drawing zones:")

        self.canvas.delete("all")

        for monitor in self.monitors:

            print("MONITOR:", monitor.id, "position:", monitor.x, monitor.y)
            mx1 = monitor.x - self.min_x
            my1 = monitor.y - self.min_y

            mx2 = mx1 + monitor.width
            my2 = my1 + monitor.height
            self.canvas.create_rectangle(
                mx1,
                my1,
                mx2,
                my2,
                outline="blue",
                width=5,
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
                #
                # Example:
                #
                # Monitor 2 zone:
                #
                # x = 2120
                #
                # Overlay starts at:
                #
                # min_x = -1920
                #
                # Canvas coordinate:
                #
                # 2120 - (-1920)
                # = 4040
                #
                # ----------------------------------------------------

                x1 = zone.x - self.min_x
                y1 = zone.y - self.min_y

                x2 = x1 + zone.width
                y2 = y1 + zone.height

                print("ZONE:", zone.x, zone.y, "canvas:", x1, y1)

                # Draw rectangle
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3)

                # Label zone size
                self.canvas.create_text(
                    x1 + 10,
                    y1 + 10,
                    text=f"Xcoord:{zone.x} Ycoord:{zone.y} Dimensions:{zone.width}x{zone.height} Assigned:{zone.assignment}",
                    anchor="nw",
                    fill="white",
                )

        self.root.update()

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

    def process_events(self):
        """
        Allows Tkinter to process:
        - mouse clicks
        - mouse movement
        - redraw events

        without starting a second event loop.
        """

        if self.root:
            self.root.update()

    def mouse_down(self, event):
        """
        Starts drawing a new zone.
        """
        print("MOUSE DOWN RECEIVED")
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        print("Started zone:", self.drag_start_x, self.drag_start_y)

    def mouse_drag(self, event):
        """
        Updates the temporary rectangle while dragging.
        """
        print("MOUSE DRAG RECEIVED")
        if self.drag_start_x is None or self.drag_start_y is None:
            return

        # After the check above, tell Python/type checker
        # these are definitely numbers.
        start_x = self.drag_start_x
        start_y = self.drag_start_y

        # Remove old preview rectangle
        if self.current_rectangle:
            self.canvas.delete(self.current_rectangle)

        # Draw new preview rectangle
        self.current_rectangle = self.canvas.create_rectangle(
            start_x, start_y, event.x, event.y, outline="yellow", width=3
        )

    def mouse_up(self, event):
        """
        Finishes creating the zone.
        """

        if self.drag_start_x is None:
            return

        print("Finished zone:", self.drag_start_x, self.drag_start_y, event.x, event.y)

        # Reset drawing state
        self.drag_start_x = None
        self.drag_start_y = None
