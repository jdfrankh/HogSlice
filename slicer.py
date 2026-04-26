# -*- coding: utf-8 -*-

import math
import sys
import string
import copy
import struct
import multiprocessing
import traceback

def _init_mp(_extrudeWidth, _delta, _supportInfill, _bedWidth, _triangles=None):
    global extrudeWidth, delta, supportInfill, bedWidth, global_triangles
    extrudeWidth = _extrudeWidth
    delta = _delta
    supportInfill = _supportInfill
    bedWidth = _bedWidth
    global_triangles = _triangles

def _do_separate_and_clean(args):
    s, b0, b1, layerThickness = args
    currentSegment = []
    currentSegmentSurface = False
    
    for triangle in global_triangles:
        point1 = intersectSlice(Line(p0_=triangle.p0, p1_=triangle.p1), s)
        point2 = intersectSlice(Line(p0_=triangle.p1, p1_=triangle.p2), s)
        point3 = intersectSlice(Line(p0_=triangle.p2, p1_=triangle.p0), s)

        points_ = list(set([point1, point2, point3]))
        points = []

        for point in points_:
            if point is None:
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

        if s <= (b0+layerThickness) or s >= (b1-layerThickness):
            currentSegmentSurface = True

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

    percent = min(1.0, max(0.0, float(percent)))

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

    # Keep density behavior tied to part size (with a minimum of one line).
    target_span = max(width, height)
    numLines = max(1, int(round((target_span * percent) / extrudeWidth)))

    gap = width / numLines
    infill = []

    if pattern == "Radial":
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        numLines = max(2, int(round((360 * percent) / 5))) # arbitrary density factor
        # radial lines
        for r in range(numLines):
            # Spanning line completely across the object
            angle = math.radians(r * (180 / numLines))
            length = target_span * 2
            x_start = center_x - math.cos(angle) * length
            y_start = center_y - math.sin(angle) * length
            x_end = center_x + math.cos(angle) * length
            y_end = center_y + math.sin(angle) * length
            
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
            
            # Sort by distance from the far start point to naturally pair outside-in
            inters.sort(key=lambda p: math.hypot(p.x-x_start, p.y-y_start))
            
            # Check every segment between consecutive intersections
            for i in range(1, len(inters)):
                newLine = Line(inters[i-1], inters[i])
                if math.hypot(newLine.p0.x - newLine.p1.x, newLine.p0.y - newLine.p1.y) < delta:
                    continue
                mx = (newLine.p0.x + newLine.p1.x) / 2
                my = (newLine.p0.y + newLine.p1.y) / 2
                
                # If midpoint is inside object, keep the line
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
    for x in range(numLines + 1):
        
        #start with full line

        x_pos = min_x + (x * gap)
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
    #for line in s:
        #if L is a duplicate and if every triangle containing L is on the slice, remove all L in base
    setPerimeter = copy.deepcopy(s.perimeter)
    
    i = 0
    while i < len(setPerimeter):
        j = i+1
        while j < len(setPerimeter):
            if lineEqual(setPerimeter[i],setPerimeter[j]):
                setPerimeter.remove(setPerimeter[j])
            else:
                j+=1
        i+=1


    '''    
    pathPerimeter = list()
    print("Perimetering")
    k = 0
    while setPerimeter:
        pathPerimeter.insert(0,copy.deepcopy(setPerimeter[0]))
        setPerimeter = setPerimeter[1:]
        while setPerimeter:
            print(len(pathPerimeter))
            loc = findNextPoint(pathPerimeter[k].p1, setPerimeter)
            if loc is None:
                #print(pathPerimeter[k].p1.toString())
                #for line in setPerimeter:
                #    print(line.toString())
                k+=1
                break
            if pathPerimeter[k].p1.equals(setPerimeter[loc].p0):
                pathPerimeter.insert(0,copy.deepcopy(setPerimeter[loc]))
            else:
                pathPerimeter.insert(0,copy.deepcopy(setPerimeter[loc].reverse()))
            setPerimeter.remove(setPerimeter[loc])
            k+=1
    
    for line in pathPerimeter:
        if line.p0.equals(line.p1):
            pathPerimeter.remove(line)
    finalPerimeter = [value for value in pathPerimeter if value != None]
    
    '''

    finalPerimeter = setPerimeter
    #need to order perimeter such that it is manifold
    return Slice(zValue_=s.zValue, perimeter_=finalPerimeter, isSurface_=s.isSurface)


