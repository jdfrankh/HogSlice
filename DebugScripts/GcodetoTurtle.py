import turtle
import tkinter as tk
import sys
import os
import time

SCALE = 3  # pixels per mm


def parse_gcode(filepath):
    """Parse a gcode/gcgcode file into a list of (layer_number, commands) tuples."""
    layers = []
    current_layer = []
    current_layer_num = 0

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'):
                if line.startswith(';Layer '):
                    if current_layer:
                        layers.append((current_layer_num, current_layer))
                        current_layer = []
                    try:
                        current_layer_num = int(line.split()[0].replace(';Layer', ''))
                    except (ValueError, IndexError):
                        current_layer_num = len(layers) + 1
                continue
            current_layer.append(line)

    if current_layer:
        layers.append((current_layer_num, current_layer))

    return layers


def parse_command(line):
    """Parse a single gcode line into a dict of parameters."""
    parts = line.split()
    if not parts:
        return None, {}
    cmd = parts[0]
    params = {}
    for p in parts[1:]:
        if len(p) > 1 and p[0].isalpha():
            try:
                params[p[0]] = float(p[1:])
            except ValueError:
                pass
    return cmd, params


class GcodeViewer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.layers = parse_gcode(filepath)
        if not self.layers:
            print("No layers found in the file.")
            sys.exit(1)
        print(f"Parsed {len(self.layers)} layers from {filepath}")

        self.paused = False
        self.waiting_for_next = True
        self.skip_current = False
        self.drawing = False
        self.current_x = 0.0
        self.current_y = 0.0

        # --- Build the tkinter root with controls ---
        self.root = tk.Tk()
        self.root.title(f"Gcode Viewer - {os.path.basename(filepath)}")
        self.root.geometry("1050x900")
        self.root.protocol("WM_DELETE_WINDOW", self.quit_viewer)

        # Control frame at the top
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Speed slider
        tk.Label(ctrl_frame, text="Speed:").pack(side=tk.LEFT, padx=(0, 5))
        self.speed_var = tk.IntVar(value=10)
        self.speed_slider = tk.Scale(
            ctrl_frame, from_=0, to=1000, orient=tk.HORIZONTAL,
            variable=self.speed_var, length=200, showvalue=True
        )
        self.speed_slider.pack(side=tk.LEFT, padx=(0, 15))

        # Delay slider
        tk.Label(ctrl_frame, text="Delay (ms):").pack(side=tk.LEFT, padx=(0, 5))
        self.delay_var = tk.IntVar(value=10)
        self.delay_slider = tk.Scale(
            ctrl_frame, from_=0, to=200, orient=tk.HORIZONTAL,
            variable=self.delay_var, length=200, showvalue=True
        )
        self.delay_slider.pack(side=tk.LEFT, padx=(0, 15))

        # Zoom slider
        tk.Label(ctrl_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 5))
        self.zoom_var = tk.DoubleVar(value=SCALE)
        self.zoom_slider = tk.Scale(
            ctrl_frame, from_=0.5, to=20.0, resolution=0.5, orient=tk.HORIZONTAL,
            variable=self.zoom_var, length=150, showvalue=True
        )
        self.zoom_slider.pack(side=tk.LEFT, padx=(0, 15))

        # Pause button
        self.pause_btn = tk.Button(ctrl_frame, text="Pause", width=8, command=self.toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Next layer button
        self.next_btn = tk.Button(ctrl_frame, text="Next Layer", width=10, command=self.next_layer)
        self.next_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Quit button
        tk.Button(ctrl_frame, text="Quit", width=6, command=self.quit_viewer).pack(side=tk.LEFT)

        # Status label
        self.status_var = tk.StringVar(value="Press Next Layer to begin")
        tk.Label(ctrl_frame, textvariable=self.status_var, fg="darkgreen", font=("Courier", 10)).pack(
            side=tk.RIGHT, padx=10
        )

        # Turtle canvas
        canvas = tk.Canvas(self.root, width=1000, height=800)
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.screen = turtle.TurtleScreen(canvas)
        self.screen.bgcolor("white")
        self.screen.tracer(1)

        # Drawing turtle
        self.t = turtle.RawTurtle(self.screen)
        self.t.shape("circle")
        self.t.shapesize(0.3)
        self.t.pensize(1)

        # Label turtle
        self.label_turtle = turtle.RawTurtle(self.screen)
        self.label_turtle.hideturtle()
        self.label_turtle.penup()
        self.label_turtle.color("black")

        # Command turtle
        self.cmd_turtle = turtle.RawTurtle(self.screen)
        self.cmd_turtle.hideturtle()
        self.cmd_turtle.penup()
        self.cmd_turtle.color("darkgreen")

        # Keyboard bindings
        self.root.bind("<space>", lambda e: self.next_layer())
        self.root.bind("q", lambda e: self.quit_viewer())
        self.root.bind("p", lambda e: self.toggle_pause())
        self.root.bind("+", lambda e: self.zoom_in())
        self.root.bind("=", lambda e: self.zoom_in())
        self.root.bind("-", lambda e: self.zoom_out())
        canvas.bind("<MouseWheel>", self.on_mousewheel)

        # Start the layer loop
        self.layer_idx = 0
        self.waiting_for_next = True
        self.root.after(100, self.check_start)

        self.root.mainloop()

    def zoom_in(self):
        val = min(self.zoom_var.get() + 0.5, 20.0)
        self.zoom_var.set(val)

    def zoom_out(self):
        val = max(self.zoom_var.get() - 0.5, 0.5)
        self.zoom_var.set(val)

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Resume" if self.paused else "Pause")

    def next_layer(self):
        if self.waiting_for_next:
            self.waiting_for_next = False
        elif self.drawing:
            self.skip_current = True

    def quit_viewer(self):
        self.root.destroy()
        sys.exit(0)

    def check_start(self):
        """Wait for user to press Next Layer, then start drawing."""
        if self.waiting_for_next:
            self.root.after(50, self.check_start)
        else:
            self.draw_current_layer()

    def draw_current_layer(self):
        if self.layer_idx >= len(self.layers):
            self.status_var.set("All layers drawn. Press Q to quit.")
            return

        layer_num, commands = self.layers[self.layer_idx]

        # Clear previous
        self.t.clear()
        self.t.penup()
        self.t.goto(0, 0)
        self.current_x = 0.0
        self.current_y = 0.0

        # Label
        self.label_turtle.clear()
        cw = self.screen.window_width()
        ch = self.screen.window_height()
        self.label_turtle.goto(-cw // 2 + 20, ch // 2 - 40)
        self.label_turtle.write(f"Layer {layer_num}", font=("Arial", 16, "bold"))

        self.current_commands = commands
        self.cmd_idx = 0
        self.drawing = True
        self.skip_current = False
        self.draw_next_command()

    def draw_next_command(self):
        # Handle skip
        if self.skip_current:
            self.skip_current = False
            self.on_layer_complete()
            return

        # Handle pause
        if self.paused:
            self.root.after(50, self.draw_next_command)
            return

        if self.cmd_idx >= len(self.current_commands):
            self.on_layer_complete()
            return

        line = self.current_commands[self.cmd_idx]
        self.cmd_idx += 1

        cmd, params = parse_command(line)
        if cmd is None:
            self.root.after(1, self.draw_next_command)
            return

        # Display current command
        self.cmd_turtle.clear()
        cw = self.screen.window_width()
        ch = self.screen.window_height()
        self.cmd_turtle.goto(-cw // 2 + 20, ch // 2 - 70)
        self.cmd_turtle.write(f"> {line}", font=("Courier", 10, "normal"))

        speed = self.speed_var.get()

        zoom = self.zoom_var.get()

        if cmd == 'G0':
            self.t.speed(0)
            self.t.penup()
            self.t.color("gray")
            x = params.get('X', self.current_x)
            y = params.get('Y', self.current_y)
            self.t.goto(x * zoom, y * zoom)
            self.current_x, self.current_y = x, y

        elif cmd == 'G1':
            self.t.speed(min(speed, 10))
            x = params.get('X', self.current_x)
            y = params.get('Y', self.current_y)
            if 'E' in params:
                self.t.pendown()
                self.t.color("blue")
            else:
                self.t.penup()
                self.t.color("gray")
            self.t.goto(x * zoom, y * zoom)
            self.current_x, self.current_y = x, y

        speed = self.speed_var.get()
        # Higher speed values reduce delay; speed 0 uses slider delay as-is
        if speed > 10:
            delay = max(0, self.delay_var.get() - speed + 10)
        else:
            delay = self.delay_var.get()
        self.root.after(delay, self.draw_next_command)

    def on_layer_complete(self):
        layer_num = self.layers[self.layer_idx][0]
        total = len(self.layers)
        self.status_var.set(
            f"Layer {layer_num} complete ({self.layer_idx + 1}/{total})"
        )
        self.cmd_turtle.clear()
        cw = self.screen.window_width()
        ch = self.screen.window_height()
        self.cmd_turtle.goto(-cw // 2 + 20, ch // 2 - 70)
        self.cmd_turtle.write(
            f"Layer {layer_num} complete ({self.layer_idx + 1}/{total}) - Press SPACE / Next Layer",
            font=("Courier", 10, "normal")
        )

        self.drawing = False
        self.layer_idx += 1
        if self.layer_idx < total:
            self.waiting_for_next = True
            self.wait_for_next()
        else:
            self.status_var.set("All layers drawn. Press Q to quit.")

    def wait_for_next(self):
        if self.waiting_for_next:
            self.root.after(50, self.wait_for_next)
        else:
            self.draw_current_layer()


def main():
    if len(sys.argv) < 2:
        print("Usage: python GcodetoTurtle.py <file.gcode|file.gcgcode>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    GcodeViewer(filepath)


if __name__ == "__main__":
    main()
