import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera

class ActorType:
    NOTYPE = 0
    STL = 1
    BUILD_CHAMBER = 2
    GIZMO = 3



class Actor:
    

    actorType = ActorType.NOTYPE #ActorType.STL
    
    actor = None
    id = ""
    isSelected = False

    def __init__(self, _id, actor=None, _actorType = ActorType.NOTYPE):
        self.id = _id
        self.actor = actor
        self.actorType = _actorType

    def getActor(self):
        return self.actor

    def setColor(self, color):
        if(self.actorType == ActorType.STL):
            self.actor.GetProperty().SetColor(color)
        
        
    @staticmethod
    def make_rectangle(width, height, thickness=0, unit="mm"):
        """
        Create a VTK actor representing a 2D rectangle (plane) if thickness==0,
        or a 3D box if thickness > 0. Units can be 'mm' (default) or 'in' (inches).
        """
        # Convert inches to mm if needed
        if unit == "in":
            width *= 25.4
            height *= 25.4
            thickness *= 25.4
        if thickness == 0:
            # 2D rectangle (plane)
            plane = vtk.vtkPlaneSource()
            plane.SetOrigin(-width/2, -height/2, 0)
            plane.SetPoint1(width/2, -height/2, 0)
            plane.SetPoint2(-width/2, height/2, 0)
            plane.SetResolution(1, 1)
            plane.Update()
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(plane.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            return actor
        else:
            # 3D box
            box = vtk.vtkCubeSource()
            box.SetXLength(width)
            box.SetYLength(height)
            box.SetZLength(thickness)
            box.Update()
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(box.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            return actor

    @staticmethod
    def makeGizmo(coordinates = [], length=200, unit="mm"):
        """
        Create a VTK actor representing a 3D gizmo (axes) with specified length.
        Units can be 'mm' (default) or 'in' (inches).
        """
        print("Creating Gizmo Actor with length:", length, "and unit:", unit, "at coordinates:", coordinates)
        if unit == "in":
            length *= 25.4

        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(length, length, length)

        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 3:
            axes.SetPosition(coordinates[0], coordinates[1], coordinates[2])

        axes.SetShaftTypeToLine()
        axes.SetAxisLabels(0)
        axes.SetPickable(True)

        actor = Actor("Gizmo", axes, ActorType.GIZMO)

        return actor

    @staticmethod
    def make_hollow_box_no_top(width, height, depth, wall_thickness=1.0, unit="mm"):
        """
        Create a hollow box (cube) with no top face, so the interior is visible.
        The box is constructed manually with 5 sides (bottom and 4 walls), with given wall thickness.
        Units can be 'mm' (default) or 'in' (inches).
        """
        import vtk
        if unit == "in":
            width *= 25.4
            height *= 25.4
            depth *= 25.4
            wall_thickness *= 25.4
        min_dim = min(width, height, depth)
        if wall_thickness <= 0 or wall_thickness * 2 >= min_dim:
            raise ValueError("Wall thickness must be positive and less than half of the smallest dimension.")

        # Outer and inner box bounds
        x0, x1 = -width/2, width/2
        y0, y1 = -height/2, height/2
        z0, z1 = -depth/2, depth/2
        ix0, ix1 = x0 + wall_thickness, x1 - wall_thickness
        iy0, iy1 = y0 + wall_thickness, y1 - wall_thickness
        iz0, iz1 = z0 + wall_thickness, z1 - wall_thickness

        # Points for the outer box (bottom corners)
        points = vtk.vtkPoints()
        # Outer bottom
        points.InsertNextPoint(x0, y0, z0)  # 0
        points.InsertNextPoint(x1, y0, z0)  # 1
        points.InsertNextPoint(x1, y1, z0)  # 2
        points.InsertNextPoint(x0, y1, z0)  # 3
        # Outer top (for wall height)
        points.InsertNextPoint(x0, y0, z1)  # 4
        points.InsertNextPoint(x1, y0, z1)  # 5
        points.InsertNextPoint(x1, y1, z1)  # 6
        points.InsertNextPoint(x0, y1, z1)  # 7
        # Inner bottom
        points.InsertNextPoint(ix0, iy0, iz0)  # 8
        points.InsertNextPoint(ix1, iy0, iz0)  # 9
        points.InsertNextPoint(ix1, iy1, iz0)  # 10
        points.InsertNextPoint(ix0, iy1, iz0)  # 11
        # Inner top (for wall height)
        points.InsertNextPoint(ix0, iy0, iz1)  # 12
        points.InsertNextPoint(ix1, iy0, iz1)  # 13
        points.InsertNextPoint(ix1, iy1, iz1)  # 14
        points.InsertNextPoint(ix0, iy1, iz1)  # 15

        # Polygons for 5 faces (bottom, 4 sides)
        faces = vtk.vtkCellArray()
        def quad(a, b, c, d):
            q = vtk.vtkQuad()
            q.GetPointIds().SetId(0, a)
            q.GetPointIds().SetId(1, b)
            q.GetPointIds().SetId(2, c)
            q.GetPointIds().SetId(3, d)
            faces.InsertNextCell(q)

        # Bottom face (outer bottom 0-3, inner bottom 8-11)
        quad(0, 1, 2, 3)  # Outer bottom
        quad(8, 9, 10, 11)  # Inner bottom

        # Walls (each as two quads: outer and inner, plus two for thickness)
        # -Y wall
        quad(0, 1, 5, 4)  # Outer
        quad(8, 9, 13, 12)  # Inner
        quad(0, 4, 12, 8)  # Thickness
        quad(1, 5, 13, 9)  # Thickness
        # +X wall
        quad(1, 2, 6, 5)  # Outer
        quad(9, 10, 14, 13)  # Inner
        quad(1, 5, 13, 9)  # Thickness (already added)
        quad(2, 6, 14, 10)  # Thickness
        # +Y wall
        quad(2, 3, 7, 6)  # Outer
        quad(10, 11, 15, 14)  # Inner
        quad(2, 6, 14, 10)  # Thickness (already added)
        quad(3, 7, 15, 11)  # Thickness
        # -X wall
        quad(3, 0, 4, 7)  # Outer
        quad(11, 8, 12, 15)  # Inner
        quad(3, 7, 15, 11)  # Thickness (already added)
        quad(0, 4, 12, 8)  # Thickness (already added)

        # PolyData
        poly = vtk.vtkPolyData()
        poly.SetPoints(points)
        poly.SetPolys(faces)
        # Normals
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

        actor.SetPosition(0, 0, -depth/2)
        actor.GetProperty().SetOpacity(.2)
        outline_actor.SetPosition(0,0,-depth/2)

        # Combine box and outline in an assembly
        assembly = vtk.vtkAssembly()
        assembly.AddPart(actor)
        assembly.AddPart(outline_actor)
        return assembly