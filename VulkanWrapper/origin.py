import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera, vtkInteractorStyleUser,vtkInteractorStyleMultiTouchCamera
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from VulkanWrapper.vulkanActor import Actor, ActorType




class Origin(Actor):

    def __init__(self, vtkWidget, colors, renderer, events):
        self.vtkWidget = vtkWidget
        self.renderer = renderer
        self.events = events
        self.colors = colors
        self.actorType = ActorType.GIZMO

    def makeOrigin(self, length=200, unit="mm"):
        """
        Create a VTK actor representing a 3D origin (axes) with specified length.
        Units can be 'mm' (default) or 'in' (inches).
        """
        print("Creating Origin Actor with length:", length, "and unit:", unit)
        if unit == "in":
            length *= 25.4

        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(length, length, length)

        axes.SetShaftTypeToLine()
        axes.SetAxisLabels(0)
        axes.SetPickable(False)

        actor = Actor("Origin", axes, ActorType.GIZMO)

        return actor
    

    def display_origin(self, length=1.0, unit="in"):
        """
        Display XYZ axes at the origin using colored lines.
        X: Red, Y: Green, Z: Blue
        """
        if unit == "in":
            length *= 25.4
        # Remove previous origin axes if needed (optional, not implemented here)
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(length, length, length)
        axes.SetShaftTypeToLine()
        axes.SetAxisLabels(0)

        return axes