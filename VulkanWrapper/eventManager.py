import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
import sys
class Events:

    id = ""
    event = None

    def __init__(self, _id, _event):
        self.id = _id
        self.event = _event 

class EventManager:

    vtkWidget = None

    iren = None

    enabledEvents = []



    def __init__(self, _vtkWidget, parent):
        self.vtkWidget = _vtkWidget
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.iren.SetInteractorStyle(vtkInteractorStyleMultiTouchCamera())

        self.vtkWidget.installEventFilter(None)
        #self.setAcceptDrops(True)

    def AddObserver(self, eventName, function):
        
        self.enabledEvents.append(Events(eventName, function))
        self.iren.AddObserver(eventName, function)
    
    def getEventPosition(self):
        return self.iren.GetEventPosition()

    def removeObserver(self, eventName):
        self.iren.removeObserver(eventName)
        for i in range(len(self.enabledEvents)):
            if(eventName == self.enabledEvents[i]):
                self.enabledEvents[i].remove()

        for i in range(len(self.enabledEvents)):
            self.iren.AddObserver(self.enabledEvents[i].id, self.enabledEvents[i].event)
    
    def disableAllObservers(self):
        for i in range(len(self.enabledEvents)):
            self.iren.RemoveObserver(self.enabledEvents[i].id)
        
    def enableAllObservers(self):
        for i in range(len(self.enabledEvents)):
            self.iren.AddObserver(self.enabledEvents[i].id, self.enabledEvents[i].event )


    def printEnabledEvents(self):
        for i in range(len(self.enabledEvents)):
            print(self.enabledEvents[i].id)

    def toggleCamera(self, mode = False):
        print("Camera toggled")
        style = self.iren.GetInteractorStyle()
        """
        if isinstance(style, vtkInteractorStyleTrackballCamera):
            self.iren.SetInteractorStyle(vtkInteractorStyleUser())
        else:
            self.iren.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        """
        if mode:
            #self.iren.SetInteractorStyle(vtkInteractorStyleUser())
            self.iren.SetInteractorStyle(vtkInteractorStyleMultiTouchCamera())
        else:
            self.iren.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
            #self.iren.SetInteractorStyle(vtkInteractorStyleMultiTouchCamera())

    def set_isometric_view(self, camera):
        #camera = self.renderer.GetActiveCamera()
        camera.SetPosition(200, 200, 150)  # Isometric direction
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 0, 1)
    
