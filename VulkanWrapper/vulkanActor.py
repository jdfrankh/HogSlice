import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera

class ActorType:
    NOTYPE = 0
    STL = 1
    BUILD_CHAMBER = 2
    GIZMO = 3
    ORIGIN = 4



class Actor:
    

    actorType = ActorType.NOTYPE #ActorType.STL
    
    actor = None
    id = ""
    isSelected = False

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
        self.actor = actor
        self.actorType = _actorType
        self.vtkWidget = vtkWidget
        self.colors = colors
        self.renderer = renderer
        self.events = events
        self.selectColor = colors.GetColor3d("Red")
        self.defaultColor =colors.GetColor3d("LightSteelBlue")
        self.picker = picker
        #print("Scanning for actor with ID:", self.id, "and type:", self.actorType)
        if(actor):
            print("Adding Actor:", self.id, "of type:", self.actorType)

            self.addActor()
            #self.renderer.AddActor(self.actor)

    def removeActor(self):
        self.renderer.RemoveActor(self.actor)

    def addActor(self):
        print("Adding Actor:", self.id, "of type:", self.actorType)
        self.renderer.AddActor(self.actor)

    def __del__(self):
        if self.actor:
            self.renderer.RemoveActor(self.actor)

    def getActor(self,):
        return self.actor

    def ifActorClicked(self, keyActor):
        if self.getActor() == keyActor:
            return True
        else:
            return False

    def setColor(self, color):
        self.actor.GetProperty().SetColor(color)
        
        
    def actorSelected(self, moveType):
        print(f"Selecting Actor {self.id}")
        self.moveType = moveType 
        self.isSelected = True
        

    def deselectAction(self):
        print(f"Deselecting Actor {self.id}")

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


    

