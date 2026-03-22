    
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
        self.leftOverlay.addButton("SetFlat", lambda: self.setMoveType("SetFlat"))

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
            self.ActorManager.removeActor(onlyPicked = True)

    def parseActor(self, fileName):
        self.ActorManager.insertActor(fileName)


    def printActors(self):

        return self.ActorManager.printActors()
    
    

    def onLeftButtonPress(self, obj, event):
        print("Left Button Pressed----------------------------------")
        click_pos = self.events.getEventPosition()
        
        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()

        

        displayOverlay = self.ActorManager.selectActor(click_pos,self.selectedMoveType, shift_pressed)

        if self.leftOverlay.determineIfOverlayPressed(click_pos):
            #Do function assigned to left overlay
            return

        if(displayOverlay and not self.leftOverlay.overlayEnabled):
            self.leftOverlay.createOverlayActor()
        elif (not displayOverlay and self.leftOverlay.overlayEnabled):
            self.leftOverlay.destroyOverlay()

        self.vtkWidget.GetRenderWindow().Render()
        
        #self.events.toggleCamera(True)

    def onMouseMove(self, obj, event):

        self.ActorManager.moveSelectedActors()

    def onLeftButtonRelease(self, obj, event):
        print("Left Button Releasaed-------------------------------------------")
        self.events.toggleCamera(False)

        self.ActorManager.finishActions()
   
        self.gizmoSelectedAxis = None
        self.gizmoStartPosition = None
        self.gizmoActiveActors = []

    def _qtMouseReleaseEvent(self, event):
        # Ensure release handling even if VTK doesn't emit the event
        self.onLeftButtonRelease(self.events.iren, "LeftButtonReleaseEvent")
        #if self._originalMouseReleaseEvent:
        #    self._originalMouseReleaseEvent(event)


    
   

    