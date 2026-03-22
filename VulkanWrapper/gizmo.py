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

        # Gizmo dragging variables
    gizmoSelectedAxis = None  # 'X', 'Y', or 'Z'
    gizmoStartPosition = None  # Initial mouse position
    gizmoActiveActors = []  # Actors to move with gizmo

    parentActor = None

    def __init__(self,item, vtkWidget, colors, renderer, events, id, picker):

        actor = self.makeGizmo(self.getActorCenter(item))
        self.parentActor = item

        super().__init__(id, actor, ActorType.GIZMO, vtkWidget, colors, renderer, events, picker)

    def makeGizmo(self, coordinates = [], length=200, unit="mm"):
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

        return axes


    
    def actorSelected(self): #, moveActorList = []):
        """
        Called when gizmo is selected. Determines which axis was picked and prepares for translation.
        """
        print("Gizmo Actor Selected - Begin Dragging")
        
        # Get the gizmo actor from the Actors list
   
        self.actor = self.makeGizmo(self.getActorCenter(self.parentActor))

        self.renderer.AddActor(self.actor)

        if not self.actor:
            return
        
        # Get pick position and gizmo position
        click_pos = self.events.getEventPosition()
        gizmo_pos = self.actor.GetPosition()

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
        length = self.actor.GetTotalLength()[0]

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
        #self.gizmoActiveActors = moveActorList

 

        super().actorSelected()

    def deselectAction(self):
        self.renderer.RemoveViewProp(self.actor)
        self.__del__()
        super().deselectAction()

