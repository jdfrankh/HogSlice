
import vtk
from PyQt5.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .vulkanActor import Actor, ActorType
from .BuildChamber  import BuildChamber
from .STLActor import STLActor
from .origin import Origin
from .eventManager import EventManager


from constants import BuildChamberDisplay
import math

# Actor manager should handle all rendering requests...
#color change can be imported,
#Event change is near useless I think to import
#Picker needs to be imported
class ActorManager:

    def exportAllActorsToSTL(self):
        """
        Export all non-build-chamber actors to a single STL file.
        """
        append_filter = vtk.vtkAppendPolyData()
        for actor in self.Actors:
            # Skip build chamber
            if hasattr(actor, 'actorType') and actor.actorType == ActorType.BUILD_CHAMBER:
                continue
            #Skip origin
            if hasattr(actor, 'actorType') and actor.actorType == ActorType.ORIGIN:
                continue
            
            # Get the VTK actor
            vtk_actor = actor.getActor() if hasattr(actor, 'getActor') else getattr(actor, 'actor', None)
            if vtk_actor is None:
                continue
            mapper = vtk_actor.GetMapper()
            if mapper is None:
                continue
            polydata = mapper.GetInput()
            if polydata is None:
                continue
            # Apply actor's transform to polydata
            #necessary for for import, as it takes into account user actions
            transform = vtk.vtkTransform()
            transform.SetMatrix(vtk_actor.GetMatrix())
            tf_filter = vtk.vtkTransformPolyDataFilter()
            tf_filter.SetInputData(polydata)
            tf_filter.SetTransform(transform)
            tf_filter.Update()
            append_filter.AddInputData(tf_filter.GetOutput())
        append_filter.Update()
        merged = append_filter.GetOutput()
        writer = vtk.vtkSTLWriter()
        #return writer
        writer.SetFileName('enviroment.stl')
        writer.SetInputData(merged)
        writer.Write()

    Actors = []

    printerBed = []

    moveActionFlag = False # Determine if mouse movements matter

    def __init__(self, vtkWidget, colors, renderer, events,picker, printerBed = []):
        self.vtkWidget = vtkWidget
        self.colors = colors
        self.renderer = renderer
        self.events = events
        self.Actors = []
        self.printerBed = printerBed
        self.picker = picker

    
    def prepareEnviroment(self):

        buildChamber = BuildChamber(self.vtkWidget, self.colors, self.renderer, self.events ,self.picker)
        buildChamber.constructNewPrinter(self.printerBed)
        self.Actors.append(buildChamber)
        
        if BuildChamberDisplay.displayOrigin:
            axis = Origin(self.vtkWidget, self.colors, self.renderer, self.events ,self.picker)

            self.Actors.append(axis)

    def updatePrinterBed(self, printerBed):
        if not printerBed or len(printerBed) < 3:
            return

        self.printerBed = printerBed

        # Keep existing STL actors and gizmos aligned with the active printer bed.
        for actor in self.Actors:
            if hasattr(actor, "printerBed"):
                actor.printerBed = self.printerBed
            gizmo = getattr(actor, "gizmoActor", None)
            if gizmo is not None and hasattr(gizmo, "printerBed"):
                gizmo.printerBed = self.printerBed

        # Remove existing build chamber actors from scene and actor list.
        for actor in list(self.Actors):
            if actor.actorType == ActorType.BUILD_CHAMBER:
                actor.removeActor()
                self.Actors.remove(actor)

        # Insert fresh build chamber for the new printer settings.
        buildChamber = BuildChamber(self.vtkWidget, self.colors, self.renderer, self.events, self.picker)
        buildChamber.constructNewPrinter(self.printerBed)
        self.Actors.insert(0, buildChamber)

    
    def removeActor(self, onlyPicked):

        for actor in self.Actors:
            if(actor.isSelected and onlyPicked) or not onlyPicked:
                print("Removing actor:", actor.id)
                actor.removeActor()
                self.Actors.remove(actor)

        self.renderer.GetRenderWindow().Render()    


    def insertActor(self, fileName): # Insert a new

        reader = vtk.vtkSTLReader()
        reader.SetFileName(fileName)
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        new_actor = STLActor(actor, self.vtkWidget, self.colors, self.renderer, self.events, fileName.split("/")[-1], self.picker, printerBed=self.printerBed)
        new_actor.centerObject()

        self.Actors.append(new_actor)

    

    def printActors(self, returnType = ActorType.STL):
        temp = []
        for actor in self.Actors:
            #print("Actor ID:", actor.id, "Type:", actor.actorType, "Selected:", actor.isSelected)
            if actor.actorType == returnType:
                temp.append(actor.id)
        return temp
    


    def selectActorByID(self, id, moveType, appendSelected = False):
        itemSelected = False

        for actor in self.Actors:
            if actor.id == id:

                actor.isSelected = True
                actor.actorSelected(moveType)
                itemSelected = True
            
            elif not appendSelected:
                actor.isSelected = False
                
                actor.deselectAction()

       # self.renderer.GetRenderWindow().Render()
       
        return itemSelected


    def selectActor(self, clickPos, moveType, appendSelected = False):
        possibleSelection = False 

        self.moveActionFlag = False
        

        for actor in (self.Actors):
            if actor.actorType == ActorType.BUILD_CHAMBER:
                self.renderer.RemoveActor(actor.getActor())
            

        # Select the item
        self.picker.Pick(clickPos[0], clickPos[1], 0, self.renderer)

        #Add back the build chamber
        for actor in range(len(self.Actors)):
            if(self.Actors[actor].actorType == ActorType.BUILD_CHAMBER):
                self.renderer.AddActor(self.Actors[actor].getActor())


        #Determine what was found 

        #Shif pressed to select multiple actors
        #if not appendSelected:
            #print("Shift key detected during pick. Add to list")
       #     for actor in self.Actors:
       #         if actor.isSelected:
       #             actor.isSelected = False
       #             actor.deselectAction()
                    #Get the midpoints of either selected objects and place the gizmo actor there
                    #bounds = picked.GetBounds()

                    #midpoint = ((bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0, (bounds[4] + bounds[5])
            #self.pickedActorLists.append(self.picked_actor)
        

        #Determine what actor was selected
        picked_actor = self.picker.GetProp3D()

        #print("Picked Actor:", picked_actor)
        curentActors = self.Actors

        for actor in curentActors:
            #print("Checking actor:", actor.id)
            if actor.ifActorClicked(picked_actor):
            #    print("Picked Actor ID:", actor.id)S
            #    print("Actor Type:", actor.actorType)
                #actor.isSelected = True
                actor.actorSelected(moveType)
                possibleSelection = True

            elif not appendSelected:

                actor.isSelected = False
                
                actor.deselectAction()

            # Only enable move behavior when something is actually selected.
            self.moveActionFlag = possibleSelection
                
        return possibleSelection

    

    def moveSelectedActors(self ):
        if not self.moveActionFlag:
            return False

        moved = False
        for actor in self.Actors:
            if getattr(actor, "isSelected", False):
                actor.moveAction()
                moved = True

        return moved

          
    def setActorOpacity(self, level):
        for actor in self.Actors:
            if actor.actorType != ActorType.BUILD_CHAMBER and actor.actorType != ActorType.ORIGIN:
                actor.setOpacity(level)

        self.vtkWidget.GetRenderWindow().Render()

    

    def determineIfOutOfBounds(self, actor):

        

        bounds = actor.actor.GetBounds()
        xMin, xMax, yMin, yMax, zMin, zMax = bounds

        if (xMin < 0 or xMax > self.printerBed[0] or
            yMin < 0 or yMax > self.printerBed[1] or
            zMin < 0 or zMax > self.printerBed[2]):
            return True

        return False


    def changeMoveType(self, moveType):
        for actor in self.Actors:
            if actor.isSelected:
                actor.actorSelected(moveType)

    def finishActions(self):
        self.moveActionFlag = False











    
