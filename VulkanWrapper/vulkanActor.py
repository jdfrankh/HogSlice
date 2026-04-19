import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera

from VulkanWrapper.ActorCreator import ActorCreator
from constants import ActorConstants 
import math
class ActorType:
    NOTYPE = 0
    STL = 1
    BUILD_CHAMBER = 2
    GIZMO = 3
    ORIGIN = 4

""" TODO: 
Move actor movement into this class to simplify it.
Currently, it takes the position of gizmo and move it accordingly. It may be better to create a command class to do it


"""

class Actor:
    

    actorType = ActorType.NOTYPE #ActorType.STL
    
    actor = None
    creator = None 
    id = ""
    isSelected = False
    uniformScale = True
    selectColor = None
    defaultColor = None

    vtkWidget = None
    renderer = None
    events = None
    colors = None
    picker = None

    moveType = None

    def __init__(self, _id, actor=None, _actorType = ActorType.NOTYPE, vtkWidget=None, colors=None, renderer=None, events=None, picker=None):
        self.id = _id
        self.creator = ActorCreator(vtkWidget, colors, renderer, events, picker, "in")
        self.actor = actor
        self.actorType = _actorType
        self.vtkWidget = vtkWidget
        self.colors = colors
        self.renderer = renderer
        self.events = events
        self.selectColor = colors.GetColor3d(ActorConstants.selectColor)
        self.outOfBoundsSelectColor = colors.GetColor3d(ActorConstants.outOfBoundsSelectColor)
        self.defaultColor =colors.GetColor3d(ActorConstants.defaultColor)
        self.picker = picker

        
        #print("Scanning for actor with ID:", self.id, "and type:", self.actorType)
        if(actor):
           # print("Adding Actor:", self.id, "of type:", self.actorType)

            self.addActor()
            #self.renderer.AddActor(self.actor)

    def removeActor(self):
        if(self.actor):
            self.renderer.RemoveActor(self.actor)

    def addActor(self):
        if(self.actor):
         #   print("Adding Actor:", self.id, "of type:", self.actorType)
            self.renderer.AddActor(self.actor)
    

    def getActor(self):
      #  print("Getting Actor:", self.id, "of type:", self.actorType)
        return self.actor

    def ifActorClicked(self, keyActor):
        if self.getActor() == keyActor:
            return True
        else:
            return False

    def setOpacity(self, level):
        if self.actor:
            self.actor.GetProperty().SetOpacity(level)

    def setColor(self, color):
        self.actor.GetProperty().SetColor(color)
        
        
    def actorSelected(self, moveType):
        #print(f"Selecting Actor {self.id}")
        self.moveType = moveType 
        self.isSelected = True
        

    def deselectAction(self):
        #print(f"Deselecting Actor {self.id}")

        self.isSelected = False
        

    def getActorCenter(self, altActor=None):
        if(altActor):
            bounds = altActor.GetBounds()
        else:
            bounds = self.actor.getActor().GetBounds()
        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0
        cz = (bounds[4] + bounds[5]) / 2.0
        return (cx, cy, cz)

    def getActorScale(self, altActor=None):
        target_actor = altActor if altActor else self.actor
        return target_actor.GetScale()
    
    
    def setOutofBounds(self, outOfBounds):
        if outOfBounds:
            self.actor.GetProperty().SetColor(self.colors.GetColor3d(ActorConstants.outOfBoundsColor))
        else:
            self.actor.GetProperty().SetColor(self.defaultColor)


    def centerObject(self, target_center=(0, 0, 0)):

        # Get bounds of the actor
        bounds = self.actor.GetBounds()
        # Compute current center
        current_center = [
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0 
        ]
        # Compute translation vector
        translation = [target_center[i] - current_center[i] for i in range(3)]
        # Apply translation
        self.actor.SetPosition(*translation)

    def moveAction(self):
        pass

    
    ######### Movement Based commands ##########


    def setFlatAction(self, selectedSurface):
        """Rotate parent actor so the selected flat surface faces down (-Z)."""

        #There must be a gizmo to control the system
        if(not self.surfaceNormals):
            print("No surface normals available for flat action")
            return

        normal = self.surfaceNormals[selectedSurface]
        parent = self.actor

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
        #if self.printerBed and len(self.printerBed) >= 3:
        #    floor_z = -(self.printerBed[2] * 25.4)
        #else:
        #    floor_z = 0.0
        floor_z = ActorConstants.FloorZ
        bounds = parent.GetBounds()
        z_min = bounds[4]
        pos = list(parent.GetPosition())
        pos[2] += floor_z - z_min
        parent.SetPosition(*pos)

        # Rebuild surface highlights with new orientation
        #Do this by removing gizmo
        if(self.gizmoActor):
            self.gizmoActor.removeActor()

        #self.actor = self.makeGizmo("SetFlat")
        #for a in self.actor.values():
        #    self.renderer.AddActor(a)

        self.vtkWidget.GetRenderWindow().Render()



    def _translateAction(self,axis,startPosition, current_display_pos):
        parent = self.actor
        pos = list(parent.GetPosition())

        world_start = self.displayToWorld(startPosition[0], startPosition[1], pos)
        world_current = self.displayToWorld(current_display_pos[0], current_display_pos[1], pos)

        if axis == 'Z':
            pos[0] += world_current[0] - world_start[0]
        elif axis == 'X':
            pos[1] += world_current[1] - world_start[1]
        elif axis   == 'Y':
            pos[2] += world_current[2] - world_start[2]

  

        parent.SetPosition(*pos)

    def _rotateAction(self,axis, delta):
        speed = 0.5
        angle = delta * speed
        parent = self.actor

        if axis == 'X':
            parent.RotateX(angle)
        elif axis == 'Y':
            parent.RotateY(angle)
        elif axis == 'Z':
            parent.RotateZ(angle)

    def _scaleAction(self,axis, delta):
        speed = 0.005
        factor = 1.0 + delta * speed
        factor = max(factor, 0.01)  # Prevent negative/zero scale
        parent = self.actor
        sx, sy, sz = parent.GetScale()

        if(self.uniformScale):
            parent.SetScale(sx* factor, sy*factor, sz*factor)
        else:

            if axis == 'X':
                parent.SetScale(sx * factor, sy, sz)
            elif axis == 'Y':
                parent.SetScale(sx, sy * factor, sz)
            elif axis == 'Z':
                parent.SetScale(sx, sy, sz * factor)

    def displayToWorld(self, display_x, display_y, ref_world_pos):
        """Convert display coordinates to world coordinates using a reference point's depth."""
        self.renderer.SetWorldPoint(ref_world_pos[0], ref_world_pos[1], ref_world_pos[2], 1.0)
        self.renderer.WorldToDisplay()
        depth = self.renderer.GetDisplayPoint()[2]

        self.renderer.SetDisplayPoint(display_x, display_y, depth)
        self.renderer.DisplayToWorld()
        wp = self.renderer.GetWorldPoint()
        if wp[3] != 0:
            return [wp[i] / wp[3] for i in range(3)]
        return list(ref_world_pos)



    

