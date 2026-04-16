import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType


class BuildChamber(Actor):

    axes = None

    def __init__(self, vtkWidget, colors, renderer, events, picker):

        

        super().__init__("BuildChamber", None, ActorType.BUILD_CHAMBER, vtkWidget, colors, renderer, events, picker)


    def constructNewPrinter(self, printerBed = []):
        
        print(f"Making a new printer with dimensions {printerBed[0]} , {printerBed[1]}, {printerBed[2]}")

        self.actor = self.creator.makeBuildChamber(printerBed[0], printerBed[1], printerBed[2], wallThickness=.01)

  


        #self.renderer.AddActor(actor)
  



        #self.vtkWidget.GetRenderWindow().Render()

        #for i in range(len(self.BuildChamberActors)):
        #    self.renderer.AddActor(self.BuildChamberActors[i])
    