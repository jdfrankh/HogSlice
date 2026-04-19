import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType
from VulkanWrapper.ActorCreator import ActorCreator
from constants import ActorConstants
import math
#Gizmos are the tools that allow the user to interact with a part within the scene.

#Goal for this class is to:
"""
1. Create and destroy gizmos within the frame

2. Set the sytyle of gizmo given an innput (Translate, Rotate, Scale)


"""

"Lets create another class that handles actor creation. Make it an instance in actor"

class Gizmo(Actor):

    
        # Gizmo dragging variables
    gizmoSelectedAxis = None  # 'X', 'Y', or 'Z'
    gizmoStartPosition = None  # Initial mouse position
    gizmoActiveActors = []  # Actors to move with gizmo

    parentActor = None
    surfaceNormals = {}
    #actor = {}

    def __init__(self,item, vtkWidget, colors, renderer, events, id, picker, moveType, printerBed=[], owner=None):


        self.parentActor = item
        self.owner = owner
        self.printerBed = printerBed
        #I need another instance here so gizmo is properly called sadly...
        self.creator = ActorCreator(vtkWidget, colors, renderer, events, picker, "in")

        actor = self.makeGizmo(moveType)
        
        super().__init__(id, actor, ActorType.GIZMO, vtkWidget, colors, renderer, events, picker)

        
    
        

    def removeActor(self):
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
       # print("Checking if clicked actor matches Gizmo actors...")
        if not isinstance(self.actor, dict):
            return False

        for a in self.actor.values():
            if a == keyActor:
       #         print("Clicked actor matches Gizmo actor:")
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
        self.removeActor()

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
            actors["X"] = self.creator.makeOrientedArrow("X", colors.GetColor3d(ActorConstants.XAxisColor))
            actors["Y"] = self.creator.makeOrientedArrow("Y", colors.GetColor3d(ActorConstants.YAxisColor))
            actors["Z"] = self.creator.makeOrientedArrow("Z", colors.GetColor3d(ActorConstants.ZAxisColor))
        elif moveType == "Rotate":
            actors["X"] = self.creator.makeRotateRing("X", colors.GetColor3d(ActorConstants.XAxisColor))
            actors["Y"] = self.creator.makeRotateRing("Y", colors.GetColor3d(ActorConstants.YAxisColor))
            actors["Z"] = self.creator.makeRotateRing("Z", colors.GetColor3d(ActorConstants.ZAxisColor))
        elif moveType == "Scale":
            actors["X"] = self.creator.makeScaleHandle("X", colors.GetColor3d(ActorConstants.XAxisColor))
            actors["Y"] = self.creator.makeScaleHandle("Y", colors.GetColor3d(ActorConstants.YAxisColor))
            actors["Z"] = self.creator.makeScaleHandle("Z", colors.GetColor3d(ActorConstants.ZAxisColor))
        elif moveType == "SetFlat":
            self.surfaceNormals = {}
            actors, self.owner.surfaceNormals = self.creator.extractFlatSurfaces(self.parentActor, ActorConstants.FlatSurfaceColor, ActorConstants.FlatSurfaceAreaFraction, ActorConstants.FlatSurfaceAngleThreshold)
            
        else:
            # Fallback to translate gizmo
            actors["X"] = self.creator.makeOrientedArrow("X", colors.GetColor3d(ActorConstants.XAxisColor))
            actors["Y"] = self.creator.makeOrientedArrow("Y", colors.GetColor3d(ActorConstants.YAxisColor))
            actors["Z"] = self.creator.makeOrientedArrow("Z", colors.GetColor3d(ActorConstants.ZAxisColor))

        if moveType != "SetFlat":
            for actor in actors.values():
                actor.SetPosition(center)
                actor.SetScale(  scale,  scale,  scale)  # dynamic scaling
                #self.renderer.AddActor(actor)


        #print(f"Created Gizmo Actors: {list(actors.keys())}, Center: {center}, Scale: {scale}")
        return actors

    
    def actorSelected(self, moveType = "Translate"): #, moveActorList = []):
        """
        Called when gizmo is selected. Determines which axis was picked and prepares for translation.
        """
       # print("Gizmo Actor Selected - Begin Dragging")
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
        #    print("No gizmo axis selected")
            return

        #print(f"Selected Axis: {self.gizmoSelectedAxis}")

        if moveType == "SetFlat":
            if self.gizmoSelectedAxis not in self.owner.surfaceNormals:
                return
            
            if self.owner is not None:
                self.owner.setFlatAction(self.gizmoSelectedAxis)
            return
        
        # Store initial position and actors to move
        self.gizmoStartPosition = click_pos
        #self.gizmoActiveActors = moveActorList

        super().actorSelected(moveType)

    def deselectAction(self):
        
        self.removeActor()
        super().deselectAction()


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
            self.owner._translateAction(self.gizmoSelectedAxis,self.gizmoStartPosition, current_pos)


            self.removeActor()
            self.actor = self.makeGizmo(self.moveType)

            self.addActor()
            
        elif self.moveType == "Rotate":
            self.owner._rotateAction(self.gizmoSelectedAxis, delta)
        elif self.moveType == "Scale":
            self.owner._scaleAction(self.gizmoSelectedAxis, delta)

        self.gizmoStartPosition = current_pos
        self.vtkWidget.GetRenderWindow().Render()


    

    


    
