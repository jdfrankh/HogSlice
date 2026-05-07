from SlicerWrapper.SlicerManagerHelpers import Point, Line, Triangle
import math
import numpy as np
from shapely.geometry import Polygon as _ShapelyPolygon, MultiPolygon as _ShapelyMultiPolygon, GeometryCollection as _ShapelyGeomCollection


class GCODEPACKETTYPE:
    WALLS = 0,
    TOPBOTTOM = 1,

    INFILL = 2,
    SUPPORT = 3,
    TRAVEL = 4,
    OTHER = 5

class COMMANDS:
    HOMECOMMAND = "G28"

    TRAVELMOVE = "G0"
    PRINTMOVE = "G1"


#Layer maanager allows for a b


#Let a gcode packet be a segment of a designated portion of a layer
#Eg, for layer z, there will be a gcode packet for walls, infill, support, etc
#We will do the logic in here to determine the pattern
# We can then utilize Gcode stucturing to better organize the gcode and store it


class Slice:
    """Holds all geometry data for a single horizontal layer."""
    definedPackets = []
    
    
    
    def __init__(self, zValue, entities, isSurface=False, sideWallSettings ={},
                  infillSettings={}, topBottomSettings={}):
        self.definedPackets = []
        self.gcodeText = []

        self.zValue = zValue
        self.isSurface = isSurface
        self.definedPackets.append(SideWall(entities, sideWallSettings))
        self.definedPackets.append(TopBottom(entities, topBottomSettings))
        self.definedPackets.append(Infill(entities, infillSettings))
        
        self.writeOutlines()

        #TODO: Add more to the diagnostics to display infill lines, volume, fill, etc
         

    def writeOutlines(self):
        for packet in self.definedPackets:
            packet.defineSegment(self.zValue)

    def getPacketLines(self, type):
        for packet in self.definedPackets:
            if type == packet.id:
                return packet.segments
        return None 
            
    def getDiagnosticsClosedLoop(self):
        for packet in self.definedPackets:
            if packet.id == GCODEPACKETTYPE.WALLS:
                return packet.diagnostics['closed_loops']
    
    def getDiagnosticsOpenChain(self):
        for packet in self.definedPackets:
            if packet.id == GCODEPACKETTYPE.WALLS:
                return packet.diagnostics['open_gaps']
    
    def getAllSegments(self):
        temp = []
        for packet in self.definedPackets:
                temp = temp + packet.segments 

        return temp

    def setTopBottomRegions(self, fill_region, z):
        """Post-processing hook: called by SlicerManager after cross-layer detection.
        Forwards the computed fill region to the TopBottom packet.
        """
        for packet in self.definedPackets:
            if packet.id == GCODEPACKETTYPE.TOPBOTTOM:
                packet.setFillRegion(fill_region, z)
                break

    def setInfillRegion(self, infill_region, z):
        """Post-processing hook: called by SlicerManager with the solid interior
        area that remains after wall and top/bottom passes are accounted for.
        """
        for packet in self.definedPackets:
            if packet.id == GCODEPACKETTYPE.INFILL:
                packet.setFillRegion(infill_region, z)
                break

    def buildGcode(self):
        """Generate G-code for every packet in this layer and concatenate into
        self.gcodeText.  Returns the list of G-code lines.
        """
        _section_names = {
            GCODEPACKETTYPE.WALLS:     'side_walls',
            GCODEPACKETTYPE.TOPBOTTOM: 'top_bottom',
            GCODEPACKETTYPE.INFILL:    'infill',
            GCODEPACKETTYPE.SUPPORT:   'support',
        }
        self.gcodeText = [f";layer_z {self.zValue:.4f}"]
        for packet in self.definedPackets:
            if not packet.segments:
                continue
            packet.writeGcodeFromSegment()
            if packet.gcodeText:
                section = _section_names.get(packet.id, 'other')
                self.gcodeText.append(f";{section}")
                self.gcodeText.extend(packet.gcodeText)
                self.gcodeText.append(f";end_{section}")
        return self.gcodeText

    def delete(self):
        self.zValue = None
        self.isSurface = None
        
        for packet in self.definedPackets:
            packet.delete()
        
        self.definedPackets = []


