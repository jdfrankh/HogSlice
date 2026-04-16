import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera

from constants import BuildChamberDisplay
import math
"""
Store all actor creation tools in this class

-STL creator
-Rectangle creator
-Arrow creator for gizmo
-etc
"""

class ActorCreator:
    def __init__(self, vtkWidget, colors, renderer, events, picker, unit="mm"):
        self.vtkWidget = vtkWidget
        self.colors = colors
        self.renderer = renderer
        self.events = events
        self.picker = picker
        self.unit = unit


    def makeBuildChamber(self, width, height, depth, wallThickness= None, centerPoint=(0,0,0) ):
        """
        Create a hollow box (cube) with no top face, so the interior is visible.
        The box is constructed manually with 5 sides (bottom and 4 walls), with given wall thickness.
        Units can be 'mm' (default) or 'in' (inches).
        """

        if(wallThickness is None):
            print("No wall thickness provided, using default value from BuildChamberDisplay")
            wallThickness = BuildChamberDisplay.wallThickess


    
        if self.unit == "in":
            width *= 25.4
            height *= 25.4
            depth *= 25.4
            wallThickness *= 25.4
        min_dim = min(width, height, depth)
        if wallThickness <= 0 or wallThickness   * 2 >= min_dim:
            print(f"Invalid wall thickness: {wallThickness}. Must be positive and less than half of the smallest dimension ({min_dim}).")
            raise ValueError("Wall thickness must be positive and less than half of the smallest dimension.")

        #Do some math to create the chamber
        x0, x1 = -width/2 + centerPoint[0], width/2 + centerPoint[0]
        y0, y1 = -height/2 + centerPoint[1], height/2 + centerPoint[1]
        z0, z1 = centerPoint[2], depth + centerPoint[2]

        # Build 5 faces (no top)
        bottom = self.makeRectangle((x0, x1), (y0, y1), z0, wallThickness, axis='z')
        front  = self.makeRectangle((x0, x1), (z0, z1), y0, wallThickness, axis='y')
        back   = self.makeRectangle((x0, x1), (z0, z1), y1, wallThickness, axis='y')
        left   = self.makeRectangle((y0, y1), (z0, z1), x0, wallThickness, axis='x')
        right  = self.makeRectangle((y0, y1), (z0, z1), x1, wallThickness, axis='x')

        # Combine all faces into one polydata
        append = vtk.vtkAppendPolyData()
        for face in [bottom, front, back, left, right]:
            append.AddInputData(face)
        append.Update()
        poly = append.GetOutput()

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(poly)
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOn()
        normals.Update()
        # Mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(normals.GetOutput())
        actor = vtk.vtkActor()

        
        actor.SetMapper(mapper)
        # Set color (e.g., light blue)
        actor.GetProperty().SetColor(0.3, 0.6, 1.0)

        # Add outline for edge visibility
        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(normals.GetOutput())
        outline.Update()
        outline_mapper = vtk.vtkPolyDataMapper()
        outline_mapper.SetInputConnection(outline.GetOutputPort())
        outline_actor = vtk.vtkActor()
        outline_actor.SetMapper(outline_mapper)
        outline_actor.GetProperty().SetColor(0, 0, 0)
        outline_actor.GetProperty().SetLineWidth(2)

        actor.SetPosition(0, 0, 0)
        actor.GetProperty().SetOpacity(.2)
        outline_actor.SetPosition(0, 0, 0)

        # Combine box and outline in an assembly
        assembly = vtk.vtkAssembly()
        assembly.AddPart(actor)
        assembly.AddPart(outline_actor)
        return assembly
    

    def makeRectangle(self, span1, span2, fixed_val, thickness, axis='z'):
        """
        Create a flat rectangle with an inner cutout (for wall thickness).
        span1, span2: tuples (min, max) for the two spanning axes.
        fixed_val: the fixed coordinate value for the flat axis.
        thickness: wall thickness to inset the inner rectangle.
        axis: which axis is fixed — 'z' (XY plane), 'y' (XZ plane), 'x' (YZ plane).
        """
        a0, a1 = span1
        b0, b1 = span2
        ia0, ia1 = a0 + thickness, a1 - thickness
        ib0, ib1 = b0 + thickness, b1 - thickness

        faces = vtk.vtkCellArray()
        points = vtk.vtkPoints()

        def quad(a, b, c, d):
            q = vtk.vtkQuad()
            q.GetPointIds().SetId(0, a)
            q.GetPointIds().SetId(1, b)
            q.GetPointIds().SetId(2, c)
            q.GetPointIds().SetId(3, d)
            faces.InsertNextCell(q)

        def pt(a, b):
            if axis == 'z':
                return (a, b, fixed_val)
            elif axis == 'y':
                return (a, fixed_val, b)
            else:  # axis == 'x'
                return (fixed_val, a, b)

        # Outer rectangle
        points.InsertNextPoint(*pt(a0, b0))  # 0
        points.InsertNextPoint(*pt(a1, b0))  # 1
        points.InsertNextPoint(*pt(a1, b1))  # 2
        points.InsertNextPoint(*pt(a0, b1))  # 3

        # Inner rectangle
        points.InsertNextPoint(*pt(ia0, ib0))  # 4
        points.InsertNextPoint(*pt(ia1, ib0))  # 5
        points.InsertNextPoint(*pt(ia1, ib1))  # 6
        points.InsertNextPoint(*pt(ia0, ib1))  # 7

        quad(0, 1, 2, 3)  # Outer
        quad(4, 5, 6, 7)  # Inner

        poly = vtk.vtkPolyData()
        poly.SetPoints(points)
        poly.SetPolys(faces)

        return poly
    

    def makeOrientedArrow(self, axis, color):
        arrow_source = vtk.vtkArrowSource()

        transform = vtk.vtkTransform()
        if axis == "X":
            transform.RotateZ(-90)   # X axis
        elif axis == "Y":
            transform.RotateY(90)    # Y axis
        # Z axis needs no rotation (default)

        tf = vtk.vtkTransformPolyDataFilter()
        tf.SetTransform(transform)
        tf.SetInputConnection(arrow_source.GetOutputPort())

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tf.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetLineWidth(100)
        actor.GetProperty().SetOpacity(1.0)

        return actor
    
    def makeRotateRing(self, axis, color):
        disk = vtk.vtkDiskSource()
        disk.SetInnerRadius(0.7)
        disk.SetOuterRadius(1.0)
        disk.SetCircumferentialResolution(64)

        transform = vtk.vtkTransform()
        if axis == "X":
            transform.RotateY(-90)
        elif axis == "Y":
            transform.RotateX(90)
        # Z axis: no rotation

        tf = vtk.vtkTransformPolyDataFilter()
        tf.SetTransform(transform)
        tf.SetInputConnection(disk.GetOutputPort())

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tf.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetOpacity(1.0)

        return actor
    

    def makeScaleHandle(self, axis, color):
        # Base line along X axis from origin to 1.0
        line = vtk.vtkLineSource()
        line.SetPoint1(0.0, 0.0, 0.0)
        line.SetPoint2(1.0, 0.0, 0.0)

        # Box at the tip of the line
        cube = vtk.vtkCubeSource()
        cube.SetXLength(0.2)
        cube.SetYLength(0.2)
        cube.SetZLength(0.2)

        cube_transform = vtk.vtkTransform()
        cube_transform.Translate(1.0, 0.0, 0.0)

        cube_tf = vtk.vtkTransformPolyDataFilter()
        cube_tf.SetTransform(cube_transform)
        cube_tf.SetInputConnection(cube.GetOutputPort())

        append = vtk.vtkAppendPolyData()
        append.AddInputConnection(line.GetOutputPort())
        append.AddInputConnection(cube_tf.GetOutputPort())

        # Orient the combined geometry along the requested axis
        transform = vtk.vtkTransform()
        if axis == "X":
            transform.RotateZ(-90)
        elif axis == "Y":
            transform.RotateY(90)
        # Z axis: keep default

        tf = vtk.vtkTransformPolyDataFilter()
        tf.SetTransform(transform)
        tf.SetInputConnection(append.GetOutputPort())

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tf.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetOpacity(1.0)

        return actor
    

    def extractFlatSurfaces(self,actor, _color, min_area_fraction=0.05, angle_threshold=5.0):
        """Extract groups of coplanar faces that form large flat surfaces."""
        mapper = actor.GetMapper()
        polydata = mapper.GetInput()
        if polydata is None:
            mapper.Update()
            polydata = mapper.GetInput()
        if polydata is None or polydata.GetNumberOfCells() == 0:
            return []

        normals_filter = vtk.vtkPolyDataNormals()
        normals_filter.SetInputData(polydata)
        normals_filter.ComputeCellNormalsOn()
        normals_filter.ComputePointNormalsOff()
        normals_filter.SplittingOff()
        normals_filter.Update()

        output = normals_filter.GetOutput()
        cell_normals = output.GetCellData().GetNormals()
        if cell_normals is None:
            return []

        num_cells = output.GetNumberOfCells()
        cos_threshold = math.cos(math.radians(angle_threshold))

        cell_areas = []
        cell_normal_list = []
        total_area = 0.0

        for i in range(num_cells):
            cell = output.GetCell(i)
            pts = cell.GetPoints()
            if pts.GetNumberOfPoints() >= 3:
                p0 = pts.GetPoint(0)
                p1 = pts.GetPoint(1)
                p2 = pts.GetPoint(2)
                area = vtk.vtkTriangle.TriangleArea(p0, p1, p2)
            else:
                area = 0.0
            cell_areas.append(area)
            total_area += area
            cell_normal_list.append(cell_normals.GetTuple3(i))

        if total_area == 0:
            return []

        # Cluster cells by normal similarity
        assigned = [False] * num_cells
        groups = []

        for i in range(num_cells):
            if assigned[i]:
                continue
            ni = cell_normal_list[i]
            mag_i = (ni[0]**2 + ni[1]**2 + ni[2]**2) ** 0.5
            if mag_i < 1e-9:
                assigned[i] = True
                continue
            group_cells = [i]
            assigned[i] = True
            for j in range(i + 1, num_cells):
                if assigned[j]:
                    continue
                nj = cell_normal_list[j]
                dot = ni[0]*nj[0] + ni[1]*nj[1] + ni[2]*nj[2]
                if dot > cos_threshold:
                    group_cells.append(j)
                    assigned[j] = True
            group_area = sum(cell_areas[c] for c in group_cells)
            groups.append((ni, group_cells, group_area))

        min_area = total_area * min_area_fraction
        result = []

        actors = {}
        surfaceNormals = {}

        for normal, cell_ids, group_area in groups:
            if group_area >= min_area:
                id_list = vtk.vtkIdTypeArray()
                id_list.SetNumberOfValues(len(cell_ids))
                for idx, cid in enumerate(cell_ids):
                    id_list.SetValue(idx, cid)

                selection_node = vtk.vtkSelectionNode()
                selection_node.SetFieldType(vtk.vtkSelectionNode.CELL)
                selection_node.SetContentType(vtk.vtkSelectionNode.INDICES)
                selection_node.SetSelectionList(id_list)

                selection = vtk.vtkSelection()
                selection.AddNode(selection_node)

                extract = vtk.vtkExtractSelection()
                extract.SetInputData(0, output)
                extract.SetInputData(1, selection)
                extract.Update()

                geom = vtk.vtkGeometryFilter()
                geom.SetInputData(extract.GetOutput())
                geom.Update()

                result.append((normal, geom.GetOutput()))

                for i, (normal, surface_pd) in enumerate(result):
                    key = f"S{i}"
                    color = _color[i % len(_color)]
                    smapper = vtk.vtkPolyDataMapper()
                    smapper.SetInputData(surface_pd)
                    surface_actor = vtk.vtkActor()
                    surface_actor.SetMapper(smapper)
                    surface_actor.GetProperty().SetColor(*color)
                    surface_actor.GetProperty().SetOpacity(0.7)
                    surface_actor.SetPosition(actor.GetPosition())
                    surface_actor.SetOrientation(actor.GetOrientation())
                    surface_actor.SetScale(actor.GetScale())

                    actors[key] = surface_actor
                    surfaceNormals[key] = normal

        print(f"Extracted {len(result)} flat surfaces from actor.")
        return (actors, surfaceNormals)
    





