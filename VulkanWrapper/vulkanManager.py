    
import vtk
from PyQt5.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .vulkanActor import Actor, ActorType
from .eventManager import EventManager
import math

class VulkanManager:
    
    vtkWidget = None
    colors = None
    renderer = None
    #iren = None
    events = None
    picked_actor = None
    pickedActorLists = []

    Actors = []

    BuildChamberActors = []

    GizmoActors = []
    
    # Gizmo dragging variables
    gizmoSelectedAxis = None  # 'X', 'Y', or 'Z'
    gizmoStartPosition = None  # Initial mouse position
    gizmoActiveActors = []  # Actors to move with gizmo

    picker = vtk.vtkPropPicker()

    def __init__(self, printerBed = []):
        self.vtkWidget = QVTKRenderWindowInteractor(None)
        self.colors = vtk.vtkNamedColors()
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.renderer)
        #self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Ensure the VTK widget can receive mouse release events
        self.vtkWidget.setFocusPolicy(Qt.ClickFocus)
        self.vtkWidget.setFocus()

        self.events = EventManager(self.vtkWidget, self)

        self.events.AddObserver("LeftButtonPressEvent", self.onLeftButtonPress)
        self.events.AddObserver("MouseMoveEvent", self.onMouseMove)
        self.events.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonRelease)

        self.events.printEnabledEvents()
        # Gradient background (dark → lighter)
        self.renderer.GradientBackgroundOn()
        self.renderer.SetBackground(0.1, 0.1, 0.1)      # bottom color
        self.renderer.SetBackground2(0.3, 0.3, 0.3)     # top color

        #self.iren.SetInteractorStyle(vtkInteractorStyleMultiTouchCamera())

        #Enable VTK observers
        #self.iren.AddObserver("LeftButtonPressEvent", self.onLeftButtonPress)
        #self.iren.AddObserver("BackspacePressEvent", self.deleteItem)
        #self.iren.AddObserver("MouseMoveEvent", self.onMouseMove)
        #self.iren.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonRelease)
        

        

        # Install an event filter on the VTK widget to intercept key presses
        # when it has focus.
        #self.vtkWidget.installEventFilter(None)

        self.vtkWidget.Initialize()
        self.vtkWidget.Start()

        # Qt fallback for mouse release events
        self._originalMouseReleaseEvent = self.vtkWidget.mouseReleaseEvent
        self.vtkWidget.mouseReleaseEvent = self._qtMouseReleaseEvent

        
        self.set_isometric_view()

        #actor = Actor.make_rectangle(2, 2, .25)
        
        #self.renderer.AddActor(actor)

        self.contructNewPrinter(printerBed)

        

    def contructNewPrinter(self, printerBed = []):

        for i in range(len(self.BuildChamberActors)):
            self.renderer.removeActor(self.BuildChamberActors[i])
        

        actor = Actor.make_hollow_box_no_top(printerBed[0], printerBed[1], printerBed[2], wall_thickness=.005, unit="in")

        self.BuildChamberActors.append(actor)

        #self.renderer.AddActor(actor)
        axes = self.display_origin(printerBed[0] * .5)

        self.BuildChamberActors.append(axes)

        #self.vtkWidget.GetRenderWindow().Render()

        for i in range(len(self.BuildChamberActors)):
            self.renderer.AddActor(self.BuildChamberActors[i])



    def reset(self):
        pass

    def display_origin(self, length=1.0, unit="in"):
        """
        Display XYZ axes at the origin using colored lines.
        X: Red, Y: Green, Z: Blue
        """
        if unit == "in":
            length *= 25.4
        # Remove previous origin axes if needed (optional, not implemented here)
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(length, length, length)
        axes.SetShaftTypeToLine()
        axes.SetAxisLabels(0)

        return axes
        
        #self.BuildChamberActors.append(actor)
        
        #self.renderer.AddActor(axes)
        
        #self.vtkWidget.GetRenderWindow().Render()

    def set_isometric_view(self):
        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(200, 200, 150)  # Isometric direction
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 0, 1)

        self.renderer.ResetCamera()
        self.vtkWidget.GetRenderWindow().Render()

    def removeActor(self, actor):
        self.renderer.removeActor(actor)

        for i in range(len(self.Actors)):
            if(self.Actors[i].getActor() == actors ):
                self.Actors[i].remove()

    def insertActor(self, fileName): # Insert a new

        reader = vtk.vtkSTLReader()
        reader.SetFileName(fileName)
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        #self.actor.RotateZ(90)
        #self.actor.SetPosition(20, 10, 0)
        actor.GetProperty().SetColor(self.colors.GetColor3d("LightSteelBlue"))
        #actor.GetProperty().SetDiffuse(0.8)
        #actor.GetProperty().SetSpecular(0.3)
        #actor.GetProperty().SetSpecularPower(60.0)

        self.Actors.append(Actor(fileName, actor, ActorType.STL))
        self.renderer.AddActor(actor)
        #self.renderer.ResetCamera()
        self.centerObject(actor)

    
    def centerObject(self, actor, target_center=(0, 0, 0)):
        """
        Move the given actor so its geometric center matches target_center (default: cylinder center).
        Args:
            actor: vtkActor to move
            renderer: vtkRenderer (for world coordinates)
            target_center: tuple (x, y, z) for desired center
        """
        # Get bounds of the actor
        bounds = actor.GetBounds()
        # Compute current center
        current_center = [
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0 
        ]
        # Compute translation vector
        translation = [target_center[i] - current_center[i] for i in range(3)]
        # Apply translation
        actor.SetPosition(*translation)



    def onLeftButtonPress(self, obj, event):
        #print("Left Button Pressed")
        click_pos = self.events.getEventPosition()
        self.events.toggleCamera()

        # Remove the build chamber to prevent it from interfering with picking
        for i in range(len(self.BuildChamberActors)):
            self.renderer.RemoveActor(self.BuildChamberActors[i])

        # Select the item
        self.picker.Pick(click_pos[0], click_pos[1], 0, self.renderer)

        #Add back the build chamber
        for i in range(len(self.BuildChamberActors)):
            self.renderer.AddActor(self.BuildChamberActors[i])

        # Use GetProp() instead of GetActor() to pick vtkAxesActor and other vtkProp objects
        self.picked_actor = self.picker.GetProp3D()

        #Is an actor found an actor or a gizmo?
        # Check if the selected item is an axes actor or STL actor
 
        # Is an STL Object
        if isinstance(self.picked_actor, vtk.vtkActor):
            print("STL Actor picked at position:", click_pos)
            self.selectActor(self.picked_actor)

        elif isinstance(self.picked_actor, vtk.vtkAxesActor):
            print("Gizmo Actor picked at position:", click_pos)
            self.selectGizmo(self.pickedActorLists)

        else: 
            
            
            print("No actor picked at position:", click_pos)
            self.removeSelections()


    def onMouseMove(self, obj, event):
        if not self.gizmoSelectedAxis or not self.gizmoStartPosition or not self.gizmoActiveActors:
            return

        current_pos = self.events.getEventPosition()
        dx = current_pos[0] - self.gizmoStartPosition[0]
        dy = current_pos[1] - self.gizmoStartPosition[1]

        camera = self.renderer.GetActiveCamera()
        scale = max(camera.GetDistance(), 1.0) * 0.001

        if self.gizmoSelectedAxis == 'X':
            delta = (dx * scale, 0.0, 0.0)
        elif self.gizmoSelectedAxis == 'Y':
            delta = (0.0, dy * scale, 0.0)
        else:
            delta = (0.0, 0.0, ((dx + dy) * 0.5) * scale)

        for actor in self.gizmoActiveActors:
            if hasattr(actor, "AddPosition"):
                actor.AddPosition(*delta)

        for actor in self.Actors:
            if actor.actorType == ActorType.GIZMO and hasattr(actor.getActor(), "AddPosition"):
                actor.getActor().AddPosition(*delta)

        self.vtkWidget.GetRenderWindow().Render()
        self.gizmoStartPosition = current_pos

    def onLeftButtonRelease(self, obj, event):
        print("Left Button Releasaed")
        self.events.toggleCamera()
        self.gizmoSelectedAxis = None
        self.gizmoStartPosition = None
        self.gizmoActiveActors = []

    def _qtMouseReleaseEvent(self, event):
        # Ensure release handling even if VTK doesn't emit the event
        self.onLeftButtonRelease(self.events.iren, "LeftButtonReleaseEvent")
        if self._originalMouseReleaseEvent:
            self._originalMouseReleaseEvent(event)


    def selectActor(self, actor):
        
        #self.picked_actor.GetProperty().SetColor(self.colors.GetColor3d("Red"))
        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()

        #Shif pressed to select multiple actors
        if shift_pressed:
            print("Shift key detected during pick. Add to list")
    
            self.pickedActorLists.append(self.picked_actor)
        
        #Single selection
        else:
            for actor in self.pickedActorLists:
                actor.GetProperty().SetColor(self.colors.GetColor3d("LightSteelBlue"))
            

            self.pickedActorLists = []
            self.pickedActorLists.append(self.picked_actor)
        
        #Now set color, as well as the gizmo placement for all selected items
        gizmoPlacement = []

        for actor in self.Actors:
            for picked in self.pickedActorLists:
                if actor.getActor() == picked:

                    print("Picked Actor ID:", actor.id)
                    print("Actor Type:", actor.actorType)
                    actor.isSelected = True
                    if(actor.actorType == ActorType.STL):
                        actor.setColor(self.colors.GetColor3d("Red"))
                        gizmoPlacement.append(actor.getActor().GetBounds())
                    elif(actor.actorType == ActorType.GIZMO):
                        # Begin dragging the gizmo, and move all selected items based on the movement of the gizmo
                        print("Gizmo Actor Selected - Begin Dragging")
                    
                else:
                    actor.isSelected = False
                    actor.setColor(self.colors.GetColor3d("LightSteelBlue"))
                    #Get the midpoints of either selected objects and place the gizmo actor there
                    #bounds = picked.GetBounds()

                    #midpoint = ((bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0, (bounds[4] + bounds[5])

        # Get middle of gizmo
        gizmoMidpoint = [0, 0, 0]
        for bounds in gizmoPlacement:
            gizmoMidpoint[0] += (bounds[0] + bounds[1]) / 2.0 # X dimension
            gizmoMidpoint[1] += (bounds[2] + bounds[3]) / 2.0 # Y dimension
            gizmoMidpoint[2] += (bounds[4] + bounds[5]) / 2.0 # Z dimension

        gizmoMidpoint[0] /= len(gizmoPlacement)
        gizmoMidpoint[1] /= len(gizmoPlacement)
        gizmoMidpoint[2] /= len(gizmoPlacement)

        # Remove previous gizmo actors
        for actor in self.Actors:
            if actor.actorType == ActorType.GIZMO:
                self.renderer.RemoveActor(actor.getActor())
                self.Actors.remove(actor)
        # Add new one 
        self.Actors.append(Actor.makeGizmo(self, gizmoMidpoint))
        # Use AddViewProp for vtkAxesActor to ensure picking works
        gizmo_actor = self.Actors[-1].getActor()
        if isinstance(gizmo_actor, vtk.vtkAxesActor):
            self.renderer.AddViewProp(gizmo_actor)
        else:
            self.renderer.AddActor(gizmo_actor)
        #Find the picked actor in the list, and show the gizmo actor in the center of the selected items


        
    
    def removeSelections(self):
        #Remove all selected actors and gizmos
        for actor in self.Actors:
            actor.isSelected = False
            actor.setColor(self.colors.GetColor3d("LightSteelBlue"))

            if actor.actorType == ActorType.GIZMO:
                self.renderer.RemoveActor(actor.getActor())
                self.Actors.remove(actor)

        self.pickedActorLists = []
   

    def selectGizmo(self, moveActorList = []):
        """
        Called when gizmo is selected. Determines which axis was picked and prepares for translation.
        """
        print("Gizmo Actor Selected - Begin Dragging")
        
        # Get the gizmo actor from the Actors list
        gizmo_actor = None
        for actor in self.Actors:
            if actor.actorType == ActorType.GIZMO:
                gizmo_actor = actor.getActor()
                break
        
        if not gizmo_actor:
            return
        
        # Get pick position and gizmo position
        click_pos = self.events.getEventPosition()
        gizmo_pos = gizmo_actor.GetPosition()

        def distance_point_to_segment(p, a, b):
            ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
            ap = [p[0] - a[0], p[1] - a[1], p[2] - a[2]]
            ab_len2 = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2]
            if ab_len2 == 0:
                return math.sqrt(ap[0] * ap[0] + ap[1] * ap[1] + ap[2] * ap[2])
            t = (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / ab_len2
            t = max(0.0, min(1.0, t))
            closest = [a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t]
            d = [p[0] - closest[0], p[1] - closest[1], p[2] - closest[2]]
            return math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])

        pick_pos_world = self.picker.GetPickPosition()
        length = gizmo_actor.GetTotalLength()[0]

        x_end = [gizmo_pos[0] + length, gizmo_pos[1], gizmo_pos[2]]
        y_end = [gizmo_pos[0], gizmo_pos[1] + length, gizmo_pos[2]]
        z_end = [gizmo_pos[0], gizmo_pos[1], gizmo_pos[2] + length]

        distances = {
            'X': distance_point_to_segment(pick_pos_world, gizmo_pos, x_end),
            'Y': distance_point_to_segment(pick_pos_world, gizmo_pos, y_end),
            'Z': distance_point_to_segment(pick_pos_world, gizmo_pos, z_end)
        }

        self.gizmoSelectedAxis = min(distances, key=distances.get)
        print(f"Selected Axis: {self.gizmoSelectedAxis}")
        
        # Store initial position and actors to move
        self.gizmoStartPosition = click_pos
        self.gizmoActiveActors = moveActorList