# given a perimeter (list of line segments) on a single slice,
# offsets each segment inward by a given distance using the centroid
# returns a new list of offset line segments
def offsetPerimeter(perimeter, distance):
    if len(perimeter) == 0:
        return []

    # compute centroid of all perimeter endpoints
    cx, cy = 0.0, 0.0
    count = 0
    for line in perimeter:
        cx += line.p0.x + line.p1.x
        cy += line.p0.y + line.p1.y
        count += 2
    cx /= count
    cy /= count

    offset = []
    for line in perimeter:
        p0 = copy.deepcopy(line.p0)
        p1 = copy.deepcopy(line.p1)

        # offset p0 toward centroid
        dx0 = cx - p0.x
        dy0 = cy - p0.y
        mag0 = math.sqrt(dx0**2 + dy0**2)
        if mag0 > delta:
            p0.x += (dx0 / mag0) * distance
            p0.y += (dy0 / mag0) * distance

        # offset p1 toward centroid
        dx1 = cx - p1.x
        dy1 = cy - p1.y
        mag1 = math.sqrt(dx1**2 + dy1**2)
        if mag1 > delta:
            p1.x += (dx1 / mag1) * distance
            p1.y += (dy1 / mag1) * distance

        offset.append(Line(p0, p1))
    return offset


# given the number of walls and a list of slices,
# generates inner wall perimeters for each slice
# numSideWalls includes the original perimeter (1 = no extra walls)
# returns the slices with walls added to each slice's perimeter
def generateWalls(numSideWalls, slices):
    for s in slices:
        sideWalls = list()
        for w in range(1, numSideWalls):
            wallPerimeter = offsetPerimeter(s.perimeter, extrudeWidth * w)
            sideWalls.extend(wallPerimeter)
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


def getTopBottomSurfaceIndices(slices, numBottom, numTop):
    totalLayers = len(slices)
    numBottom = int(max(0, numBottom))
    numTop = int(max(0, numTop))
    
    surface_indices = set()
    
    def get_bbox(perimeter):
        if not perimeter: return (0,0,0,0)
        xs = [p for line in perimeter for p in (line.p0.x, line.p1.x)]
        ys = [p for line in perimeter for p in (line.p0.y, line.p1.y)]
        return (min(xs), max(xs), min(ys), max(ys))
        
    def is_significantly_different(bbox1, bbox2):
        if bbox1 == (0,0,0,0) or bbox2 == (0,0,0,0):
            return True
        tol = extrudeWidth * 1.5
        return (bbox1[0] < bbox2[0] - tol or 
                bbox1[1] > bbox2[1] + tol or 
                bbox1[2] < bbox2[2] - tol or 
                bbox1[3] > bbox2[3] + tol)
                
    for i in range(totalLayers):
        bbox = get_bbox(slices[i].perimeter)
        
        # Check if it is a bottom surface (exposed to the bottom)
        if i == 0 or is_significantly_different(bbox, get_bbox(slices[i-1].perimeter)):
            for j in range(i, min(i + numBottom, totalLayers)):
                surface_indices.add(j)
                
        # Check if it is a top surface (exposed to the top)
        if i == totalLayers - 1 or is_significantly_different(bbox, get_bbox(slices[i+1].perimeter)):
            for j in range(max(0, i - numTop + 1), i + 1):
                surface_indices.add(j)
                
    return surface_indices

