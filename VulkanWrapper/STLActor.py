import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType
from VulkanWrapper.gizmo import Gizmo




class STLActor(Actor):

    gizmoActor = None

    def __init__(self,actor, vtkWidget, colors, renderer, events, id, picker ):

        #Assign a gizmo to the accosiated STL Actor


        super().__init__(  id, actor, ActorType.STL, vtkWidget, colors, renderer, events, picker)

        #Assign a gizmo to each STL Actor

        self.gizmoActor = Gizmo(actor, vtkWidget, colors, renderer, events, id + "_gizmo", picker)

        self.actorSelected()
        


    def actorSelected(self):
        
        self.isSelected = True
        
        self.actor.GetProperty().SetColor(self.selectColor)

        self.gizmoActor = Gizmo(self.actor, self.vtkWidget, self.colors, self.renderer, self.events, self.id + "_gizmo", self.picker)
        
    
        super().actorSelected()
        #self.gizmoActor.makeGizmo()

    def deselectAction(self):
        

        self.actor.GetProperty().SetColor(self.defaultColor)

        if(not self.gizmoActor.isSelected):
            self.gizmoActor.__del__()  # Remove the gizmo actor from the scene


        super().deselectAction()

    def getGizmo(self):
        return self.gizmoActor
        