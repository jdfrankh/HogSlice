# -*- coding: utf-8 -*-

import math
import sys
import string
import copy
import struct
import multiprocessing
from runtime_paths import get_runtime_path
import traceback

def _init_mp(_extrudeWidth, _delta, _supportInfill, _bedWidth, _triangles=None, _radialMaxSpacing=5.0):
    global extrudeWidth, delta, supportInfill, bedWidth, global_triangles, radialMaxSpacing
    extrudeWidth = _extrudeWidth
    delta = _delta
    supportInfill = _supportInfill
    bedWidth = _bedWidth
    global_triangles = _triangles
    radialMaxSpacing = _radialMaxSpacing

def _do_separate_and_clean(args):
    s, b0, b1, layerThickness = args
    currentSegment = []
    currentSegmentSurface = False

    if s <= (b0 + layerThickness) or s >= (b1 - layerThickness):
        currentSegmentSurface = True

    for triangle in global_triangles:
        point1 = intersectSlice(Line(p0_=triangle.p0, p1_=triangle.p1), s)
        point2 = intersectSlice(Line(p0_=triangle.p1, p1_=triangle.p2), s)
        point3 = intersectSlice(Line(p0_=triangle.p2, p1_=triangle.p0), s)

        # Collect non-None intersection points, deduplicated by coordinate equality.
        # (set() uses object identity for Point, not .equals(), so we dedupe manually.)
        points = []
        for p in (point1, point2, point3):
            if p is not None and not any(p.equals(q) for q in points):
                points.append(p)

        # Exactly 2 distinct points → one valid perimeter segment.
        # 0 or 1 point: triangle doesn't cross the plane (or touches at a vertex) → skip.
        # 3 points: plane is coplanar with the triangle face (flat top/bottom face).
        #   Generating three micro-segments here creates noise loops that pollute
        #   the perimeter and survive the closed-loop filter.  Skip entirely.
        if len(points) == 2:
            currentSegment.append(Line(points[0], points[1]))

    slice_obj = Slice(zValue_=s, perimeter_=currentSegment, isSurface_=currentSegmentSurface)
    return s, cleanPerimeter(slice_obj)

def _do_infill(args):
    idx, perimeter, percent, pattern = args
    if not isinstance(perimeter, list):
        return idx, []
    return idx, infill(perimeter, percent, pattern)

#printer specific constants, should be suplied as args
bedWidth = 150.0#mm
extrudeWidth = 0.71#mm
supportInfill = .5
delta = extrudeWidth/100.0 #delta for floating point comparison
radialMaxSpacing = 5.0  # mm – max arc gap between adjacent radial lines at the perimeter

# Written by sliceItem so callers can read part volume_cm3 after slicing
last_volume_cm3 = 0.0


def _polygon_area_mm2(lines):
    """Signed shoelace area (mm²) of a closed polygon described by a list of Line segments."""
    area = 0.0
    for line in lines:
        area += (line.p0.x * line.p1.y) - (line.p1.x * line.p0.y)
    return abs(area) * 0.5


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

