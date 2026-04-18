import vtk
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
#from .vulkanActor import Actor, ActorType
#from .BuildChamber  import BuildChamber
from .ActorManager import ActorManager
from .eventManager import EventManager
from .leffOverlay import leftOverlay
import numpy as np
import math

from constants import BuildChamberDisplay

class VulkanManager:
    
    vtkWidget = None
    colors = None
    renderer = None
    #iren = None
    events = None

    selectedMoveType = "Translate"

    moveTypes = ["Translate", "Rotate", "Scale"]

    leftOverlay = None

    updatePagesRequest = None


    ActorManager = None


    picker = vtk.vtkPropPicker()

    def __init__(self, printerBed = [], updatePagesFunction = None):
        self.vtkWidget = QVTKRenderWindowInteractor(None)
        self.colors = vtk.vtkNamedColors()
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.renderer)

        self.events = EventManager(self.vtkWidget, self)

        self.ActorManager = ActorManager(self.vtkWidget, self.colors, self.renderer, self.events, self.picker, printerBed)
        #self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.updatePagesRequest = updatePagesFunction
        # Ensure the VTK widget can receive mouse release events
        self.vtkWidget.setFocusPolicy(Qt.ClickFocus)
        self.vtkWidget.setFocus()

        self.leftOverlay = leftOverlay(self.vtkWidget, self.colors, self.renderer, self.events)

        self.leftOverlay.addButton("Translate", lambda: self.setMoveType("Translate"))
        self.leftOverlay.addButton("Rotate", lambda: self.setMoveType("Rotate"))
        self.leftOverlay.addButton("Scale", lambda: self.setMoveType("Scale"))
        self.leftOverlay.addButton("SetFlat", lambda: self.setMoveType("SetFlat"))

        self.events.AddObserver("LeftButtonPressEvent", self.onLeftButtonPress)
        self.events.AddObserver("MouseMoveEvent", self.onMouseMove)
        self.events.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonRelease)
        self.events.AddObserver("KeyPressEvent", self.onKeyPress)

        self.events.printEnabledEvents()
        # Gradient background (dark → lighter)
        self.renderer.GradientBackgroundOn()
        self.renderer.SetBackground(BuildChamberDisplay.backgroundColor1)      # bottom color
        self.renderer.SetBackground2(BuildChamberDisplay.backgroundColor2)     # top color

        self.vtkWidget.Initialize()
        self.vtkWidget.Start()

        # Qt fallback for mouse release events
        self._originalMouseReleaseEvent = self.vtkWidget.mouseReleaseEvent
        self.vtkWidget.mouseReleaseEvent = self._qtMouseReleaseEvent

        
        self.events.set_isometric_view(self.renderer.GetActiveCamera())



        self.ActorManager.prepareEnviroment()
        
        self.vtkWidget.GetRenderWindow().Render()

        # Gcode viewer state
        self._gcode_actor = None
        self._gcode_threshold = None
        self._gcode_layers_info = []
        self._gcode_layer_cumulative = []
        self._gcode_total_lines = 0

        # Create wrapper widget: VTK view + gcode controls
        self.viewWidget = QWidget()
        viewLayout = QVBoxLayout(self.viewWidget)
        viewLayout.setContentsMargins(0, 0, 0, 0)
        viewLayout.setSpacing(2)

        # Top area: VTK widget + vertical layer slider
        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        self.vtkWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        topLayout.addWidget(self.vtkWidget)

        # Vertical layer slider (right side)
        self._layerSliderWidget = QWidget()
        layerLayout = QVBoxLayout(self._layerSliderWidget)
        layerLayout.setContentsMargins(2, 2, 2, 2)
        self._layerLabel = QLabel("Layer")
        self._layerLabel.setAlignment(Qt.AlignCenter)
        self._layerSlider = QSlider(Qt.Vertical)
        self._layerSlider.setMinimum(0)
        self._layerSlider.setMaximum(0)
        self._layerSlider.valueChanged.connect(self._onLayerChanged)
        self._layerValue = QLabel("0 / 0")
        self._layerValue.setAlignment(Qt.AlignCenter)
        layerLayout.addWidget(self._layerLabel)
        layerLayout.addWidget(self._layerSlider)
        layerLayout.addWidget(self._layerValue)
        self._layerSliderWidget.setFixedWidth(60)
        self._layerSliderWidget.hide()
        topLayout.addWidget(self._layerSliderWidget)
        viewLayout.addLayout(topLayout)

        # Horizontal line slider (bottom)
        self._lineSliderWidget = QWidget()
        lineLayout = QHBoxLayout(self._lineSliderWidget)
        lineLayout.setContentsMargins(2, 2, 2, 2)
        self._lineLabel = QLabel("Line:")
        self._lineLabel.setFixedWidth(35)
        self._lineSlider = QSlider(Qt.Horizontal)
        self._lineSlider.setMinimum(0)
        self._lineSlider.setMaximum(0)
        self._lineSlider.valueChanged.connect(self._onLineChanged)
        self._lineValue = QLabel("0 / 0")
        self._lineValue.setFixedWidth(80)
        lineLayout.addWidget(self._lineLabel)
        lineLayout.addWidget(self._lineSlider)
        lineLayout.addWidget(self._lineValue)
        self._lineSliderWidget.hide()
        viewLayout.addWidget(self._lineSliderWidget)

        # Legend
        self._legendWidget = QWidget()
        legendLayout = QHBoxLayout(self._legendWidget)
        legendLayout.setContentsMargins(4, 2, 4, 2)
        for label_text, color in [("Wall", "#4444FF"), ("Infill", "#FFAA00"), ("Support", "#44CC44")]:
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background-color: {color}; border: 1px solid #666;")
            legendLayout.addWidget(swatch)
            legendLayout.addWidget(QLabel(label_text))
            legendLayout.addSpacing(10)
        legendLayout.addStretch()
        self._legendWidget.hide()
        viewLayout.addWidget(self._legendWidget)

    def getScene(self):
        return self.ActorManager.exportAllActorsToSTL()
    

    def setMoveType(self, moveType):
        self.selectedMoveType = moveType
        
        self.ActorManager.changeMoveType(moveType)

        self.renderer.GetRenderWindow().Render()
        print("Selected Move Type:", self.selectedMoveType)

    def onKeyPress(self, obj, event):
        if self.events.iren.GetKeySym() == "BackSpace" or self.events.iren.GetKeySym() == "Delete":
            self.ActorManager.removeActor(onlyPicked = True)

    def parseActor(self, fileName):
        self.ActorManager.insertActor(fileName)


    def printActors(self):

        return self.ActorManager.printActors()
    
    def selectActorById(self, id):
        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()
        print("Selecting actor by ID:", id)
         
        overlayNeeded = self.ActorManager.selectActorByID(id, self.selectedMoveType, shift_pressed)

        if overlayNeeded and not self.leftOverlay.overlayEnabled:
            self.leftOverlay.createOverlayActor()
        
        self.renderer.GetRenderWindow().Render()

    def onLeftButtonPress(self, obj, event):
        print("Left Button Pressed----------------------------------")
        click_pos = self.events.getEventPosition()
        
        shift_pressed = self.vtkWidget.GetRenderWindow().GetInteractor().GetShiftKey()

        if self.leftOverlay.determineIfOverlayPressed(click_pos):
            #Do function assigned to left overlay
            return


        displayOverlay = self.ActorManager.selectActor(click_pos,self.selectedMoveType, shift_pressed)

        
        if(displayOverlay and not self.leftOverlay.overlayEnabled):
            self.leftOverlay.createOverlayActor()
        elif (not displayOverlay and self.leftOverlay.overlayEnabled):
            self.leftOverlay.destroyOverlay()

        self.vtkWidget.GetRenderWindow().Render()
        
        #self.events.toggleCamera(True)

    def onMouseMove(self, obj, event):

        self.ActorManager.moveSelectedActors()

    def onLeftButtonRelease(self, obj, event):
        print("Left Button Releasaed-------------------------------------------")
        self.events.toggleCamera(False)

        self.ActorManager.finishActions()
   
        self.gizmoSelectedAxis = None
        self.gizmoStartPosition = None
        self.gizmoActiveActors = []

    # -- Gcode type constants for scalar coloring --
    GCODE_TYPE_WALL = 0
    GCODE_TYPE_INFILL = 1
    GCODE_TYPE_SUPPORT = 2

    def displayGcode(self, filepath):
        """Parse a gcode file and display the toolpath with wall/infill/support coloring."""
        # Remove previous gcode actor
        if self._gcode_actor is not None:
            self.renderer.RemoveActor(self._gcode_actor)
            self._gcode_actor = None
        self._gcode_threshold = None

        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        type_array = vtk.vtkIntArray()
        type_array.SetName("Type")
        order_array = vtk.vtkIntArray()
        order_array.SetName("Order")

        TYPE_MAP = {'wall': self.GCODE_TYPE_WALL, 'infill': self.GCODE_TYPE_INFILL, 'support': self.GCODE_TYPE_SUPPORT}

        cur_x, cur_y, cur_z = 0.0, 0.0, 0.0
        current_section = 'wall'
        in_layer = False
        layer_line_count = 0
        global_order = 0
        layers_info = []

        with open(filepath, 'r') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith(';Layer'):
                    if in_layer:
                        layers_info.append(layer_line_count)
                        layer_line_count = 0
                    in_layer = True
                    current_section = 'wall'
                    continue
                if line == ';perimeter':
                    current_section = 'wall'
                    continue
                if line == ';infill':
                    current_section = 'infill'
                    continue
                if line == ';support':
                    current_section = 'support'
                    continue
                if line.startswith(';') or not line[0] == 'G':
                    continue

                parts = line.split()
                cmd = parts[0]
                if cmd not in ('G0', 'G1'):
                    continue

                new_x, new_y, new_z = cur_x, cur_y, cur_z
                for p in parts[1:]:
                    if p[0] == 'X':
                        new_x = float(p[1:])
                    elif p[0] == 'Y':
                        new_y = float(p[1:])
                    elif p[0] == 'Z':
                        new_z = float(p[1:])

                if cmd == 'G1' and in_layer:
                    id0 = points.InsertNextPoint(cur_x, cur_y, cur_z)
                    id1 = points.InsertNextPoint(new_x, new_y, new_z)
                    vtkLine = vtk.vtkLine()
                    vtkLine.GetPointIds().SetId(0, id0)
                    vtkLine.GetPointIds().SetId(1, id1)
                    lines.InsertNextCell(vtkLine)
                    type_array.InsertNextValue(TYPE_MAP.get(current_section, 0))
                    order_array.InsertNextValue(global_order)
                    global_order += 1
                    layer_line_count += 1

                cur_x, cur_y, cur_z = new_x, new_y, new_z

        if in_layer:
            layers_info.append(layer_line_count)

        # Build polydata with type + order scalars
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(lines)
        polydata.GetCellData().AddArray(type_array)
        polydata.GetCellData().AddArray(order_array)
        polydata.GetCellData().SetActiveScalars("Type")

        # Store layer info for slider control
        self._gcode_layers_info = layers_info
        self._gcode_layer_cumulative = []
        cumsum = 0
        for count in layers_info:
            self._gcode_layer_cumulative.append(cumsum)
            cumsum += count
        self._gcode_total_lines = cumsum

        # Build persistent VTK pipeline: threshold filter -> mapper -> actor
        self._gcode_threshold = vtk.vtkThreshold()
        self._gcode_threshold.SetInputData(polydata)
        self._gcode_threshold.SetInputArrayToProcess(
            0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "Order")

        # Lookup table: wall=blue, infill=orange, support=green
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(3)
        lut.SetTableValue(0, 0.27, 0.27, 1.0, 1.0)   # wall
        lut.SetTableValue(1, 1.0, 0.67, 0.0, 1.0)     # infill
        lut.SetTableValue(2, 0.27, 0.8, 0.27, 1.0)    # support
        lut.Build()

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(self._gcode_threshold.GetOutputPort())
        mapper.SetScalarModeToUseCellData()
        mapper.SelectColorArray("Type")
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(0, 2)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1.5)

        self._gcode_actor = actor
        self.renderer.AddActor(actor)

        # Configure sliders
        max_layer = max(len(layers_info) - 1, 0)
        self._layerSlider.blockSignals(True)
        self._layerSlider.setMaximum(max_layer)
        self._layerSlider.setValue(max_layer)
        self._layerSlider.blockSignals(False)
        self._layerValue.setText(f"{max_layer} / {max_layer}")

        last_layer_lines = layers_info[-1] if layers_info else 0
        self._lineSlider.blockSignals(True)
        self._lineSlider.setMaximum(last_layer_lines)
        self._lineSlider.setValue(last_layer_lines)
        self._lineSlider.blockSignals(False)
        self._lineValue.setText(f"{last_layer_lines} / {last_layer_lines}")

        # Show gcode controls
        self._layerSliderWidget.show()
        self._lineSliderWidget.show()
        self._legendWidget.show()

        self._updateGcodeDisplay()

    def _onLayerChanged(self, value):
        self._layerValue.setText(f"{value} / {self._layerSlider.maximum()}")
        # Update line slider max for the selected layer
        if self._gcode_layers_info and 0 <= value < len(self._gcode_layers_info):
            line_count = self._gcode_layers_info[value]
        else:
            line_count = 0
        self._lineSlider.blockSignals(True)
        self._lineSlider.setMaximum(line_count)
        self._lineSlider.setValue(line_count)
        self._lineSlider.blockSignals(False)
        self._lineValue.setText(f"{line_count} / {line_count}")
        self._updateGcodeDisplay()

    def _onLineChanged(self, value):
        self._lineValue.setText(f"{value} / {self._lineSlider.maximum()}")
        self._updateGcodeDisplay()

    def _updateGcodeDisplay(self):
        if self._gcode_threshold is None:
            return

        layer_idx = self._layerSlider.value()
        line_in_layer = self._lineSlider.value()

        # Compute the max global order index to show
        if layer_idx < len(self._gcode_layer_cumulative):
            max_order = self._gcode_layer_cumulative[layer_idx] + line_in_layer - 1
        else:
            max_order = self._gcode_total_lines - 1

        if max_order < 0:
            self._gcode_actor.SetVisibility(False)
        else:
            self._gcode_actor.SetVisibility(True)
            self._gcode_threshold.ThresholdBetween(0, max_order)
            self._gcode_threshold.Update()

        self.vtkWidget.GetRenderWindow().Render()

    def _qtMouseReleaseEvent(self, event):
        # Ensure release handling even if VTK doesn't emit the event
        self.onLeftButtonRelease(self.events.iren, "LeftButtonReleaseEvent")
        #if self._originalMouseReleaseEvent:
        #    self._originalMouseReleaseEvent(event)





