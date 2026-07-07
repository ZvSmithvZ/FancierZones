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
        self.root.attributes("-alpha", 0.35)

        # ------------------------------------------------------------
        # Transparent background
        #
        # The black pixels disappear.
        # The zone outlines remain visible.
        # ------------------------------------------------------------

        self.root.configure(bg="black")
        self.root.wm_attributes("-transparentcolor", "black")

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

    def draw(self):

        print("--------------------------------")
        print("Drawing zones:")

        self.canvas.delete("all")

        for monitor in self.monitors:

            print("MONITOR:", monitor.id, "position:", monitor.x, monitor.y)

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
                    text=f"{zone.width}x{zone.height}",
                    anchor="nw",
                    fill="white",
                )

        self.root.update()

    def show(self):

        self.draw()

        self.root.mainloop()