class GcodePacket():

    id = None
    perimeter = None
    segments = []
    diagnostics = {'closed_loops': [], 'open_gaps': []}
    params = {} 


    gcodeText = [] # Contain an array of strings that represent the gcode commands for this packets

    #params is a dictionary of all relevant commands. It will be different for
    #eah gcodepacket type 

    def __init__(self,layerRaw, params=None):
        
        self.segments = []
        self.diagnostics = {'closed_loops': [], 'open_gaps': []}
        self.gcodeText = []
  
        self.layerRaw = layerRaw
        self.params = params if params is not None else {}

        if id == None:
            self.id = GCODEPACKETTYPE.OTHER

    def defineSegment(self, z):
        pass

    def writeGcodeFromSegment(self):
        """Convert self.segments into G-code lines and store in self.gcodeText.

        Travel moves (G0, laser off) are emitted whenever the start of a segment
        does not coincide with the end of the previous one.  Print moves (G1)
        carry the configured laser power via the S parameter.
        """
        self.gcodeText = []
        if not self.segments:
            return

        p            = self.params or {}
        speed        = int(p.get('printSpeed', p.get('speed', 900)))
        power        = float(p.get('laserPower', p.get('power', 0.0)))
        travel_speed = max(speed * 3, 2700)

        prev_end = None
        for seg in self.segments:
            sx = round(float(seg.p0.x), 3)
            sy = round(float(seg.p0.y), 3)
            ex = round(float(seg.p1.x), 3)
            ey = round(float(seg.p1.y), 3)

            # Travel to segment start only when position has changed
            if prev_end is None or abs(prev_end[0] - sx) > 1e-3 or abs(prev_end[1] - sy) > 1e-3:
                self.gcodeText.append(f"G0 X{sx:.3f} Y{sy:.3f} F{travel_speed}")

            self.gcodeText.append(f"G1 X{ex:.3f} Y{ey:.3f} F{speed} S{power:.4f}")
            prev_end = (ex, ey)

    def getId(self):
        return self.id
    
    def delete(self):
        self.layerRaw = None
        self.params = None
        self.id = None
        self.segments = []
        
    


    