# given a list of slices and per-print top/bottom layer counts,
# fills the topBottom list on the relevant slices with solid infill lines
def generateTopBottomLayers(slices, numBottom, numTop, topBottomSpacing=0.71):
    surface_indices = getTopBottomSurfaceIndices(slices, numBottom, numTop)
    
    # Calculate density percent based on extrudeWidth ratio to spacing
    percent = min(1.0, max(0.01, extrudeWidth / max(topBottomSpacing, 0.01)))
    
    cores = max(1, multiprocessing.cpu_count() // 4)
    pool = multiprocessing.Pool(processes=cores, initializer=_init_mp, initargs=(extrudeWidth, delta, supportInfill, bedWidth))
    
    tasks = [(i, slices[i].perimeter, percent, "Lines") for i in surface_indices]
    for i, res in pool.imap_unordered(_do_infill, tasks):
        slices[i].topBottom = res
        
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
    global bedWidth, extrudeWidth, supportInfill, delta

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
    else:
        numSideWalls = 1
        printSpeed = int(max(1, round(_to_float(speed, 900))))
        laserPower = _to_float(power, 0)
        infill_pattern = "Lines"
        topBottomSpacing = extrudeWidth

    delta = max(extrudeWidth / 100.0, 1e-9)
    supportSpeed = int(max(1, round(printSpeed * 0.9)))
    travelSpeed = int(max(1, round(printSpeed * 3.0)))

    print("Slicing "+filename+" with layer thickness "+str(layerThickness)+" and infill percent "+str(infillPercent))
    active_pool = None
    try:
        triangles = fileToTriangles('enviroment.stl')
        supportSlices = generateSupports(triangles, layerThickness)

        bounds = findBoundaries(triangles)
        numSlices = int((bounds[1]-bounds[0])/layerThickness)
        zs = [bounds[0]+z*layerThickness for z in range(0, numSlices+1)]
        
        cores = max(1, multiprocessing.cpu_count() // 4)
        pool = multiprocessing.Pool(processes=cores, initializer=_init_mp, initargs=(extrudeWidth, delta, supportInfill, bedWidth, triangles))
        active_pool = pool
        
        tasks = [(z, bounds[0], bounds[1], layerThickness) for z in zs]
        completed = 0
        slices_dict = {}
        
        for z_val, res in pool.imap_unordered(_do_separate_and_clean, tasks):
            slices_dict[z_val] = res
            completed += 1
            if progressCallback:
                progressCallback(int((completed) / len(tasks) * 60))
                
        pool.close()
        pool.join()
        active_pool = None
        
        slices = [slices_dict[z] for z in zs if z in slices_dict]
        # Pad with empty slices if any z-values are missing
        if len(slices) < len(zs):
            for z in zs:
                if z not in slices_dict:
                    slices.append(Slice(zValue_=z, perimeter_=[], isSurface_=False))

        slices = generateWalls(numSideWalls, slices)

        surface_indices = getTopBottomSurfaceIndices(slices, bottomLayers, topLayers)
        
        print("Finished Creating Walls...")
        
        # Start infill multiprocessing
        cores = max(1, multiprocessing.cpu_count() // 4)
        pool = multiprocessing.Pool(processes=cores, initializer=_init_mp, initargs=(extrudeWidth, delta, supportInfill, bedWidth))
        active_pool = pool
        tasks = []
        for i, s in enumerate(slices):
            if i in surface_indices:
                # Top/Bottom material is generated in s.topBottom, keep regular infill off here.
                s.infill = []
            elif infillPercent != 0:
                peri = s.perimeter if isinstance(s.perimeter, list) else []
                if peri:
                    tasks.append((i, peri, min(1.0, max(0.0, infillPercent)), infill_pattern))
                else:
                    s.infill = []
            else:
                s.infill = []

        completed = 0
        total_tasks = len(tasks)
        for i, res in pool.imap_unordered(_do_infill, tasks):
            slices[i].infill = res
            completed += 1
            if progressCallback and total_tasks > 0:
                progressCallback(60 + int((completed) / total_tasks * 30))
        
        pool.close()
        pool.join()
        active_pool = None

        print("Infill Complete")
        generateTopBottomLayers(slices, bottomLayers, topLayers, topBottomSpacing)
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
        if active_pool is not None:
            active_pool.terminate()
            active_pool.join()
        if progressCallback:
            progressCallback(100)

def main():
    filename = sys.argv[1]
    layerThickness = float(sys.argv[2])
    infillPercent = float(sys.argv[3])

    sliceItem(filename, layerThickness, infillPercent)
    

if __name__ == "__main__":
    main()



