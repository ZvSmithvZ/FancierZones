import tkinter as tk


class ZoneOverlay:

    def __init__(self, monitors):

        self.monitors = monitors

        self.root = tk.Tk()

        # Remove normal window borders
        self.root.overrideredirect(True)

        # Keep above everything
        self.root.attributes("-topmost", True)

        # Make background transparent
        self.root.attributes("-alpha", 0.35)

        # Allow mouse clicks to pass through
        self.root.wm_attributes("-transparentcolor", "black")

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)

        self.canvas.pack(fill="both", expand=True)

    def draw(self):

        self.canvas.delete("all")

        for monitor in self.monitors:

            for zone in monitor.zones:

                x1 = zone.x
                y1 = zone.y

                x2 = zone.x + zone.width
                y2 = zone.y + zone.height

                self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3)

        self.root.update()

    def show(self):

        self.draw()

        self.root.mainloop()