class SideWall(GcodePacket):
    
    INTERNAL = False
    EXTERNAL = True


    def __init__(self, layerRaw, params={}):
        self.id = GCODEPACKETTYPE.WALLS
        super().__init__(layerRaw,params)

    def delete(self):
        self.diagnostics = {}
        self.segments = []
        super().delete()

    def writeGcodeFromSegment(self):
        pass
        
    def defineSegment(self, z, ):
        closed_loops_info = []
        loop_label_idx    = 0   # only increments for substantial loops worth labelling

        # polygons_closed only yields geometrically closed rings — open-chain
        # artifacts from degenerate triangles are excluded automatically.
        for poly in self.layerRaw.polygons_closed:
            if poly is None or poly.exterior is None:
                continue
            coords = np.array(poly.exterior.coords)[:-1]  # Nx2, drop duplicate closing vertex
            n = len(coords)
            if n < 3:
                continue

            loop_segs = []
            for i in range(n):
                nxt = (i + 1) % n
                loop_segs.append(Line(
                    Point(float(coords[i][0]),   float(coords[i][1]),   z),
                    Point(float(coords[nxt][0]), float(coords[nxt][1]), z),
                ))
            # Raw edges stored only for diagnostics; wall segments come from _buildWallOffsets

            xs, ys = coords[:, 0], coords[:, 1]
            bbox_area = (float(xs.max()) - float(xs.min())) * (float(ys.max()) - float(ys.min()))
            if bbox_area < 0.2:   # mm² — ignore sub-0.5 mm² fragments
                continue
            loop_label_idx += 1
            min_x, max_x = float(xs.min()), float(xs.max())
            min_y, max_y = float(ys.min()), float(ys.max())
            closed_loops_info.append({
                'cx':    (min_x + max_x) * 0.5,
                'cy':    (min_y + max_y) * 0.5,
                'min_x': min_x, 'max_x': max_x,
                'min_y': min_y, 'max_y': max_y,
                'index': loop_label_idx,
                'internalOrExternal': self.EXTERNAL,
                'segs': loop_segs,
                'poly': poly,  # already a shapely Polygon — reuse for containment tests
            })

        # Classify loops after all are collected.
        # Use shapely Polygon.contains() for geometrically exact containment.
        # A loop is contained by another if its polygon is fully inside the other.
        # Odd containment count → INTERNAL, even → EXTERNAL.
        for selectedLoop in closed_loops_info:
            contain_count = sum(
                1 for otherLoop in closed_loops_info
                if otherLoop['index'] != selectedLoop['index']
                and otherLoop['poly'].contains(selectedLoop['poly'])
            )
            selectedLoop['contain_count'] = contain_count
            selectedLoop['internalOrExternal'] = self.INTERNAL if contain_count % 2 == 1 else self.EXTERNAL
        
        #print("Saving Diagnostics")
        self.diagnostics['closed_loops'] = closed_loops_info
        self.diagnostics['open_gaps'] = []
        self._buildWallOffsets(closed_loops_info, z)
        #print(f"Finished {self.id}: [layer {z + 1}] z={z:.3f}  loops={len(closed_loops_info)}  segs={len(self.segments)}")

    def _buildWallOffsets(self, closed_loops_info, z):
        """Generate numSideWalls inset/outset passes for each classified loop.

        External loops are inset inward (negative buffer) so additional passes
        move toward the part interior.
        Internal loops (holes) are offset outward into the solid material
        (positive buffer expands the hole polygon toward the solid).
        Any offset ring that overlaps another loop's base polygon is clipped.
        """
        extrude_w = float(self.params.get('extruderWidth', 0.71))
        num_walls = int(self.params.get('numSideWalls', 1))
        if num_walls < 1:
            return

        all_base_polys = [loop['poly'] for loop in closed_loops_info]

        def _poly_to_segs(geom):
            """Yield Line objects for all rings in a shapely Polygon/MultiPolygon."""
            polys = []
            if isinstance(geom, _ShapelyPolygon):
                polys = [geom]
            elif isinstance(geom, (_ShapelyMultiPolygon, _ShapelyGeomCollection)):
                polys = [g for g in geom.geoms if isinstance(g, _ShapelyPolygon) and not g.is_empty]
            for poly in polys:
                for ring in [poly.exterior] + list(poly.interiors):
                    coords = list(ring.coords)
                    for k in range(len(coords) - 1):
                        yield Line(
                            Point(float(coords[k][0]),   float(coords[k][1]),   z),
                            Point(float(coords[k+1][0]), float(coords[k+1][1]), z),
                        )

        for loop in closed_loops_info:
            is_external = loop['internalOrExternal'] == self.EXTERNAL
            base_poly   = loop['poly']

            for wall_i in range(0, num_walls):   # wall_i=0 = the polygon outline itself
                if wall_i == 0:
                    # First pass: trace the polygon boundary directly (exterior + interior holes)
                    self.segments.extend(_poly_to_segs(base_poly))
                    continue
                dist = extrude_w * wall_i
                # External: shrink inward; Internal: expand outward into solid
                offset_dist = -dist if is_external else dist
                try:
                    offset_geom = base_poly.buffer(offset_dist, join_style=2, mitre_limit=5.0)
                except Exception:
                    break
                if offset_geom is None or offset_geom.is_empty:
                    break  # further walls will also be empty

                # Clip to prevent overlap with sibling/child loops.
                # Never difference against a loop that CONTAINS us — that erases the ring.
                # (e.g. don't clip D-hole's inset against the D-letter that wraps it)
                for other_loop in closed_loops_info:
                    if other_loop['index'] == loop['index']:
                        continue
                    if other_loop['poly'].contains(loop['poly']):
                        continue  # parent — skip
                    try:
                        offset_geom = offset_geom.difference(other_loop['poly'])
                    except Exception:
                        pass
                    if offset_geom.is_empty:
                        break

                if offset_geom.is_empty:
                    continue

                self.segments.extend(_poly_to_segs(offset_geom))



