    
import vtk
from PyQt5.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
#from .vulkanActor import Actor, ActorType
#from .BuildChamber  import BuildChamber
from .ActorManager import ActorManager
from .eventManager import EventManager
from .leffOverlay import leftOverlay

import math

class VulkanManager:
    
    vtkWidget = None
    colors = None
    renderer = None
    #iren = None
    events = None

    selectedMoveType = "Translate"

    moveTypes = ["Translate", "Rotate", "Scale"]

    leftOverlay = None

    updatePagesRequest = None


    ActorManager = None


    picker = vtk.vtkPropPicker()

    def __init__(self, printerBed = [], updatePagesFunction = None):
        self.vtkWidget = QVTKRenderWindowInteractor(None)
        self.colors = vtk.vtkNamedColors()
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.renderer)

        self.events = EventManager(self.vtkWidget, self)

        self.ActorManager = ActorManager(self.vtkWidget, self.colors, self.renderer, self.events, self.picker, printerBed)
        #self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.updatePagesRequest = updatePagesFunction
        # Ensure the VTK widget can receive mouse release events
        self.vtkWidget.setFocusPolicy(Qt.ClickFocus)
        self.vtkWidget.setFocus()

        self.leftOverlay = leftOverlay(self.vtkWidget, self.colors, self.renderer, self.events)

        self.leftOverlay.addButton("Translate", lambda: self.setMoveType("Translate"))
        self.leftOverlay.addButton("Rotate", lambda: self.setMoveType("Rotate"))
        self.leftOverlay.addButton("Scale", lambda: self.setMoveType("Scale"))

        self.events.AddObserver("LeftButtonPressEvent", self.onLeftButtonPress)
        self.events.AddObserver("MouseMoveEvent", self.onMouseMove)
        self.events.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonRelease)
        self.events.AddObserver("KeyPressEvent", self.onKeyPress)

        self.events.printEnabledEvents()
        # Gradient background (dark → lighter)
        self.renderer.GradientBackgroundOn()
        self.renderer.SetBackground(0.1, 0.1, 0.1)      # bottom color
        self.renderer.SetBackground2(0.3, 0.3, 0.3)     # top color

        self.vtkWidget.Initialize()
        self.vtkWidget.Start()

        # Qt fallback for mouse release events
        self._originalMouseReleaseEvent = self.vtkWidget.mouseReleaseEvent
        self.vtkWidget.mouseReleaseEvent = self._qtMouseReleaseEvent

        
        self.events.set_isometric_view(self.renderer.GetActiveCamera())



        self.ActorManager.prepareEnviroment()
        
        self.vtkWidget.GetRenderWindow().Render()

        
    
    def setMoveType(self, moveType):
        self.selectedMoveType = moveType
        print("Selected Move Type:", self.selectedMoveType)

    def onKeyPress(self, obj, event):
        if self.events.iren.GetKeySym() == "BackSpace" or self.events.iren.GetKeySym() == "Delete":
            self.ActorManager.removeActors(onlyPicked = True)

    def parseActor(self, fileName):
        self.ActorManager.insertActor(fileName)


    def printActors(self):

        return self.ActorManager.printActors()
    
    

    def onLeftButtonPress(self, obj, event):
        print("Left Button Pressed")
        click_pos = self.events.getEventPosition()
        
        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()

        if self.leftOverlay.determineIfOverlayPressed(click_pos):
            #Do function assigned to left overlay
            return

        self.ActorManager.selectActor(click_pos, shift_pressed)

        self.vtkWidget.GetRenderWindow().Render()


    def onMouseMove(self, obj, event):
        pass
        """
        if not self.gizmoSelectedAxis or not self.gizmoStartPosition or not self.gizmoActiveActors:
            return

        current_pos = self.events.getEventPosition()
        dx = current_pos[0] - self.gizmoStartPosition[0]
        dy = current_pos[1] - self.gizmoStartPosition[1]

        camera = self.renderer.GetActiveCamera()
        scale = max(camera.GetDistance(), 1.0) * 0.001

        if(self.selectedMoveType == "Translate"):
            if self.gizmoSelectedAxis == 'X':
                delta = (-dx * scale, 0.0, 0.0)
            elif self.gizmoSelectedAxis == 'Y':
                delta = (0.0, -dy * scale, 0.0)
            else:
                delta = (0.0, 0.0, ((dx + dy) * 0.5) * scale)

            for actor in self.gizmoActiveActors:
                if hasattr(actor, "AddPosition"):
                    actor.AddPosition(*delta)

            for actor in self.Actors:
                if actor.actorType == ActorType.GIZMO and hasattr(actor.getActor(), "AddPosition"):
                    actor.getActor().AddPosition(*delta)
        
        if(self.selectedMoveType == "Rotate"):
            angle = (dx + dy) * 0.5 * scale * 10  # Rotation speed factor
            for actor in self.gizmoActiveActors:
                # Compute world-space center of the actor
                bounds = actor.GetBounds()
                cx = (bounds[0] + bounds[1]) / 2.0
                cy = (bounds[2] + bounds[3]) / 2.0
                cz = (bounds[4] + bounds[5]) / 2.0
                pos = actor.GetPosition()
                # Set origin to center so rotation pivots around center of mass
                actor.SetOrigin(cx - pos[0], cy - pos[1], cz - pos[2])
                if self.gizmoSelectedAxis == 'X':
                    actor.RotateX(angle)
                elif self.gizmoSelectedAxis == 'Y':
                    actor.RotateY(angle)
                else:
                    actor.RotateZ(angle)

        if(self.selectedMoveType == "Scale"):
            factor = 1.0 + (dx + dy) * 0.5 * scale  # Scaling speed factor
            for actor in self.gizmoActiveActors:
                if self.gizmoSelectedAxis == 'X':
                    actor.SetScale(factor, 1.0, 1.0)
                elif self.gizmoSelectedAxis == 'Y':
                    actor.SetScale(1.0, factor, 1.0)
                else:
                    actor.SetScale(1.0, 1.0, factor)

        self.vtkWidget.GetRenderWindow().Render()
        self.gizmoStartPosition = current_pos
    """


    def onLeftButtonRelease(self, obj, event):
        print("Left Button Releasaed")
        self.events.toggleCamera(False)
   
        self.gizmoSelectedAxis = None
        self.gizmoStartPosition = None
        self.gizmoActiveActors = []

    def _qtMouseReleaseEvent(self, event):
        # Ensure release handling even if VTK doesn't emit the event
        self.onLeftButtonRelease(self.events.iren, "LeftButtonReleaseEvent")
        #if self._originalMouseReleaseEvent:
        #    self._originalMouseReleaseEvent(event)


    
   

    