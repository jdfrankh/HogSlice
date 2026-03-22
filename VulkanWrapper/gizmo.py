import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType

import math
#Gizmos are the tools that allow the user to interact with a part within the scene.

#Goal for this class is to:
"""
1. Create and destroy gizmos within the frame

2. Set the sytyle of gizmo given an innput (Translate, Rotate, Scale)


"""
class Gizmo(Actor):

    uniformScale = True
        # Gizmo dragging variables
    gizmoSelectedAxis = None  # 'X', 'Y', or 'Z'
    gizmoStartPosition = None  # Initial mouse position
    gizmoActiveActors = []  # Actors to move with gizmo

    parentActor = None
    surfaceNormals = {}
    #actor = {}

    def __init__(self,item, vtkWidget, colors, renderer, events, id, picker, moveType, printerBed=[]):


        self.parentActor = item
        self.printerBed = printerBed

        actor = self.makeGizmo(moveType)
        
        super().__init__(id, actor, ActorType.GIZMO, vtkWidget, colors, renderer, events, picker)

    
    def __del__(self):
        if isinstance(self.actor, dict):
            for a in self.actor.values():
                self.renderer.RemoveActor(a) 

            self.actor = None

    def addActor(self):
        if not isinstance(self.actor, dict):
            return

        for a in self.actor.values():
            self.renderer.AddActor(a)
    
    def ifActorClicked(self, keyActor):
        print("Checking if clicked actor matches Gizmo actors...")
        if not isinstance(self.actor, dict):
            return False

        for a in self.actor.values():
            if a == keyActor:
                print("Clicked actor matches Gizmo actor:")
                self.isSelected = True
                return True
            
        self.isSelected = False
        return False

    def makeGizmo(self, moveType=None, length=200, unit="mm"):
        """
        Create a VTK actor representing a 3D gizmo (axes) with specified length.
        Units can be 'mm' (default) or 'in' (inches).
        """
        
        #print(f"Scale: {scale}")
        self.__del__()

        bounds = self.parentActor.GetBounds()

        center = (
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0,
        )



        # Compute bounding box diagonal length
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diagonal = (dx**2 + dy**2 + dz**2) ** 0.5

        scale = diagonal * 0.75

        if moveType is None:
            moveType = getattr(self, "moveType", "Translate")

        actors = {}
        colors = vtk.vtkNamedColors()

        if moveType == "Translate":
            actors["X"] = self.make_oriented_arrow("X", colors.GetColor3d("Red"))
            actors["Y"] = self.make_oriented_arrow("Y", colors.GetColor3d("Green"))
            actors["Z"] = self.make_oriented_arrow("Z", colors.GetColor3d("Blue"))
        elif moveType == "Rotate":
            actors["X"] = self.make_rotate_ring("X", colors.GetColor3d("Red"))
            actors["Y"] = self.make_rotate_ring("Y", colors.GetColor3d("Green"))
            actors["Z"] = self.make_rotate_ring("Z", colors.GetColor3d("Blue"))
        elif moveType == "Scale":
            actors["X"] = self.make_scale_handle("X", colors.GetColor3d("Red"))
            actors["Y"] = self.make_scale_handle("Y", colors.GetColor3d("Green"))
            actors["Z"] = self.make_scale_handle("Z", colors.GetColor3d("Blue"))
        elif moveType == "SetFlat":
            self.surfaceNormals = {}
            surfaces = self._extract_flat_surfaces()
            highlight_colors = [
                (0.2, 0.8, 0.2),
                (0.2, 0.2, 0.8),
                (0.8, 0.8, 0.2),
                (0.8, 0.2, 0.8),
                (0.2, 0.8, 0.8),
                (0.8, 0.5, 0.2),
            ]
            for i, (normal, surface_pd) in enumerate(surfaces):
                key = f"S{i}"
                color = highlight_colors[i % len(highlight_colors)]
                smapper = vtk.vtkPolyDataMapper()
                smapper.SetInputData(surface_pd)
                surface_actor = vtk.vtkActor()
                surface_actor.SetMapper(smapper)
                surface_actor.GetProperty().SetColor(*color)
                surface_actor.GetProperty().SetOpacity(0.7)
                surface_actor.SetPosition(self.parentActor.GetPosition())
                surface_actor.SetOrientation(self.parentActor.GetOrientation())
                surface_actor.SetScale(self.parentActor.GetScale())
                actors[key] = surface_actor
                self.surfaceNormals[key] = normal
        else:
            # Fallback to translate gizmo
            actors["X"] = self.make_oriented_arrow("X", colors.GetColor3d("Red"))
            actors["Y"] = self.make_oriented_arrow("Y", colors.GetColor3d("Green"))
            actors["Z"] = self.make_oriented_arrow("Z", colors.GetColor3d("Blue"))

        if moveType != "SetFlat":
            for actor in actors.values():
                actor.SetPosition(center)
                actor.SetScale(  scale,  scale,  scale)  # dynamic scaling
                #self.renderer.AddActor(actor)


        print(f"Created Gizmo Actors: {list(actors.keys())}, Center: {center}, Scale: {scale}")
        return actors

    
    def actorSelected(self, moveType = "Translate"): #, moveActorList = []):
        """
        Called when gizmo is selected. Determines which axis was picked and prepares for translation.
        """
        print("Gizmo Actor Selected - Begin Dragging")
        self.events.toggleCamera(True)

        click_pos = self.events.getEventPosition()
        picked_actor = self.picker.GetProp3D()

        self.gizmoSelectedAxis = None
        if isinstance(self.actor, dict):
            for axis, actor in self.actor.items():
                if actor == picked_actor:
                    self.gizmoSelectedAxis = axis
                    break

        if self.gizmoSelectedAxis is None:
            print("No gizmo axis selected")
            return

        print(f"Selected Axis: {self.gizmoSelectedAxis}")

        if moveType == "SetFlat":
            self._setFlatAction()
            return
        
        # Store initial position and actors to move
        self.gizmoStartPosition = click_pos
        #self.gizmoActiveActors = moveActorList

        super().actorSelected(moveType)

    def deselectAction(self):
        
        self.__del__()
        super().deselectAction()


    def make_oriented_arrow(self, axis, color):
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

    def make_rotate_ring(self, axis, color):
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

    def make_scale_handle(self, axis, color):
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

    

    def moveAction(self):


        if not self.isSelected or not self.gizmoSelectedAxis or not self.gizmoStartPosition:
            print("ERROR: Gizmo not prepped")
            return

        #print("Moving Gizmo....")
        current_pos = self.events.getEventPosition()
        dx = current_pos[0] - self.gizmoStartPosition[0]
        dy = current_pos[1] - self.gizmoStartPosition[1]

        # Use the larger screen-space delta as the movement magnitude
        delta = dx if abs(dx) > abs(dy) else dy

        if self.moveType == "Translate":
            self._translateAction(delta)
        elif self.moveType == "Rotate":
            self._rotateAction(delta)
        elif self.moveType == "Scale":
            self._scaleAction(delta)

        self.gizmoStartPosition = current_pos
        self.vtkWidget.GetRenderWindow().Render()

    def _translateAction(self, delta):
        speed = 0.5
        offset = delta * speed
        parent = self.parentActor
        pos = list(parent.GetPosition())

        if self.gizmoSelectedAxis == 'Z':
            pos[0] -= offset
        elif self.gizmoSelectedAxis == 'X':
            pos[1] += offset
        elif self.gizmoSelectedAxis == 'Y':
            pos[2] += offset


        for oldGizmo in self.actor.values():
            self.renderer.RemoveActor(oldGizmo)    

        parent.SetPosition(*pos)
        self.actor = self.makeGizmo()



        for n in self.actor.values():

            self.renderer.AddActor(n)

    def _rotateAction(self, delta):
        speed = 0.5
        angle = delta * speed
        parent = self.parentActor

        if self.gizmoSelectedAxis == 'X':
            parent.RotateX(angle)
        elif self.gizmoSelectedAxis == 'Y':
            parent.RotateY(angle)
        elif self.gizmoSelectedAxis == 'Z':
            parent.RotateZ(angle)

    def _scaleAction(self, delta):
        speed = 0.005
        factor = 1.0 + delta * speed
        factor = max(factor, 0.01)  # Prevent negative/zero scale
        parent = self.parentActor
        sx, sy, sz = parent.GetScale()

        if(self.uniformScale):
            parent.SetScale(sx* factor, sy*factor, sz*factor)
        else:

            if self.gizmoSelectedAxis == 'X':
                parent.SetScale(sx * factor, sy, sz)
            elif self.gizmoSelectedAxis == 'Y':
                parent.SetScale(sx, sy * factor, sz)
            elif self.gizmoSelectedAxis == 'Z':
                parent.SetScale(sx, sy, sz * factor)

    def _extract_flat_surfaces(self, min_area_fraction=0.05, angle_threshold=5.0):
        """Extract groups of coplanar faces that form large flat surfaces."""
        mapper = self.parentActor.GetMapper()
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

        return result

    def _setFlatAction(self):
        """Rotate parent actor so the selected flat surface faces down (-Z)."""
        if self.gizmoSelectedAxis not in self.surfaceNormals:
            return

        normal = self.surfaceNormals[self.gizmoSelectedAxis]
        parent = self.parentActor

        # Transform model-space normal to world space via actor orientation
        matrix = parent.GetMatrix()
        transform = vtk.vtkTransform()
        transform.SetMatrix(matrix)
        world_normal = transform.TransformNormal(normal)

        mag = (world_normal[0]**2 + world_normal[1]**2 + world_normal[2]**2) ** 0.5
        if mag < 1e-9:
            return
        wn = [c / mag for c in world_normal]

        # Target: surface normal pointing straight down
        target = [0.0, 0.0, -1.0]

        dot = wn[0]*target[0] + wn[1]*target[1] + wn[2]*target[2]
        cross = [
            wn[1]*target[2] - wn[2]*target[1],
            wn[2]*target[0] - wn[0]*target[2],
            wn[0]*target[1] - wn[1]*target[0],
        ]
        cross_mag = (cross[0]**2 + cross[1]**2 + cross[2]**2) ** 0.5

        if cross_mag < 1e-9:
            if dot > 0:
                angle_deg = 0.0
            else:
                angle_deg = 180.0
            axis = [1.0, 0.0, 0.0]
        else:
            angle_deg = math.degrees(math.atan2(cross_mag, dot))
            axis = [c / cross_mag for c in cross]

        if abs(angle_deg) > 0.01:
            parent.RotateWXYZ(angle_deg, axis[0], axis[1], axis[2])

        # Reposition so bottom sits on build chamber floor
        if self.printerBed and len(self.printerBed) >= 3:
            floor_z = -(self.printerBed[2] * 25.4)
        else:
            floor_z = 0.0
        bounds = parent.GetBounds()
        z_min = bounds[4]
        pos = list(parent.GetPosition())
        pos[2] += floor_z - z_min
        parent.SetPosition(*pos)

        # Rebuild surface highlights with new orientation
        for old_actor in self.actor.values():
            self.renderer.RemoveActor(old_actor)

        self.actor = self.makeGizmo("SetFlat")
        for a in self.actor.values():
            self.renderer.AddActor(a)

        self.vtkWidget.GetRenderWindow().Render()
