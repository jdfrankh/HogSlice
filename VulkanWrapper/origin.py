import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType




class Origin(Actor):

    def __init__(self, vtkWidget, colors, renderer, events, picker):
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(25.4, 25.4, 25.4)
        axes.SetShaftTypeToLine()
        axes.SetAxisLabels(0)
        axes.SetPickable(False)

        super().__init__("Origin", axes, ActorType.ORIGIN, vtkWidget, colors, renderer, events, picker)