class Point:
    def __init__(self, x_, y_, z_):
        self.x = x_
        self.y = y_
        self.z = z_

    def dotProduct(self, p):
        return self.x*p.x + self.y*p.y + self.z*p.z

    def normalize(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def toString(self):
        return "Point("+str(self.x)+","+str(self.y)+","+str(self.z)+")"
    def equals(self, p2):
        if close(self.x,p2.x) and close(self.y,p2.y) and close(self.z,p2.z):
            return True
        else:
            return False

def pointInLine(p, line):
    if close(p.x,line.p0.x) and close(p.y,line.p0.y) and close(p.z,line.p0.z):
        return True
    elif close(p.x,line.p1.x) and close(p.y,line.p1.y) and close(p.z,line.p1.z):
        return True
    else:
        return False

class Line:
    def __init__(self, p0_, p1_):
        self.p0 = p0_
        self.p1 = p1_

    def toString(self):
        return "Line("+self.p0.toString()+","+self.p1.toString()+")"
    def reverse(self):
        x_ = copy.copy(self.p0.x)
        y_ = copy.copy(self.p0.y)
        z_ = copy.copy(self.p0.z)
        self.p0.x = copy.copy(self.p1.x)
        self.p0.y = copy.copy(self.p1.y)
        self.p0.z = copy.copy(self.p1.z)
        self.p1.x = x_
        self.p1.y = y_
        self.p1.z = z_
        return self

#for floating point comparison
def close(f1,f2):
    comp = (max(f1,f2) - min(f1,f2))
    return (comp > -delta) and (comp < delta)

def lineEqual(L1,L2):
    if ((close(L1.p0.x, L2.p0.x) and close(L1.p0.y, L2.p0.y)
     and close(L1.p1.x, L2.p1.x) and close(L1.p1.y, L2.p1.y)) 
    or (close(L1.p0.x, L2.p1.x) and close(L1.p0.y, L2.p1.y) 
     and close(L1.p1.x, L2.p0.x) and close(L1.p1.y, L2.p0.y))):
        return True
    else:
        return False

class Triangle:
    def __init__(self, p0_, p1_, p2_, norm_):
        self.p0 = p0_
        self.p1 = p1_
        self.p2 = p2_
        self.norm = norm_
    def toString(self):
        return "Triangle("+self.p0.toString()+","+self.p1.toString()+","+self.p2.toString()+")"

def triangleEqual(T1,T2):
    if ((T1.p0.equals(T2.p0) and T1.p1.equals(T2.p1) and T1.p2.equals(T2.p2))
        or (T1.p0.equals(T2.p0) and T1.p1.equals(T2.p2) and T1.p2.equals(T2.p1))
        or (T1.p0.equals(T2.p1) and T1.p1.equals(T2.p0) and T1.p2.equals(T2.p2))
        or (T1.p0.equals(T2.p1) and T1.p1.equals(T2.p2) and T1.p2.equals(T2.p0))
        or (T1.p0.equals(T2.p2) and T1.p1.equals(T2.p0) and T1.p2.equals(T2.p1))
        or (T1.p0.equals(T2.p2) and T1.p1.equals(T2.p1) and T1.p2.equals(T2.p0))):
        return True
    else:
        return False

class Slice:
    def __init__(self, zValue_, perimeter_, isSurface_):
        self.zValue = zValue_
        self.perimeter = perimeter_
        self.isSurface = isSurface_
        self.support = list()
        self.infill = list()
        self.topBottom = list()
        self.sideWalls = list()

# given an stl file of standard format,
# returns a list of the triangles
def fileToTriangles(filename):
    # Detect binary vs ASCII STL
    with open(filename, 'rb') as f:
        header = f.read(80)
        num_triangles = struct.unpack('<I', f.read(4))[0]
        # A binary STL should be exactly 84 + 50 * num_triangles bytes
        f.seek(0, 2)
        file_size = f.tell()

    if file_size == 84 + 50 * num_triangles:
        return _readBinarySTL(filename, num_triangles)
    else:
        return _readAsciiSTL(filename)

def _readBinarySTL(filename, num_triangles):
    triangles = []
    with open(filename, 'rb') as f:
        f.read(84)  # skip header + triangle count
        for _ in range(num_triangles):
            data = struct.unpack('<12fH', f.read(50))
            norm = Point(data[0], data[1], data[2])
            p0 = Point(data[3], data[4], data[5])
            p1 = Point(data[6], data[7], data[8])
            p2 = Point(data[9], data[10], data[11])
            triangles.append(Triangle(p0, p1, p2, norm))
    return triangles

def _readAsciiSTL(filename):
    with open(filename, 'r') as f:
        next(f)
        counter = 0
        triangles = list()
        points = list()
        for line in f:
            l_ = line.strip().split()
            l = [value for value in l_ if value != '']
            if not l:
                continue
            if counter == 6:
                counter = 0
                continue
            elif counter == 0:
                if l[0] == 'endsolid':
                    break
                points.insert(0, Point(float(l[2]), float(l[3]), float(l[4])))
            elif counter == 2:
                points.insert(0, Point(float(l[1]), float(l[2]), float(l[3])))
            elif counter == 3:
                points.insert(0, Point(float(l[1]), float(l[2]), float(l[3])))
            elif counter == 4:
                points.insert(0, Point(float(l[1]), float(l[2]), float(l[3])))
            counter += 1

        while points:
            triangles.insert(0, Triangle(points[2], points[1], points[0], points[3]))
            points = points[4:]

        return triangles

# given a line segment and a plane,
# returns the point at which those two
# planes intersect. Will return the first point
# in the line if the whole line is in the plane
def intersectSlice(line, plane):
    if line.p0.z == line.p1.z and line.p1.z == plane:
        return line.p0
    elif line.p0.z == line.p1.z:
        return None
    else:
        slope = Point(x_=line.p1.x-line.p0.x, y_=line.p1.y-line.p0.y, z_=line.p1.z-line.p0.z)
        t = float(plane-line.p0.z)/float(slope.z)

        if t >= 0 and t <= 1:
            testZ = line.p0.z+t*slope.z
            if testZ <= max(line.p0.z, line.p1.z) and testZ >= min(line.p0.z, line.p1.z):
                testP = Point(x_=line.p0.x+t*slope.x, y_=line.p0.y+t*slope.y, z_=line.p0.z+t*slope.z)
                return Point(x_=line.p0.x+t*slope.x, y_=line.p0.y+t*slope.y, z_=line.p0.z+t*slope.z)

            else: 
                return None
        else:
            return None


#helper for aboveTriangle
def sign(p1, p2, p3):
    return (p1.x-p3.x)*(p2.y-p3.y) - (p2.x-p3.x)*(p1.y-p3.y)

# given a point and a triangle, 
# returns True if that point is directly above that triangle,
# False otherwise
def aboveTriangle(point,triangle):
    if  (point.z > (triangle.p0.z-delta) and
        point.z > (triangle.p1.z-delta) and
        point.z > (triangle.p2.z-delta)):

        b1 = (sign(point, triangle.p0, triangle.p1) < 0.0)
        b2 = (sign(point, triangle.p1, triangle.p2) < 0.0)
        b3 = (sign(point, triangle.p2, triangle.p0) < 0.0)
        ret = ((b1 == b2) and (b2 == b3))
        return ret

    else:
        return False
        
# given a list of triangles in 3D space,
# returns a tuple of the highest and lowest Z values
def findBoundaries(triangles):
    bottomZ = 500
    topZ = -500

    for triangle in triangles:
        maximum = max(triangle.p0.z, triangle.p1.z, triangle.p2.z)
        minimum = min(triangle.p0.z, triangle.p1.z, triangle.p2.z)

        if maximum > topZ:
            topZ = maximum
        if minimum < bottomZ:
            bottomZ = minimum

    return (bottomZ, topZ)

# given a list of triangles and a thickness per layer,
# computes the total number of layers and checks which
# line segments need to be drawn in each layer,
# returns the list of slices with the list of line segments
# to draw per slice, as a tuple with a bool for if the slice 
# is a bottom or top
def separateSlices(triangles, layerThickness):
    bounds = findBoundaries(triangles)
    numSlices = int((bounds[1]-bounds[0])/layerThickness)
    slices = [bounds[0]+z*layerThickness for z in range(0, numSlices+1)]
    segments = list()
    for s in slices:
        currentSegment = list()
        currentSegmentSurface = False
        for triangle in triangles:
            point1 = intersectSlice(Line(p0_=triangle.p0, p1_=triangle.p1), s)
            point2 = intersectSlice(Line(p0_=triangle.p1, p1_=triangle.p2), s)
            point3 = intersectSlice(Line(p0_=triangle.p2, p1_=triangle.p0), s)

            points_ = list(set([point1, point2, point3]))
            points = list()

            for point in points_:
                if point == None:
                    points_.remove(None)
                    break
            
            for i in range(0,len(points_)):
                j = i+1
                unique = True
                while j < len(points_):
                    if points_[i].equals(points_[j]):
                        unique = False
                    j+=1
                if unique:
                    points.insert(0,copy.deepcopy(points_[i]))

            if s <= (bounds[0]+layerThickness) or s >= (bounds[1]-layerThickness):
                currentSegmentSurface = True

            #if len(points) == 1:
                #currentSegment.append(Line(points[0], points[0]))
            if len(points) == 2:
                currentSegment.append(Line(points[0], points[1]))
            elif len(points) == 3:
                segment1 = Line(points[0], points[1])
                segment2 = Line(points[1], points[2])
                segment3 = Line(points[2], points[0])
                currentSegmentSurface = True

                currentSegment.append(segment1)
                currentSegment.append(segment2)
                currentSegment.append(segment3)
         
        segments.append(Slice(zValue_=s, perimeter_=copy.deepcopy(currentSegment),isSurface_=currentSegmentSurface))
        '''
        for line in currentSegment:
            print("appended "+line.toString())
        '''
    return segments

# given two lines on the same z plane, 
# returns the point at which they intersect,
# or None if there is no intersection
def intersection(L1,L2):

    #make sure all lines are on the same z plane
    #assert (math.isclose(L1.p0.z, L1.p1.z, abs_tol=0.0001))
    #assert (L2.p0.z == L2.p1.z)
    #assert (L1.p0.z == L2.p0.z)

    x1 = L1.p0.x
    y1 = L1.p0.y
    x2 = L1.p1.x
    y2 = L1.p1.y
    x3 = L2.p0.x
    y3 = L2.p0.y
    x4 = L2.p1.x
    y4 = L2.p1.y

    xnum = (x1*y2-y1*x2)*(x3-x4) - (x1-x2)*(x3*y4-y3*x4)
    xden = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    ynum = (x1*y2-y1*x2)*(y3-y4) - (y1-y2)*(x3*y4-y3*x4)
    yden = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

    try:
        intersect = Point(xnum/xden,ynum/yden,L1.p0.z) 

        if ((intersect.x >= min(x1,x2)-delta) and (intersect.x <= max(x1,x2)+delta) and
            (intersect.y >= min(y1,y2)-delta) and (intersect.y <= max(y1,y2)+delta) and
            (intersect.x >= min(x3,x4)-delta) and (intersect.x <= max(x3,x4)+delta) and
            (intersect.y >= min(y3,y4)-delta) and (intersect.y <= max(y3,y4)+delta)):
            return intersect
        else:
            return None
        # return intersect
    except:
        return None

def isInsidePolygon(point, perimeter, max_x, delta, Z):
    ray = Line(Point(point.x, point.y + 0.00137, Z), Point(max_x + 1000, point.y + 0.00137, Z))
    pt_inters = []
    for l in perimeter:
        sect = intersection(l, ray)
        if sect is not None:
            newHit = True
            for pt in pt_inters:
                if math.hypot(pt.x-sect.x, pt.y-sect.y) < delta:
                    newHit = False
                    break
            if newHit:
                pt_inters.append(sect)
    return len(pt_inters) % 2 != 0

#given a list of lines that make a manifold perimeter on a slice,
#and a percentage of space that should be infill,
#returns a list of infill lines (grid pattern) for that slice
#assumes print bed area is a square
def infill(perimeter, percent, pattern="Lines"):

    # Keep lower bound at 0, but allow values >1.0 for tightly packed top/bottom fill.
    percent = max(0.0, float(percent))

    if (len(perimeter) == 0):
        return []
    Z = perimeter[0].p0.z #should be the same across all lines

    # Build infill against the current slice footprint rather than a fixed bed window.
    xs = []
    ys = []
    for line in perimeter:
        xs.extend([line.p0.x, line.p1.x])
        ys.extend([line.p0.y, line.p1.y])

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    width = max(max_x - min_x, extrudeWidth)
    height = max(max_y - min_y, extrudeWidth)

    # Use width (the span that lines are distributed across) so that
    # gap = extrudeWidth / percent exactly, regardless of aspect ratio.
    target_span = max(width, height)   # kept for Radial/Honeycomb patterns only
    numLines = max(1, int(round((width * percent) / extrudeWidth)))

    gap = width / numLines
    infill = []

    if pattern == "Radial":
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Approximate radius from center to perimeter edge
        approx_radius = target_span / 2.0
        max_radial_spacing = max(0.001, radialMaxSpacing)

        # Minimum lines required so the arc between adjacent lines <= max_radial_spacing.
        # arc = radius * dtheta  =>  dtheta = spacing / radius
        # Lines needed to cover 180 degrees: ceil(pi / dtheta)
        if approx_radius > 0:
            min_lines_for_spacing = math.ceil(math.pi * approx_radius / max_radial_spacing)
        else:
            min_lines_for_spacing = 2

        # Base density from percent, capped to avoid insane counts
        base_count = max(2, numLines)

        # Use whichever is more, but hard-cap at 5000 lines to prevent hangs
        num_radial = min(max(base_count, min_lines_for_spacing), 5000)

        for r in range(num_radial):
            angle = r * (math.pi / num_radial)
            length = target_span * 2
            x_start = center_x - math.cos(angle) * length
            y_start = center_y - math.sin(angle) * length
            x_end   = center_x + math.cos(angle) * length
            y_end   = center_y + math.sin(angle) * length

            fullLine = Line(Point(x_start, y_start, Z), Point(x_end, y_end, Z))
            inters = []

            for line in perimeter:
                sect = intersection(line, fullLine)
                if sect is not None:
                    new = True
                    for i in inters:
                        if math.hypot(i.x-sect.x, i.y-sect.y) < delta:
                            new = False
                    if new:
                        inters.append(sect)

            inters.sort(key=lambda p: math.hypot(p.x-x_start, p.y-y_start))

            for i in range(1, len(inters)):
                newLine = Line(inters[i-1], inters[i])
                if math.hypot(newLine.p0.x - newLine.p1.x, newLine.p0.y - newLine.p1.y) < delta:
                    continue
                mx = (newLine.p0.x + newLine.p1.x) / 2
                my = (newLine.p0.y + newLine.p1.y) / 2
                if isInsidePolygon(Point(mx, my, Z), perimeter, max_x + target_span, delta, Z):
                    overlap = False
                    for l in perimeter:
                        if lineEqual(l, newLine):
                            overlap = True
                            break
                    if not overlap:
                        infill.append(newLine)

        return infill

    elif pattern == "Honeycomb":
        # Simple cross-hatch for now since true hex math is quite involved for a quick patch
        hex_gap = gap * 1.5
        # Line pattern 1 (horizontal)
        for y in range(int(height / hex_gap) + 1):
            y_pos = min_y + (y * hex_gap)
            fullLine = Line(Point(min_x, y_pos, Z), Point(max_x, y_pos, Z))
            inters = []
            for line in perimeter:
                sect = intersection(line, fullLine)
                if sect is not None:
                    new = True
                    for i in inters:
                        if abs(i.x - sect.x) < delta:
                            new = False
                    if new:
                        inters.append(sect)
            inters.sort(key=lambda p: p.x)
            for i in range(1, len(inters)):
                newLine = Line(inters[i-1], inters[i])
                mx = (newLine.p0.x + newLine.p1.x) / 2
                my = (newLine.p0.y + newLine.p1.y) / 2
                if isInsidePolygon(Point(mx, my, Z), perimeter, max_x + target_span, delta, Z):
                    overlap = False
                    for l in perimeter:
                        if lineEqual(l, newLine):
                            overlap = True
                            break
                    if not overlap:
                        infill.append(newLine)
        
        # Line pattern 2 (vertical)
        for x in range(int(width / hex_gap) + 1):
            x_pos = min_x + (x * hex_gap)
            fullLine = Line(Point(x_pos, min_y, Z), Point(x_pos, max_y, Z))
            inters = []
            for line in perimeter:
                sect = intersection(line, fullLine)
                if sect is not None:
                    new = True
                    for i in inters:
                        if abs(i.y - sect.y) < delta:
                            new = False
                    if new:
                        inters.append(sect)
            inters.sort(key=lambda p: p.y)
            for i in range(1, len(inters)):
                newLine = Line(inters[i-1], inters[i])
                mx = (newLine.p0.x + newLine.p1.x) / 2
                my = (newLine.p0.y + newLine.p1.y) / 2
                if isInsidePolygon(Point(mx, my, Z), perimeter, max_x + target_span, delta, Z):
                    overlap = False
                    for l in perimeter:
                        if lineEqual(l, newLine):
                            overlap = True
                            break
                    if not overlap:
                        infill.append(newLine)

        # Line pattern 3 (diagonal)
        diag_lines = max(1, int(round((target_span * percent) / hex_gap)))
        diag_gap = target_span / diag_lines
        for d in range(diag_lines + 1):
            offset = d * diag_gap
            fullLine = Line(Point(min_x, min_y + offset, Z), Point(max_x, max_y + offset, Z))
            inters = []
            for line in perimeter:
                sect = intersection(line, fullLine)
                if sect is not None:
                    new = True
                    for i in inters:
                        if math.hypot(i.x-sect.x, i.y-sect.y) < delta:
                            new = False
                    if new:
                        inters.append(sect)
            inters.sort(key=lambda p: p.x)
            for i in range(1, len(inters)):
                newLine = Line(inters[i-1], inters[i])
                mx = (newLine.p0.x + newLine.p1.x) / 2
                my = (newLine.p0.y + newLine.p1.y) / 2
                if isInsidePolygon(Point(mx, my, Z), perimeter, max_x + target_span, delta, Z):
                    overlap = False
                    for l in perimeter:
                        if lineEqual(l, newLine):
                            overlap = True
                            break
                    if not overlap:
                        infill.append(newLine)
        
        return infill

    # Default pattern: Lines (vertical lines)
    # Offset by gap/2 so lines are centered in each cell — none land on the
    # perimeter boundary, and we always get exactly numLines interior lines.
    for x in range(numLines):

        x_pos = min_x + (x + 0.5) * gap
        fullLine = Line(Point(x_pos, min_y, Z), Point(x_pos, max_y, Z))
        inters = []

        #find intersections without repeats
        for line in perimeter:
            sect = intersection(line,fullLine)
            if (sect != None):
                new = True
                for i in inters:
                    if close(i.y,sect.y):
                        new = False
                if new:
                    inters.append(copy.deepcopy(sect))

        #sort by y to get matching pairs for internal lines
        inters.sort(key=lambda point: point.y)
        
        if len(inters)%2 == 0: #if not even then something went wrong and its safer not to print
            for i in range(len(inters)):
                if i%2 != 0:
                    overlap = False;
                    newLine = Line(inters[i-1],inters[i])
                    for l in perimeter:
                        if lineEqual(l,newLine):
                            overlap = True;
                    if not overlap:
                        # Midpoint check: verify the fill segment actually sits
                        # inside the shape.  The even-odd pair count can be
                        # fooled by stray/open perimeter segments on complex
                        # meshes, producing lines that span voids or bleed
                        # outside the boundary.  isInsidePolygon provides a
                        # conservative fallback — skip any line whose midpoint
                        # isn't genuinely inside.
                        mx = (newLine.p0.x + newLine.p1.x) / 2
                        my = (newLine.p0.y + newLine.p1.y) / 2
                        if isInsidePolygon(Point(mx, my, Z), perimeter, max_x + width, delta, Z):
                            infill.append(newLine)
        '''
        else:
            print("Perimeter not manifold\n")
            print("fullLine: "+fullLine.toString())
            for line in perimeter:
                print(line.toString())
            print(" ")
            for p in inters:
                print(p.toString())
            print(" ")
        '''
    return infill


# given a list of line segments and a starting point,
# returns the location of the next line that connects to the points,
# or None if no point follows
def findNextPoint(point, lines):
    for i in range(0, len(lines)):
        line = lines[i]
        if pointInLine(point, line):
            return i
    return None

# given a slice with a list of line segments,
# returns a new slice free of duplicate or interior line segments
# and in order for optimized drawing
def cleanPerimeter(s):
    """
    Cleans a raw slice perimeter produced by triangle-plane intersection:
      1. Drop zero/degenerate segments (plane tangent to a vertex).
      2. Remove exact duplicates (shared triangle edges intersected twice).
      3. Chain segments into connected loops, reversing where needed.
      4. Discard any open chains (fragment noise that never closes).
      5. Discard noise loops shorter than one extrude width.
    Returns a new Slice whose perimeter segments are ordered and clean.
    """
    segs = copy.deepcopy(s.perimeter)

    # --- 1. Drop degenerate (zero/near-zero length) segments ---
    # STL intersection at a vertex produces Line(p, p). Minimum real edge
    # length for any printable geometry is at least one laser width.
    min_seg = extrudeWidth * 0.05
    segs = [seg for seg in segs
            if math.hypot(seg.p1.x - seg.p0.x, seg.p1.y - seg.p0.y) >= min_seg]

    # --- 2. Remove duplicates (same segment, forward or reversed) ---
    deduped = []
    for seg in segs:
        if not any(lineEqual(seg, d) for d in deduped):
            deduped.append(seg)
    segs = deduped

    # --- 3. Chain segments into loops ---
    # STL verts are 32-bit floats; in theory shared vertices between triangles
    # are bit-identical, but some CAD exporters introduce sub-millimetre gaps
    # (up to ~0.05 mm) between what should be adjacent endpoints.  Use a snap
    # tolerance large enough to bridge these gaps without accidentally jumping
    # across the space between distinct geometric features (typically ≥ 1 mm).
    snap_tol = extrudeWidth * 0.1   # ~0.07 mm — tolerates typical exporter drift

    # Separate, tighter tolerance for the closure check so we don't seal a
    # loop that is genuinely open (e.g. a boundary arc that was never capped).
    close_tol = extrudeWidth * 0.5   # ~0.35 mm — loop considered closed

    remaining = list(segs)
    chains = []
    while remaining:
        chain = [remaining.pop(0)]
        grew = True
        while grew:
            grew = False
            head = chain[0].p0
            tail = chain[-1].p1
            for i, seg in enumerate(remaining):
                d00 = math.hypot(seg.p0.x - tail.x, seg.p0.y - tail.y)
                d01 = math.hypot(seg.p1.x - tail.x, seg.p1.y - tail.y)
                if d00 < snap_tol:
                    chain.append(remaining.pop(i)); grew = True; break
                elif d01 < snap_tol:
                    chain.append(Line(Point(seg.p1.x, seg.p1.y, seg.p1.z),
                                      Point(seg.p0.x, seg.p0.y, seg.p0.z)))
                    remaining.pop(i); grew = True; break
                # Also try prepending to the head of the chain
                d10 = math.hypot(seg.p1.x - head.x, seg.p1.y - head.y)
                d11 = math.hypot(seg.p0.x - head.x, seg.p0.y - head.y)
                if d10 < snap_tol:
                    chain.insert(0, remaining.pop(i)); grew = True; break
                elif d11 < snap_tol:
                    chain.insert(0, Line(Point(seg.p1.x, seg.p1.y, seg.p1.z),
                                         Point(seg.p0.x, seg.p0.y, seg.p0.z)))
                    remaining.pop(i); grew = True; break
        chains.append(chain)

    # --- 4. Discard open chains; only emit closed loops ---
    # A real perimeter forms a closed polygon: the tail of the last segment
    # connects back to the head of the first.  Open fragments are noise from
    # non-manifold mesh edges or boundary triangles.
    result = []
    for chain in chains:
        head = chain[0].p0
        tail = chain[-1].p1
        is_closed = math.hypot(tail.x - head.x, tail.y - head.y) < close_tol

        # --- 5. Discard short noise loops ---
        total_len = sum(math.hypot(seg.p1.x - seg.p0.x, seg.p1.y - seg.p0.y)
                        for seg in chain)
        if is_closed and total_len >= extrudeWidth:
            result.extend(chain)

    return Slice(zValue_=s.zValue, perimeter_=result, isSurface_=s.isSurface)


def _split_perimeter_into_loops(perimeter):
    """
    Split a chained, concatenated perimeter (output of cleanPerimeter) back
    into individual closed loops.  Consecutive segments within a loop share an
    endpoint; a gap in the chain marks the boundary between two loops.

    Uses the same snap tolerance as cleanPerimeter's chaining step so that
    the loops are split at exactly the same boundaries they were chained at.
    Separate loops (outer boundary vs. hole boundaries) have inter-loop gaps
    of several mm, far larger than this tolerance.
    """
    if not perimeter:
        return []
    snap = extrudeWidth * 0.1   # must match cleanPerimeter snap_tol
    loops, current = [], [perimeter[0]]
    for seg in perimeter[1:]:
        tail = current[-1].p1
        if math.hypot(seg.p0.x - tail.x, seg.p0.y - tail.y) < snap:
            current.append(seg)
        else:
            loops.append(current)
            current = [seg]
    loops.append(current)
    return loops


def _offset_loop_inward(loop, distance):
    """
    Inward offset of one closed polygon loop by `distance`, using per-edge
    inward unit normals and miter joins at vertices.

    - Winding order is detected via signed area (CCW / CW) so the normal
      direction is always into the interior, regardless of how the loop was
      wound.
    - Miter distance is capped at 4× to prevent runaway spikes at very
      acute corners.
    - Returns [] if the offset loop flipped winding (i.e. it collapsed
      through itself — feature is too small for this wall pass).
    """
    if len(loop) < 2:
        return []

    pts = [seg.p0 for seg in loop]
    z   = pts[0].z
    n   = len(pts)

    # Signed area (×2): positive = CCW, negative = CW
    area2 = sum(pts[i].x * pts[(i+1) % n].y - pts[(i+1) % n].x * pts[i].y
                for i in range(n))
    if abs(area2) < 1e-10:
        return []
    winding = 1.0 if area2 > 0 else -1.0

    # Per-edge inward unit normals.
    # For a CCW polygon, the inward normal of edge (p→q) is the left-hand
    # perpendicular: (-dy, dx) / |edge|.
    # For CW, flip by negating (multiply by winding).
    enorm = []
    for i in range(n):
        p0, p1 = pts[i], pts[(i + 1) % n]
        dx, dy = p1.x - p0.x, p1.y - p0.y
        L = math.sqrt(dx*dx + dy*dy)
        if L < 1e-9:
            enorm.append((0.0, 0.0))
        else:
            enorm.append((-dy / L * winding, dx / L * winding))

    # Per-vertex miter offset: average the two adjacent edge normals,
    # then scale so the vertex sits at `distance` from both edges.
    off_pts = []
    for i in range(n):
        n0 = enorm[(i - 1) % n]
        n1 = enorm[i]
        ax = (n0[0] + n1[0]) * 0.5
        ay = (n0[1] + n1[1]) * 0.5
        alen = math.sqrt(ax*ax + ay*ay)
        if alen < 1e-9:
            # Degenerate corner (nearly reversed edges) — skip offset
            off_pts.append(Point(pts[i].x, pts[i].y, z))
            continue
        # Miter length = distance / alen; cap at 4× to avoid giant spikes
        d = min(distance / alen, 4.0 * distance)
        off_pts.append(Point(
            pts[i].x + ax / alen * d,
            pts[i].y + ay / alen * d,
            z
        ))

    # Reject if offset loop has flipped winding (collapsed through itself)
    off_area2 = sum(off_pts[i].x * off_pts[(i+1) % n].y -
                    off_pts[(i+1) % n].x * off_pts[i].y
                    for i in range(n))
    if (off_area2 > 0) != (area2 > 0):
        return []
    if abs(off_area2) < abs(area2) * 0.01:
        return []

    # Build output segments, skipping degenerate (zero-length) ones
    out = []
    for i in range(n):
        p0 = off_pts[i]
        p1 = off_pts[(i + 1) % n]
        if math.hypot(p1.x - p0.x, p1.y - p0.y) >= extrudeWidth * 0.05:
            out.append(Line(p0, p1))
    return out


def offsetPerimeter(perimeter, distance):
    """
    Offsets each closed loop in the perimeter inward by `distance`.

    The old implementation computed a single centroid from ALL perimeter
    points (including inner holes) and pushed every point toward it.  On
    multi-loop perimeters this produces segments that cross the entire part.

    The new implementation splits the perimeter back into its constituent
    closed loops and offsets each one independently using proper inward edge
    normals, so every inner wall is a scaled copy of its own contour.
    """
    if not perimeter:
        return []
    result = []
    for loop in _split_perimeter_into_loops(perimeter):
        result.extend(_offset_loop_inward(loop, distance))
    return result



# given the number of walls and a list of slices,
# generates inner wall perimeters for each slice
# numSideWalls includes the original perimeter (1 = no extra walls)
# returns the slices with walls added to each slice's perimeter
def generateWalls(numSideWalls, slices):
    for s in slices:
        if numSideWalls <= 1:
            s.sideWalls = []
            continue
        # Group by loop first, then by inset depth, so each island's concentric
        # shells are printed consecutively before moving to the next island.
        # This matches the traversal order of the outer perimeter (one loop at a
        # time) and avoids long travel jumps between islands.
        loops = _split_perimeter_into_loops(s.perimeter)
        sideWalls = []
        for loop in loops:
            for w in range(1, numSideWalls):
                sideWalls.extend(_offset_loop_inward(loop, extrudeWidth * w))
        s.sideWalls = sideWalls
    return slices


# pseudocode for computing brim of a single convex polyhedron base
# takes a listof(line segments) which are the base (bottom layer),
# a number of outlines, and an initial offset
# will also generate a skirt if offset is greater than 1 and number of outlines = 1
def brim(base, numOutlines, offset):
    # compute centroid of polygonal manifold
    cx = 1
    cy = 1
    area = 1
    for line in base:
        cx = cx * (line.p0.x + line.p1.x)
        cy = cy * (line.p0.y + line.p1.y)
        area *= (line.p0.x * line.p1.y - line.p1.x * line.p0.y)
    area = area / 2
    cx = cx / (6 * area)
    cy = cy / (6 * area)

    # generate outlines
    brimlines = list()
    for i in range(1, numOutlines+1):
        for line in base:
            line_ = Line(Point(line.p0.x, line.p0.y, line.p0.z), Point(line.p1.x, line.p1.y, line.p1.z))

            if line.p0.x > cx:
                line_.p0.x += offset + extrudeWidth * i
            else:
                line_.p0.x -= offset + extrudeWidth * i
            if line.p0.y > cy:
                line_.p0.y += offset + extrudeWidth * i
            else:
                line_.p0.y -= offset + extrudeWidth * i
            if line.p1.x > cx:
                line_.p1.x += offset + extrudeWidth * i
            else:
                line_.p1.x -= offset + extrudeWidth * i
            if line.p1.y > cy:
                line_.p1.y += offset + extrudeWidth * i
            else:
                line_.p1.y -= offset + extrudeWidth * i
            brimlines.append(line_)
    
    return brimlines


# pseudocode for computing a basic rectangular raft
# takes number of layers, an offset (how far raft extends from object), and an infill percentage
# and a listof(listof(line segments)) representing the object
# NOTE: raft goes UNDERNEATH object, all object / infill / support layers must be shifted up by
# height of raft (the brim, if used, is the same layer as raft and does not need to be elevated)
def raft(slices, numLayers, offset, infill, layerThickness):
    # compute enclosing rectangle on object
    x = 0
    y = 0
    x_ = 0
    y_ = 0
    for s in slices:
        for line in s.perimeter:
            if line.p0.x > x or line.p1.x > x:
                x = line.p0.x if line.p0.x > line.p1.x else line.p1.x
            if line.p0.x < x_ or line.p1.x < x_:
                x_ = line.p0.x if line.p0.x < line.p1.x else line.p1.x
            if line.p0.y > y or line.p1.y > y:
                y = line.p0.y if line.p0.y > line.p1.y else line.p1.y
            if line.p0.y < y_ or line.p1.y < y_:
                y_ = line.p0.y if line.p0.y < line.p1.y else line.p1.y

    x += offset
    y += offset
    x_ -= offset
    y_ -= offset
    # compute number of lines and gaps
    xlen = x - x_
    ylen = y - y_
    area  =  xlen * ylen
    totalArea = area * infill
    xlines = math.floor(totalArea / (extrudeWidth * xlen))
    xgap = (ylen - extrudeWidth * xlines) / xlines
    ylines = math.floor(totalArea / (extrudeWidth * ylen))
    ygap = (xlen - extrudeWidth * ylines) / ylines
    # generate layers
    i = 0
    z = slices[0].zValue
    allSegments = list()
    lines = list()
    switch = True
    while i < numLayers:
        if numLayers - i <= 1:
            lines_ = list(Line(p0_=Point(x_,y_,z),p1_=Point(x_,y,z)), Line(p0_=Point(x_,y,z),p1_=Point(x,y,z)), Line(p0_=Point(x,y,z),p1_=Point(x,y_,z)), Line(p0_=Point(x,y_,z),p1_=Point(x_,y_,z)))
            lines += lines_
            lines += infill(lines_, 1.0)
        # lines and its infill to create a solid surface

        elif i % 2 == 1:
            for k in range(0, xlines):
                if switch == True:
                    lines += list(Line(p0_=Point(x_,y_+ygap * k,z),p1_=Point(x,y_+ygap * k,z)), Line(p0_=Point(x,y_+ygap * k,z),p1_=Point(x,y_+ygap*(k+1),z)))
                    switch = False
                else:
                    lines += list(Line(p0_=Point(x,y_+ygap * k,z),p1_=Point(x_,y_+ygap* k,z)), Line(p0_=Point(x_,y_+ygap *k,z), p1_=Point(x_,y_+ygap * (k+1), z)))
                    switch = True
            
        elif i % 2 == 0:
            for k in range(0,xlines):
                if switch == True:
                    lines += list(Line(p0_=Point(x-xgap * k, y_,z),p1_=Point(x-xgap * k, y, z)), Line(p0_=Point(x-xgap * k,y,z),p1_=Point(x-xgap * (k-1),y,z)))
                    switch = False
        else:
            lines  += list(Line(p0_=Point(x-xgap * k,y,z),p1_=Point(x-xgap * k,y_,z)), Line(p0_=Point(x-xgap * k,y_,z),p1_=Point(x-xgap * (k+1),y_,z))) 
            switch = True
        allSegments.append(lines)
        switch = True
        z += layerThickness
    return allSegments

# given a list of triangles,
# returns a list of any downward-facing triangles
def downward(triangles):
    trianglesDown = list()
    for triangle in triangles:
        if triangle.norm.z < 0:
            trianglesDown.insert(0, copy.deepcopy(triangle))
    return trianglesDown

# given a downward-facing triangle and a list of all triangles,
# returns True if no triangles are in the way of the downward triangle
# and False if a triangle blocks the path directly downward
def supportNeeded(triangle, triangles, bottomZ):
    if (close(triangle.p0.z, bottomZ)
        and close(triangle.p1.z, bottomZ)
        and close(triangle.p2.z, bottomZ)):
        return False

    for tri in triangles:
        if (aboveTriangle(triangle.p0, tri) 
            or aboveTriangle(triangle.p1, tri) 
            or aboveTriangle(triangle.p2, tri)):
            return False

    return True


# given a triangle that requires support and a minimum Z value,
# returns the list of triangles required to form the support shape under that triangle
def generateSupportShape(triangle, bottomZ):
    triangleTop = copy.deepcopy(triangle)
    triangleBottom = Triangle(Point(triangleTop.p0.x, triangleTop.p0.y, bottomZ), 
                                Point(triangleTop.p1.x, triangleTop.p1.y, bottomZ), 
                                Point(triangleTop.p2.x, triangleTop.p2.y, bottomZ), None)
    newShape = [triangleTop]
    newShape.insert(0, triangleBottom)

    newShape.insert(0, Triangle(triangleTop.p0, triangleTop.p1, triangleBottom.p0, None))
    newShape.insert(0, Triangle(triangleTop.p1, triangleTop.p2, triangleBottom.p1, None))
    newShape.insert(0, Triangle(triangleTop.p2, triangleTop.p0, triangleBottom.p2, None))
    newShape.insert(0, Triangle(triangleBottom.p0, triangleBottom.p1, triangleTop.p1, None))
    newShape.insert(0, Triangle(triangleBottom.p1, triangleBottom.p2, triangleTop.p2, None))
    newShape.insert(0, Triangle(triangleBottom.p2, triangleBottom.p0, triangleTop.p0, None))

    i = 0
    while i < len(newShape):
        j = i+1
        while j < len(newShape):
            if triangleEqual(newShape[i],newShape[j]):
                newShape.remove(newShape[j])
            else:
                j+=1
        i+=1

    return newShape

def _do_support_needed(args):
    tri, b0 = args
    if supportNeeded(tri, global_triangles, b0):
        return tri
    return None

# given a list of triangles
# returns a list of list of slices to draw supports for any downward-facing triangles
#returns a list of lists of slices
def generateSupports(triangles, layerThickness):

    bounds = findBoundaries(triangles)
    trianglesDown = downward(triangles)
    
    cores = max(1, multiprocessing.cpu_count() // 4)
    pool = multiprocessing.Pool(processes=cores, initializer=_init_mp, initargs=(extrudeWidth, delta, supportInfill, bedWidth, triangles))
    
    tasks = [(tri, bounds[0]) for tri in trianglesDown]
    trianglesForSupport = []
    
    for res in pool.imap_unordered(_do_support_needed, tasks):
        if res is not None:
            trianglesForSupport.insert(0, copy.deepcopy(res))
    
    pool.close()
    pool.join()

    supportShapes = list()
    for triangle in trianglesForSupport:
        supportShapes.insert(0, generateSupportShape(triangle, bounds[0]))

    supportSlices = list()

    for shape in supportShapes:
        supportSlices.insert(0, separateSlices(shape, layerThickness))

    return supportSlices


def getTopBottomSurfaceIndices(slices, numBottom, numTop, detection_height=0.5, layer_thickness=0.1):
    """
    Area-ratio surface detection.

    A layer is flagged as TOP surface when the cross-section area found
    ``numTop`` layers above it (the "anchor" layer at the far edge of the
    solid fill region) is less than SURFACE_AREA_RATIO of the current area.

    Using the anchor layer (numTop away) instead of the nearest layer above
    breaks the cascade that previously flagged every layer of a steep taper
    (e.g. a cone) as a top surface.  Each layer's check is now independent:
    shifting the comparison point forward by ``numTop`` means a layer only
    gets flagged when there is a genuine drop in cross-section *across the
    entire fill window*, not just between two consecutive layers.

    Handles:
      - Absolute tops (no layers above) → always flagged.
      - Ledges: a plate with a narrow boss on top — the plate top is
        detected because area numTop layers up equals the small boss footprint.
      - Gentle tapers (cone) → area at numTop layers up is still close to
        current area, so NOT flagged (infill is preserved).
      - Steep tapers → only the layers near the actual tip are flagged.

    ``detection_height`` (mm) is used only to skip degenerate empty layers
    caused by coplanar mesh faces when looking for the anchor area.

    Bottom detection is the symmetric case.
    """
    SURFACE_AREA_RATIO = 0.80   # flag if area at anchor < 80 % of current

    total     = len(slices)
    numBottom = int(max(0, numBottom))
    numTop    = int(max(0, numTop))
    # skip window: how many layers to scan when searching for a non-empty anchor
    skip      = max(1, round(detection_height / max(layer_thickness, 1e-6)))

    # Precompute per-layer perimeter areas once (0 for empty layers)
    areas = [_polygon_area_mm2(s.perimeter) if s.perimeter else 0.0
             for s in slices]

    surface_indices = set()

    for i in range(total):
        area_i = areas[i]
        if area_i <= 0:
            continue

        # --- TOP surface ---
        # Check the anchor layer numTop positions above layer i.
        # If the part has shrunk significantly at that point, layer i is at
        # (or near) a top surface.  Using numTop as the lookahead distance
        # means the comparison is anchored at the boundary of the fill region,
        # so each layer's check is independent and cascades are impossible.
        anchor_top = i + numTop
        if anchor_top >= total:
            # Within numTop of the part's absolute top — scan for nearest
            # non-empty layer to see whether there is any material at all.
            above = [areas[j] for j in range(i + 1, min(i + skip + 1, total))
                     if areas[j] > 0]
            area_at_anchor = above[0] if above else 0.0
        else:
            # Find nearest non-empty layer at or near the anchor position
            # (handles degenerate empty layers from coplanar mesh faces).
            candidates = [areas[j]
                          for j in range(anchor_top, min(anchor_top + skip + 1, total))
                          if areas[j] > 0]
            area_at_anchor = candidates[0] if candidates else 0.0

        if area_at_anchor < area_i * SURFACE_AREA_RATIO:
            for k in range(max(0, i - numTop + 1), i + 1):
                if areas[k] > 0:
                    surface_indices.add(k)

        # --- BOTTOM surface ---
        # Symmetric: anchor numBottom positions below layer i.
        anchor_bot = i - numBottom
        if anchor_bot < 0:
            below = [areas[j] for j in range(max(0, i - skip), i)
                     if areas[j] > 0]
            area_at_anchor_bot = below[-1] if below else 0.0
        else:
            candidates = [areas[j]
                          for j in range(max(0, anchor_bot - skip), anchor_bot + 1)
                          if areas[j] > 0]
            area_at_anchor_bot = candidates[-1] if candidates else 0.0

        if area_at_anchor_bot < area_i * SURFACE_AREA_RATIO:
            for k in range(i, min(i + numBottom, total)):
                if areas[k] > 0:
                    surface_indices.add(k)

    flagged = len(surface_indices)
    print(f"[Surface detection] {flagged}/{total} layers flagged as top/bottom "
          f"({100.0 * flagged / total:.1f}% of all layers)  "
          f"numTop={numTop} numBottom={numBottom}")
    return surface_indices

# given a list of slices and per-print top/bottom layer counts,
# fills the topBottom list on the relevant slices with solid infill lines
def generateTopBottomLayers(slices, numBottom, numTop, topBottomSpacing=0.71,
                            pool=None, detection_height=0.5, layer_thickness=0.1,
                            numSideWalls=1):
    surface_indices = getTopBottomSurfaceIndices(
        slices, numBottom, numTop, detection_height, layer_thickness
    )

    # Enforce minimum spacing floor and convert spacing target to infill density.
    # Smaller spacing means denser top/bottom line packing.
    spacing = max(0.05, float(topBottomSpacing))
    percent = max(0.01, extrudeWidth / spacing)

    print(f"Top/Bottom spacing: {topBottomSpacing} mm  \u2192  percent={percent:.4f}")

    # Use each layer's own perimeter as the clip boundary.
    # infill() uses ray-intersection against the perimeter so fill lines are
    # always contained within the exact outline of that layer.
    tasks = []
    for i in surface_indices:
        peri = slices[i].perimeter
        if not peri:
            continue
        tasks.append((i, peri, percent, "Lines"))

    own_pool = False
    if pool is None:
        cores = max(1, multiprocessing.cpu_count() // 4)
        pool = multiprocessing.Pool(processes=cores, initializer=_init_mp,
                                    initargs=(extrudeWidth, delta, supportInfill, bedWidth, None, radialMaxSpacing))
        own_pool = True

    for i, res in pool.imap_unordered(_do_infill, tasks):
        # Guard: if every fill line spans the full Y bounding box of the
        # perimeter, the perimeter was too degenerate to clip against — the
        # even-odd logic produced bounding-box-wide segments.  Print nothing
        # rather than a solid rectangle that ignores the actual shape.
        if res:
            peri = slices[i].perimeter
            ys = [pt.y for l in peri for pt in (l.p0, l.p1)]
            bbox_h = (max(ys) - min(ys)) if ys else 0.0
            if bbox_h > 0:
                full_span = sum(1 for l in res
                                if abs(l.p1.y - l.p0.y) >= bbox_h * 0.95)
                if full_span == len(res):   # every line spans the full height
                    res = []
        slices[i].topBottom = res

    if own_pool:
        pool.close()
        pool.join()
    return slices


# given a list of slices with the list of line segments
# write the G code to the given file 
def writeGcode(slices,filename, printSpeed=900, supportSpeed=800, travelSpeed=2700, laserPower=None, progressCallback=None):

    #Gcode for unit:

    # G0 -- Rapid move (no laser)
    # G1 -- Linear move (with laser)
    #No need for a  G28 for homing
    #? - Start Swipe 


    extrudeRate = 0.05
    f = open(filename,'w')

    #preamble
    f.write(";Start GCode\n")
    f.write("M109 S210.000000\n")
    f.write("G28 X0 Y0 Z0\n")
    f.write("G92 E0\n")
    f.write("G29\n")
    if laserPower is not None:
        f.write("M3 S"+str(laserPower)+"\n")

    #o = bedWidth/2 #origin
    o = 0
    layer = 1; #current layer/slice
    E = 0; #extrusion accumulator
    for s in slices:
        if progressCallback:
            progressCallback(60 + int(layer / len(slices) * 40))

        f.write(";Layer "+str(layer)+" of "+str(len(slices))+"\n")

        #fan
        if (layer == 2):
            f.write("M106 S127\n")
        if (layer == 3):
            f.write("M106 S255\n")
        
        f.write(";perimeter\n")
        for l in s.perimeter:
            #move to start of line
            f.write("G0 F"+str(travelSpeed)+" X"+str(o+l.p0.x)+" Y"+str(o+l.p0.y)+" Z"+str(l.p0.z)+"\n")
            #move to end while extruding
            dist = math.sqrt(pow(l.p1.x-l.p0.x,2) + pow(l.p1.y-l.p0.y,2))
            E += dist*extrudeRate
            f.write("G1 F"+str(printSpeed)+" X"+str(o+l.p1.x)+" Y"+str(o+l.p1.y)+" E"+str(E)+"\n")

        if len(s.sideWalls) > 0:
            f.write(";side_walls\n")
            for l in s.sideWalls:
                f.write("G0 F"+str(travelSpeed)+" X"+str(o+l.p0.x)+" Y"+str(o+l.p0.y)+" Z"+str(l.p0.z)+"\n")
                dist = math.sqrt(pow(l.p1.x-l.p0.x,2) + pow(l.p1.y-l.p0.y,2))
                E += dist*extrudeRate
                f.write("G1 F"+str(printSpeed)+" X"+str(o+l.p1.x)+" Y"+str(o+l.p1.y)+" E"+str(E)+"\n")

        if len(s.topBottom) > 0:
            f.write(";top_bottom\n")
        for l in s.topBottom:
            f.write("G0 F"+str(travelSpeed)+" X"+str(o+l.p0.x)+" Y"+str(o+l.p0.y)+" Z"+str(l.p0.z)+"\n")
            dist = math.sqrt(pow(l.p1.x-l.p0.x,2) + pow(l.p1.y-l.p0.y,2))
            E += dist*extrudeRate
            f.write("G1 F"+str(printSpeed)+" X"+str(o+l.p1.x)+" Y"+str(o+l.p1.y)+" E"+str(E)+"\n")

        if len(s.support) > 0:
            f.write(";support\n")
        for l in s.support:
            #move to start of line
            f.write("G0 F"+str(travelSpeed)+" X"+str(o+l.p0.x)+" Y"+str(o+l.p0.y)+" Z"+str(l.p0.z)+"\n")
            #move to end while extruding
            dist = math.sqrt(pow(l.p1.x-l.p0.x,2) + pow(l.p1.y-l.p0.y,2))
            E += dist*extrudeRate
            f.write("G1 F"+str(supportSpeed)+" X"+str(o+l.p1.x)+" Y"+str(o+l.p1.y)+" E"+str(E)+"\n")

        if len(s.infill) > 0:
            f.write(";infill\n")
        for l in s.infill:
            #move to start of line
            f.write("G0 F"+str(travelSpeed)+" X"+str(o+l.p0.x)+" Y"+str(o+l.p0.y)+" Z"+str(l.p0.z)+"\n")
            #move to end while extruding
            dist = math.sqrt(pow(l.p1.x-l.p0.x,2) + pow(l.p1.y-l.p0.y,2))
            E += dist*extrudeRate
            f.write("G1 F"+str(printSpeed)+" X"+str(o+l.p1.x)+" Y"+str(o+l.p1.y)+" E"+str(E)+"\n")
        
        layer+=1

    #postamble
    f.write(";End GCode\n")
    f.write("M104 S0\n")
    f.write("M140 S0\n")
    if laserPower is not None:
        f.write("M5\n")
    f.write("G91\n")
    f.write("G1 E-1 F300\n")
    f.write("G1 Z+0.5 E-5 X-20 Y-20 F2700\n")
    f.write("G28 X0 Y0\n")
    f.write("M84\n")
    f.write("G90\n")


def sliceItem(filename, layerThickness, infillPercent, power, speed, bottomLayers=3, topLayers=3, printerProfile=None, progressCallback=None):
    global bedWidth, extrudeWidth, supportInfill, delta, radialMaxSpacing

    if printerProfile is not None:
        bedWidth = _to_float(getattr(printerProfile, "bedWidth", bedWidth), bedWidth)
        extrudeWidth = _to_float(getattr(printerProfile, "extrudeWidth", extrudeWidth), extrudeWidth)
        support_infill_percent = _to_float(getattr(printerProfile, "supportInfill", supportInfill * 100.0), supportInfill * 100.0)
        supportInfill = max(0.0, min(1.0, support_infill_percent / 100.0))
        numSideWalls = int(max(1, round(_to_float(getattr(printerProfile, "numSideWalls", 1), 1))))
        printSpeed = int(max(1, round(_to_float(getattr(printerProfile, "speed", speed), speed))))
        laserPower = _to_float(getattr(printerProfile, "power", power), power)
        infill_pattern = getattr(printerProfile, "infillPattern", "Lines")
        topBottomSpacing = _to_float(getattr(printerProfile, "topBottomSpacing", extrudeWidth), extrudeWidth)
        radialMaxSpacing = _to_float(getattr(printerProfile, "radialMaxSpacing", 5.0), 5.0)
        topBottomDetectionHeight = _to_float(getattr(printerProfile, "topBottomDetectionHeight", 0.5), 0.5)
    else:
        numSideWalls = 1
        printSpeed = int(max(1, round(_to_float(speed, 900))))
        laserPower = _to_float(power, 0)
        infill_pattern = "Lines"
        topBottomSpacing = extrudeWidth
        topBottomDetectionHeight = 0.5

    delta = max(extrudeWidth / 100.0, 1e-9)
    supportSpeed = int(max(1, round(printSpeed * 0.9)))
    travelSpeed = int(max(1, round(printSpeed * 3.0)))

    # bottomLayers / topLayers are mm thicknesses; convert to a layer count.
    numBottom = max(1, round(float(bottomLayers) / layerThickness)) if float(bottomLayers) > 0 else 0
    numTop    = max(1, round(float(topLayers)    / layerThickness)) if float(topLayers)    > 0 else 0

    print("Slicing "+filename+" with layer thickness "+str(layerThickness)+" and infill percent "+str(infillPercent))
    pool = None
    try:
        triangles = fileToTriangles(get_runtime_path('enviroment.stl'))
        supportSlices = generateSupports(triangles, layerThickness)

        bounds = findBoundaries(triangles)
        numSlices = int((bounds[1]-bounds[0])/layerThickness)
        zs = [bounds[0]+z*layerThickness for z in range(0, numSlices+1)]

        cores = max(1, multiprocessing.cpu_count() // 4)
        pool = multiprocessing.Pool(processes=cores, initializer=_init_mp,
                                    initargs=(extrudeWidth, delta, supportInfill, bedWidth, triangles, radialMaxSpacing))

        # --- Geometry slicing pass ---
        tasks = [(z, bounds[0], bounds[1], layerThickness) for z in zs]
        completed = 0
        slices_dict = {}

        for z_val, res in pool.imap_unordered(_do_separate_and_clean, tasks):
            slices_dict[z_val] = res
            completed += 1
            if progressCallback:
                progressCallback(int((completed) / len(tasks) * 60))

        slices = [slices_dict[z] for z in zs if z in slices_dict]
        # Pad with empty slices if any z-values are missing
        if len(slices) < len(zs):
            for z in zs:
                if z not in slices_dict:
                    slices.append(Slice(zValue_=z, perimeter_=[], isSurface_=False))

        slices = generateWalls(numSideWalls, slices)
        surface_indices = getTopBottomSurfaceIndices(
            slices, numBottom, numTop, topBottomDetectionHeight, layerThickness
        )
        print("Finished Creating Walls...")

        # --- Regular infill pass (reuse pool) ---
        tasks = []
        n_empty = 0
        n_surface = 0
        n_infill = 0
        for i, s in enumerate(slices):
            if i in surface_indices:
                s.infill = []
                n_surface += 1
            elif infillPercent != 0:
                peri = s.perimeter if isinstance(s.perimeter, list) else []
                if peri:
                    tasks.append((i, peri, min(1.0, max(0.0, infillPercent)), infill_pattern))
                    n_infill += 1
                else:
                    s.infill = []
                    n_empty += 1
            else:
                s.infill = []
                n_empty += 1

        total_layers = len(slices)
        print(f"[Infill pass] total={total_layers}  surface(top/bot)={n_surface}  "
              f"infill={n_infill}  empty/skipped={n_empty}  infillPercent={infillPercent:.2f}")

        completed = 0
        total_tasks = len(tasks)
        total_infill_lines = 0
        for i, res in pool.imap_unordered(_do_infill, tasks):
            slices[i].infill = res
            total_infill_lines += len(res)
            completed += 1
            if progressCallback and total_tasks > 0:
                progressCallback(60 + int((completed) / total_tasks * 30))

        print(f"Infill Complete — {total_infill_lines} total infill lines generated")

        # --- Volume calculation (mm³ → cm³) ---
        # Sum shoelace area of each perimeter cross-section × layer thickness.
        total_volume_mm3 = 0.0
        for s in slices:
            if s.perimeter:
                total_volume_mm3 += _polygon_area_mm2(s.perimeter) * layerThickness
        global last_volume_cm3
        last_volume_cm3 = total_volume_mm3 / 1000.0
        print(f"Part volume: {last_volume_cm3:.4f} cm³")

        # --- Top/bottom pass (reuse pool) ---
        generateTopBottomLayers(slices, numBottom, numTop, topBottomSpacing, pool=pool,
                                  detection_height=topBottomDetectionHeight,
                                  layer_thickness=layerThickness,
                                  numSideWalls=numSideWalls)
        print("Top/Bottom Layers Complete")
        for shape in supportSlices:
            for s in range(len(shape)):
                slices[s].support += infill(shape[s].perimeter,supportInfill)
        print("Writing Gcode to File...")
        writeGcode(
            slices,
            filename,
            printSpeed=printSpeed,
            supportSpeed=supportSpeed,
            travelSpeed=travelSpeed,
            laserPower=laserPower,
            progressCallback=progressCallback
        )
        print("Gcode writing complete")
        if progressCallback:
            progressCallback(100)
    except Exception as e:
        print("Error slicing: " + str(e))
        traceback.print_exc()
        if pool is not None:
            pool.terminate()
            pool.join()
            pool = None
        if progressCallback:
            progressCallback(100)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
            pool = None

def main():
    filename = sys.argv[1]
    layerThickness = float(sys.argv[2])
    infillPercent = float(sys.argv[3])

    sliceItem(filename, layerThickness, infillPercent)
    

if __name__ == "__main__":
    main()



