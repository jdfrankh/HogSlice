import turtle
import numpy as np
from stl import mesh
from shapely.ops import linemerge, unary_union, polygonize
from shapely.geometry import LineString, MultiLineString, GeometryCollection, Point, Polygon
import vtk
import time


class gcodeShaper():

    TOL = 1e-4  # tolerance for connecting points

    gcode_lines = []

    #t = turtle.Turtle()
    t = None 

    # Parameters
    #FILENAME = "test.stl"   # your STL file
    LAYER_HEIGHT = 1.0       # mm per layer
    SCALE = 5                # pixels per mm for turtle drawing
    INFILL_SPACING = 2  # mm
    LASERPOWER = 100 # 0 to 100
    FEEDRATE = 1500  # mm/min

    def __init__(self):
        pass


    def gcode_move(self, x, y, z=None, extrude=False, feedrate=1500):
        """Write a G-code move for a printer."""
        if not extrude:
            cmd = "G1"
        elif extrude:
            cmd = "G0"  # simplified extrusion placeholder
        cmd += f" X{x:.3f} Y{y:.3f}"
        cmd += f" F{feedrate}"
        self.gcode_lines.append(cmd)

    def gcode_shift_layer(self):
        cmd = "M0 ; Shift Line"
        self.gcode_lines.append(cmd)

    def spacing_from_density(self, poly: Polygon, density: float, min_spacing=0.5):
        """Compute spacing between infill lines based on density (0..1)."""
        minx, miny, maxx, maxy = poly.bounds
        max_length = max(maxx - minx, maxy - miny)
        spacing = max_length * (1 - density)
        return max(spacing, min_spacing)  # avoid zero spacing


    def make_loops(self, segments):
        """Connect segments into closed loops."""
        loops = []
        segs = segments.copy()
        
        while segs:
            # Start new loop
            current = list(segs.pop(0).coords)
            extended = True
            while extended:
                extended = False
                i = 0
                while i < len(segs):
                    seg = segs[i]
                    start, end = seg.coords[0], seg.coords[1]
                    if Point(current[-1]).distance(Point(start)) < self.TOL:
                        current.append(end)
                        segs.pop(i)
                        extended = True
                    elif Point(current[-1]).distance(Point(end)) < self.TOL:
                        current.append(start)
                        segs.pop(i)
                        extended = True
                    elif Point(current[0]).distance(Point(end)) < self.TOL:
                        current = [start] + current
                        segs.pop(i)
                        extended = True
                    elif Point(current[0]).distance(Point(start)) < self.TOL:
                        current = [end] + current
                        segs.pop(i)
                        extended = True
                    else:
                        i += 1
            # Close loop if first and last are close
            if len(current) >= 4 and Point(current[0]).distance(Point(current[-1])) < self.TOL:
                current[-1] = current[0]
                loops.append(Polygon(current))
        return loops


    def draw_infill_loop(self, loop: Polygon, spacing, layer):
        minx, miny, maxx, maxy = loop.bounds
        y = miny
        while y <= maxy:
            line = LineString([(minx, y), (maxx, y)])
            clipped = line.intersection(loop)

            segments = []
            # Normalize all types to a list of LineStrings
            if clipped.is_empty:
                y += spacing
                continue
            elif isinstance(clipped, LineString):
                segments = [clipped]
            elif isinstance(clipped, MultiLineString):
                segments = list(clipped.geoms)
            elif isinstance(clipped, GeometryCollection):
                for g in clipped.geoms:
                    if isinstance(g, LineString):
                        segments.append(g)
            # Points are ignored (too small for infill)

            for seg in segments:
                x0, y0 = seg.coords[0]
                x1, y1 = seg.coords[-1]
                gz = layer * self.LAYER_HEIGHT
                self.t.penup()
                self.t.goto(x0*self.SCALE, y0*self.SCALE - layer*5)
                self.gcode_move(x0, y0, gz, extrude=False)  # move without extruding
                self.t.pendown()
                self.t.goto(x1*self.SCALE, y1*self.SCALE - layer*5)
                self.gcode_move(x0, y0, gz, extrude=True)  # move and extrude
                self.t.penup()

            y += spacing



    def is_valid_segment(self,line, tol=1e-6):
        """Return True if LineString has distinct endpoints."""
        x0, y0 = line.coords[0]
        x1, y1 = line.coords[-1]
        return abs(x0 - x1) > tol or abs(y0 - y1) > tol

    def draw_segments(self,segments, layer):
        """Draw all segments as lines for the turtle."""
        for seg in segments:
            x0, y0 = seg.coords[0]
            x1, y1 = seg.coords[1]
            gz = layer * self.LAYER_HEIGHT
            self.t.penup()
            self.t.goto(x0*self.SCALE, y0*self.SCALE - layer*5)
            self.gcode_move(x0, y0, gz, extrude=False)  # move without extruding
            self.t.pendown()
            self.t.goto(x1*self.SCALE, y1*self.SCALE - layer*5)
            self.gcode_move(x0, y0, gz, extrude=True)  # move and extrude
            self.t.penup()

    def sort_loops_by_area(self, loops):
        """Return loops sorted from largest to smallest area (outermost first)."""
        return sorted(loops, key=lambda p: p.area, reverse=True)
        
    def set_file_name(self, filename):
        self.FILENAME = filename

    def preareDebugEnviroment(self):

        self.t = turtle.Turtle()
        screen = turtle.Screen()
        screen.setup(1000, 800)
        self.t.speed(0)
        self.t.penup()



    #TODO: Import the printer that has the GCODE profile
    def run_mesh(self, infillPercent, power, speed, laserWidth, layerHeight ):
        """
        Accepts a rendered scene (e.g., a mesh or actor from Vulkan manager),
        extracts geometry, and converts it into sliceable data for G-code shaping.
        """
        print("Running mesh to G-code with settings - Infill: ", infillPercent, " Power: ", power, " Speed: ", speed, " Laser Width: ", laserWidth, " Layer Height: ", layerHeight)

        self.INFILL_SPACCING = (infillPercent -1) *laserWidth

        self.LASERPOWER = power
        self.FEEDRATE = speed

        self.LAYER_HEIGHT = np.float32(layerHeight)

        print(f" self.LAYER_HEIGHT: {self.LAYER_HEIGHT}, self.INFILL_SPACCING: {self.INFILL_SPACCING}, self.LASERPOWER: {self.LASERPOWER}, self.FEEDRATE: {self.FEEDRATE}")

        your_mesh = mesh.Mesh.from_file('enviroment.stl')

        zmin = np.min(your_mesh.z)
        zmax = np.max(your_mesh.z)
    
        # Set up turtle
        self.preareDebugEnviroment()


        # Slice layer by layer
        layer = 0
        z = zmin
        while z <= zmax:
                # erase everything drawn by the turtle
            segments = []
            # Intersect all triangles with horizontal plane
            for tri in your_mesh.vectors:
                points = []
                for j in range(3):
                    p1, p2 = tri[j], tri[(j+1)%3]
                    if (p1[2] - z) * (p2[2] - z) <= 0:
                        if p1[2] == p2[2]:
                            continue
                        tval = (z - p1[2]) / (p2[2] - p1[2])
                        x = p1[0] + tval*(p2[0] - p1[0])
                        y = p1[1] + tval*(p2[1] - p1[1])
                        points.append((x, y))
                if len(points) == 2:
                    line = LineString(points)
                    if self.is_valid_segment(line):
                        segments.append(line)

            # Draw all slice segments directly
            

            loops = self.make_loops(segments)

            loops_sorted = self.sort_loops_by_area(loops)

            #draw_segments(segments, layer)
            #for loop in loops:
            #    line_spacing = spacing_from_density(loop, density=1.6)  # 30% infill
            #    draw_infill_loop(loop, line_spacing, layer)

            for i, loop in enumerate(loops_sorted):
            # Draw the outline for the outermost loop
                if len(loops_sorted) > 0:
                    coords = list(loops_sorted[0].exterior.coords)
                    self.t.penup()
                    self.t.goto(coords[0][0]*self.SCALE, coords[0][1]*self.SCALE - layer*5)
                    self.t.pendown()
                    for x, y in coords[1:]:
                        self.t.goto(x*self.SCALE, y*self.SCALE - layer*5)
                    self.t.penup()

                # Draw the outline for the next loop (optional, for visual clarity)
                if len(loops_sorted) > 1:
                    coords = list(loops_sorted[1].exterior.coords)
                    self.t.penup()
                    self.t.goto(coords[0][0]*self.SCALE, coords[0][1]*self.SCALE - layer*5)
                    self.t.pendown()
                    for x, y in coords[1:]:
                        self.t.goto(x*self.SCALE, y*self.SCALE - layer*5)
                    self.t.penup()

                # Draw infill in the space between the two loops
                if len(loops_sorted) > 1:
                    shell_area = loops_sorted[0].difference(loops_sorted[1])
                    line_spacing = self.spacing_from_density(loops_sorted[0], 1.6)
                    self.draw_infill_loop(shell_area, line_spacing, layer)
                elif len(loops_sorted) == 1:
                    # If only one loop, fill the whole area
                    line_spacing = self.spacing_from_density(loops_sorted[0], 1.6)
                    self.draw_infill_loop(loops_sorted[0], line_spacing, layer)


           # print(f"Completed layer {layer} at z={z:.3f}: {type(z)}")
            z += self.LAYER_HEIGHT
            layer += 1
            self.gcode_shift_layer()
           # print("Layer: ", z)
            time.sleep(1)
            self.t.clear()

        with open("output.gcode", "w") as f:
            f.write("\n".join(self.gcode_lines))

        turtle.done()

if __name__ == "__main__":
    gcode = gcodeShaper()

    gcode.run_mesh()