from VulkanWrapper.vulkanManager import VulkanManager
from VulkanWrapper.OverlayTemplate import OverlayTemplate
from VulkanWrapper.VulkanGcodeManager import VulkanGcodeManager
from VulkanWrapper.GcodeStatsOverlay import GcodeStatsOverlay


from constants import moverOverlayPositions, GcodeInformerPositions
from runtime_paths import get_runtime_path


#TODO:
# Move all instances of the vulkan manager here to better organize the code

class HogforgeVulkan(VulkanManager):
    moverOverlay = None
    gcodeStatsOverlay = None

    gcodeManager = None

    


    def __init__(self, printerBed= [], updatePagesFunction=None, getterFunctions= []):
        super().__init__(printerBed, updatePagesFunction, getterFunctions)

        self.gcodeManager = VulkanGcodeManager(self.vtkWidget, self.colors, self.renderer, self.events)
        self.moverOverlay = OverlayTemplate(self.vtkWidget, self.colors, self.renderer, self.events, displaySizeAndLocation=moverOverlayPositions.OverlayScreenLocation)
        self.moverOverlay.enablePressing = True

        self.moverOverlay.addElement("Translate", "BUTTON", moverOverlayPositions.TranslateButton[0], lambda: self.setMoveType("Translate"), pressedThreshold=moverOverlayPositions.TranslateButton[1], imagePath="assets/overlay_icons/translate.png")
        self.moverOverlay.addElement("Rotate", "BUTTON", moverOverlayPositions.RotateButton[0], lambda: self.setMoveType("Rotate"), pressedThreshold=moverOverlayPositions.RotateButton[1], imagePath="assets/overlay_icons/rotate.png")
        self.moverOverlay.addElement("Scale", "BUTTON", moverOverlayPositions.ScaleButton[0], lambda: self.setMoveType("Scale"), pressedThreshold=moverOverlayPositions.ScaleButton[1], imagePath="assets/overlay_icons/scale.png")
        self.moverOverlay.addElement("SetFlat", "BUTTON", moverOverlayPositions.SetFlatButton[0], lambda: self.setMoveType("SetFlat"), pressedThreshold=moverOverlayPositions.SetFlatButton[1], imagePath="assets/overlay_icons/setflat.png")

        # Gcode stats overlay - top-right panel shown after slicing
        self.gcodeStatsOverlay = GcodeStatsOverlay(self.vtkWidget, self.renderer)


    

    def onKeyPress(self, obj, event):
        key =  super().onKeyPress(obj, event)
        if(key):
            if self.events.iren.GetKeySym() == "BackSpace" or self.events.iren.GetKeySym() == "Delete":
                self.ActorManager.removeActor(onlyPicked = True)
                
                self.moverOverlay.destroyOverlay()
                self.updatePagesRequest()

    def onLeftButtonPress(self, obj, event):
        clickPosition = super().onLeftButtonPress(obj, event)

        # Per-type row click
        clicked_type = self.gcodeStatsOverlay.consume_type_click(clickPosition)
        if clicked_type is not None:
            self.gcodeManager.toggleTypeVisible(clicked_type)
            self._refresh_gcode_overlay()
            return

        # Whole gcode ON/OFF toggle
        if self.gcodeStatsOverlay.consume_toggle_click(clickPosition):
            self.gcodeManager.toggleGcodeVisible()
            self._refresh_gcode_overlay()
            return

        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()

        if self.moverOverlay.determineIfOverlayPressed(clickPosition):
            #Do function assigned to left overlay
            return
        
        displayOverlay = self.ActorManager.selectActor(clickPosition,self.selectedMoveType, shift_pressed)

        
        if(displayOverlay and not self.moverOverlay.overlayEnabled):
            self.moverOverlay.createOverlayActor()
        elif (not displayOverlay and self.moverOverlay.overlayEnabled):
            self.moverOverlay.destroyOverlay()

        self.vtkWidget.GetRenderWindow().Render()

    def onMouseMove(self, obj, event):
        isSomethingMoving =  super().onMouseMove(obj, event)

        if(isSomethingMoving):
            self.ActorManager.setActorOpacity(100)
            self.gcodeManager.removeGcode()

    def onLeftButtonRelease(self, obj, event):
        super().onLeftButtonRelease(obj, event)
        self.gizmoSelectedAxis = None
        self.gizmoStartPosition = None
        self.gizmoActiveActors = []

    
    
    def displayGcode(self, printer=None):
        self.ActorManager.setActorOpacity(0.01)
        self._last_printer = printer
        layers_info = self.gcodeManager.displayGcode(get_runtime_path('enviroment.gcode'))
        self._refresh_gcode_overlay()
        return layers_info

    def _refresh_gcode_overlay(self):
        printer = getattr(self, '_last_printer', None)
        self.gcodeStatsOverlay.show(
            self.gcodeManager._gcode_stats,
            num_layers=len(self.gcodeManager._gcode_layers_info),
            sweep_time_ms=printer.sweepTime if printer else 1000,
            layer_down_time_ms=printer.layerDownTime if printer else 200,
            gcode_visible=self.gcodeManager.isGcodeVisible(),
            hidden_types=self.gcodeManager._hidden_types,
            printer=printer,
        )