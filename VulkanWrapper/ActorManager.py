
import vtk
from PyQt5.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .vulkanActor import Actor, ActorType
from .BuildChamber  import BuildChamber
from .STLActor import STLActor
from .eventManager import EventManager
from .leffOverlay import leftOverlay

import math


class ActorManager:

    Actors = []

    printerBed = []

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
        buildChamber.contructNewPrinter(self.printerBed)

        self.Actors.append(buildChamber)

    

   

    def removeActor(self, onlyPicked):

        for actor in self.Actors:
            if(actor.isSelected and onlyPicked) or not onlyPicked:
                print("Removing actor:", actor.id)
                self.renderer.RemoveActor(actor.getActor())



    def insertActor(self, fileName): # Insert a new

        reader = vtk.vtkSTLReader()
        reader.SetFileName(fileName)
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        #self.actor.RotateZ(90)
        #self.actor.SetPosition(20, 10, 0)
        #actor.GetProperty().SetColor(self.colors.GetColor3d("LightSteelBlue"))
        #actor.GetProperty().SetDiffuse(0.8)
        #actor.GetProperty().SetSpecular(0.3)
        #actor.GetProperty().SetSpecularPower(60.0)
        new_actor = STLActor(actor, self.vtkWidget, self.colors, self.renderer, self.events, fileName.split("/")[-1], self.picker)
        new_actor.centerObject()

        self.Actors.append(new_actor)

        #self.renderer.ResetCamera()
        

        #self.updatePagesRequest()

        #print(self.printActors())

    

    def printActors(self, returnType = ActorType.STL):
        temp = []
        for actor in self.Actors:
            print("Actor ID:", actor.id, "Type:", actor.actorType, "Selected:", actor.isSelected)
            if actor.actorType == returnType:
                temp.append(actor.id)
        return temp
    




    def selectActor(self, clickPos, appendSelected = False):
        
        #self.picked_actor.GetProperty().SetColor(self.colors.GetColor3d("Red"))
        

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
        if not appendSelected:
            #print("Shift key detected during pick. Add to list")
            for actor in self.Actors:
                if actor.isSelected:
                    actor.isSelected = False
                    actor.deselectAction()
                    #Get the midpoints of either selected objects and place the gizmo actor there
                    #bounds = picked.GetBounds()

                    #midpoint = ((bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0, (bounds[4] + bounds[5])
            #self.pickedActorLists.append(self.picked_actor)
        

        #Determine what actor was selected
        self.picked_actor = self.picker.GetProp3D()

        for actor in self.Actors:
            #print("Checking actor:", actor.id)
            if actor.getActor() == self.picked_actor:
            #    print("Picked Actor ID:", actor.id)
            #    print("Actor Type:", actor.actorType)
                #actor.isSelected = True
                actor.actorSelected()

                if(actor.getGizmo()):
                    self.Actors.append(actor.getGizmo())
















    
