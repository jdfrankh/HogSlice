import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType
from VulkanWrapper.gizmo import Gizmo




class STLActor(Actor):

    gizmoActor = None
    surfaceNormals = None


    def __init__(self,actor, vtkWidget, colors, renderer, events, id, picker, moveType = "Translate", printerBed=[]):

        #Assign a gizmo to the accosiated STL Actor

        self.printerBed = printerBed

        super().__init__(  id, actor, ActorType.STL, vtkWidget, colors, renderer, events, picker)

        #Assign a gizmo to each STL Actor

        self.gizmoActor = Gizmo(actor, vtkWidget, colors, renderer, events, id + "_gizmo", picker, moveType, printerBed=printerBed, owner=self)

        #self.actorSelected(moveType)
    
    def removeActor(self):

        self.gizmoActor.removeActor()

        super().removeActor()

    def moveAction(self):
        if(self.gizmoActor):
            self.gizmoActor.moveAction()

    def ifActorClicked(self, keyActor):

        if(self.actor == keyActor):
            self.isSelected = True
            if(self.gizmoActor):
                self.gizmoActor.isSelected = False
            return True

        gizmo = self.gizmoActor

        if(not gizmo):
            return False

        return gizmo.ifActorClicked(keyActor)


    def actorSelected(self, moveType = "Translate"):
        
        #self.isSelected = True
        
        #TODO: Add a separate actor file, in which creates flat surfaces based on the object, and set them to be as low as possible

        gizmo = self.gizmoActor

        if(gizmo): # If there is a gizmo, check if it was selected
            
            if(gizmo.isSelected):
                print("STL Gizmo Selected:", self.id)
                gizmo.actorSelected(moveType)

                return

        if(self.isSelected):
        #
            print("STL Actor Selecterd:", self.id)
        #if(not gizmo): # No gizmo actor - means move cannot be made

            self.actor.GetProperty().SetColor(self.selectColor)

            #Create a new gizmo
            if self.gizmoActor:
                self.gizmoActor.deselectAction()

            self.gizmoActor = Gizmo(self.actor, self.vtkWidget, self.colors, self.renderer, self.events, self.id + "_gizmo", self.picker, moveType, printerBed=self.printerBed, owner=self)
            


    def refactorGizmo(self, moveType):
        if(self.gizmoActor):
            self.gizmoActor.removeActor()

        self.gizmoActor = Gizmo(self.actor, self.vtkWidget, self.colors, self.renderer, self.events, self.id + "_gizmo", self.picker, moveType, printerBed=self.printerBed, owner=self)

    def deselectAction(self):
        

        self.actor.GetProperty().SetColor(self.defaultColor)

        #if(not self.gizmoActor.isSelected):
        self.gizmoActor.deselectAction()
    


        super().deselectAction()


        