class TopBottom(GcodePacket):

    def __init__(self, layerRaw, params=None):
        self.id = GCODEPACKETTYPE.TOPBOTTOM
        super().__init__(layerRaw, params)

    def setFillRegion(self, fill_region, z):
        """Populate self.segments with scan-line fill clipped to fill_region.
        fill_region : shapely Polygon / MultiPolygon — top+bottom surface area
        z           : layer Z height for Line object construction
        """
        spacing = float((self.params or {}).get('topBottomSpacing', 0.71))
        self.segments.extend(self._fill_polygon(fill_region, z, spacing))

    def _fill_polygon(self, region, z, spacing):
        """Return a list of Line segments covering region with horizontal scan lines."""
        from shapely.geometry import LineString
        segs = []
        if region is None or region.is_empty:
            return segs
        minx, miny, maxx, maxy = region.bounds
        y = miny + spacing * 0.5
        while y <= maxy + 1e-9:
            scan = LineString([(minx - 1.0, y), (maxx + 1.0, y)])
            try:
                clipped = region.intersection(scan)
            except Exception:
                y += spacing
                continue
            if clipped.is_empty:
                y += spacing
                continue
            if clipped.geom_type == 'LineString':
                line_list = [clipped]
            elif clipped.geom_type == 'MultiLineString':
                line_list = list(clipped.geoms)
            elif clipped.geom_type == 'GeometryCollection':
                line_list = [g for g in clipped.geoms
                             if g.geom_type in ('LineString', 'MultiLineString') and not g.is_empty]
            else:
                line_list = []
            for line in line_list:
                sub_lines = list(line.geoms) if line.geom_type == 'MultiLineString' else [line]
                for sub in sub_lines:
                    coords = list(sub.coords)
                    for k in range(len(coords) - 1):
                        segs.append(Line(
                            Point(float(coords[k][0]),   float(coords[k][1]),   z),
                            Point(float(coords[k+1][0]), float(coords[k+1][1]), z),
                        ))
            y += spacing
        return segs


class Infill(GcodePacket):
    """Infill paths for the solid interior of a layer.

    Supported patterns (infillPattern param, case-insensitive):
      Lines     — parallel horizontal lines
      Grid      — horizontal + vertical lines
      Triangles — three directions at 0 °, 60 °, 120 °
      Honeycomb — regular hexagonal grid (pointy-top)

    Line spacing is derived from infillPercent (0.0 – 1.0 fraction):
      spacing = extruderWidth / density
    where density satisfies: infill_area * density = extruderWidth * sum(line_lengths)
    At density=1.0 → spacing = extruderWidth (fully solid).
    At density=0.2 → spacing = 5 × extruderWidth.
    """

    def __init__(self, layerRaw, params=None):
        self.id = GCODEPACKETTYPE.INFILL
        super().__init__(layerRaw, params)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setFillRegion(self, fill_region, z):
        """Generate infill segments clipped to fill_region at height z."""
        if fill_region is None or fill_region.is_empty:
            return
        p = self.params or {}
        extrude_w = max(float(p.get('extruderWidth', 0.71)), 1e-6)
        # infillPercent is stored as a 0.0–1.0 fraction (e.g. 0.8 for 80 %)
        raw = float(p.get('infillPercent', 0.20))
        # Accept both fraction (≤1) and legacy percentage (>1) forms
        density = max(1e-6, raw / 100.0 if raw > 1.0 else raw)
        pattern = str(p.get('infillPattern', 'Lines')).strip().lower()
        # spacing derived directly from the user formula:
        #   infill_area * density = extruderWidth * sum(line_lengths)
        #   => spacing = extruderWidth / density
        spacing = extrude_w / density
        if pattern == 'grid':
            self.segments += self._scan_lines(fill_region, z, spacing, 0.0)
            self.segments += self._scan_lines(fill_region, z, spacing, 90.0)
        elif pattern == 'triangles':
            for angle in (0.0, 60.0, 120.0):
                self.segments += self._scan_lines(fill_region, z, spacing, angle)
        elif pattern == 'honeycomb':
            self.segments += self._honeycomb(fill_region, z, spacing)
        else:  # 'lines' (default)
            self.segments += self._scan_lines(fill_region, z, spacing, 0.0)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_lines(geom):
        """Yield individual LineString objects from any shapely geometry."""
        if geom is None or geom.is_empty:
            return
        t = geom.geom_type
        if t == 'LineString':
            yield geom
        elif t == 'MultiLineString':
            yield from geom.geoms
        elif t == 'GeometryCollection':
            for g in geom.geoms:
                if g.geom_type == 'LineString':
                    yield g
                elif g.geom_type == 'MultiLineString':
                    yield from g.geoms

    def _scan_lines(self, region, z, spacing, angle_deg):
        """Horizontal scan-line fill after rotating region by -angle_deg.
        Segment endpoints are rotated back to world coordinates.
        """
        from shapely.geometry import LineString
        from shapely.affinity import rotate as _rotate
        segs = []
        cx, cy = region.centroid.x, region.centroid.y
        rot = _rotate(region, -angle_deg, origin=(cx, cy)) if angle_deg != 0.0 else region
        minx, miny, maxx, maxy = rot.bounds
        cos_a = math.cos(math.radians(angle_deg))
        sin_a = math.sin(math.radians(angle_deg))

        def _back(px, py):
            dx, dy = px - cx, py - cy
            return cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a

        y = miny + spacing * 0.5
        while y <= maxy + 1e-9:
            scan = LineString([(minx - 1.0, y), (maxx + 1.0, y)])
            try:
                clipped = rot.intersection(scan)
            except Exception:
                y += spacing
                continue
            for line in self._iter_lines(clipped):
                coords = list(line.coords)
                for k in range(len(coords) - 1):
                    if angle_deg != 0.0:
                        x0, y0 = _back(float(coords[k][0]),   float(coords[k][1]))
                        x1, y1 = _back(float(coords[k+1][0]), float(coords[k+1][1]))
                    else:
                        x0, y0 = float(coords[k][0]),   float(coords[k][1])
                        x1, y1 = float(coords[k+1][0]), float(coords[k+1][1])
                    segs.append(Line(Point(x0, y0, z), Point(x1, y1, z)))
            y += spacing
        return segs

    def _honeycomb(self, region, z, spacing):
        """Regular hexagonal honeycomb (pointy-top hexagons).
        spacing is used as the hexagon circumradius (= side length).
        All 6 edges of every hex cell are drawn; shared interior edges
        are intentionally printed twice for stronger walls.
        """
        from shapely.geometry import LineString
        segs = []
        r = max(spacing, 1e-6)
        col_w = math.sqrt(3) * r   # horizontal distance between column centres
        minx, miny, maxx, maxy = region.bounds
        pad = r * 3

        def _add(p0, p1):
            seg = LineString([p0, p1])
            try:
                cl = region.intersection(seg)
            except Exception:
                return
            for line in self._iter_lines(cl):
                coords = list(line.coords)
                for k in range(len(coords) - 1):
                    segs.append(Line(
                        Point(float(coords[k][0]),   float(coords[k][1]),   z),
                        Point(float(coords[k+1][0]), float(coords[k+1][1]), z),
                    ))

        col = 0
        x = minx - pad
        while x <= maxx + pad:
            # Odd columns offset upward by r so hexagons interlock
            phase = r if (col % 2) else 0.0
            y = miny - pad + phase
            while y <= maxy + pad:
                # Pointy-top: vertex 0 at top (90 °), counterclockwise
                verts = [
                    (x + r * math.cos(math.radians(90 + i * 60)),
                     y + r * math.sin(math.radians(90 + i * 60)))
                    for i in range(6)
                ]
                for i in range(6):
                    _add(verts[i], verts[(i + 1) % 6])
                y += 2 * r
            x += col_w
            col += 1
        return segs
