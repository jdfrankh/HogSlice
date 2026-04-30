from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import math
import vtk


class VulkanGcodeManager:

    vtkWidget = None
    colors = None
    renderer = None
    #iren = None
    events = None

    # -- Gcode type constants for scalar coloring --
    GCODE_TYPE_WALL = 0
    GCODE_TYPE_INFILL = 1
    GCODE_TYPE_SUPPORT = 2
    GCODE_TYPE_TOP_BOTTOM = 3
    GCODE_TYPE_TRAVEL = 4


    def __init__(self, vtkWidget, colors, renderer, events):
        self.vtkWidget = vtkWidget
        self.colors = colors
        self.renderer = renderer
        self.events = events

        # Gcode viewer state
        self._gcode_actor = None
        self._gcode_threshold = None
        self._gcode_layers_info = []
        self._gcode_layer_cumulative = []
        self._gcode_total_lines = 0
        self._gcode_stats = {}
        self._gcode_visible = True
        self._hidden_types = {'travel'}   # travel (G0) hidden by default
        self._lut = None
        # Slider refs – injected by HogforgeApplication after slicing
        self._layerSlider = None
        self._lineSlider = None

    # ---- whole-gcode visibility ----
    def isGcodeVisible(self):
        return bool(self._gcode_visible)

    def setGcodeVisible(self, visible):
        self._gcode_visible = bool(visible)
        if self._gcode_actor is not None:
            self._gcode_actor.SetVisibility(self._gcode_visible)
            self.vtkWidget.GetRenderWindow().Render()
        return self._gcode_visible

    def toggleGcodeVisible(self):
        return self.setGcodeVisible(not self._gcode_visible)

    # ---- per-type visibility ----
    _TYPE_INDEX = {'wall': 0, 'infill': 1, 'support': 2, 'top_bottom': 3, 'travel': 4}
    _TYPE_COLORS = [
        (0.27, 0.27, 1.0),   # wall
        (1.0,  0.67, 0.0),   # infill
        (0.27, 0.8,  0.27),  # support
        (1.0,  0.2,  0.2),   # top_bottom
        (0.5,  0.5,  0.5),   # travel
    ]

    def isTypeVisible(self, type_key):
        return type_key not in self._hidden_types

    def setTypeVisible(self, type_key, visible):
        if visible:
            self._hidden_types.discard(type_key)
        else:
            self._hidden_types.add(type_key)
        self._apply_lut()

    def toggleTypeVisible(self, type_key):
        self.setTypeVisible(type_key, type_key in self._hidden_types)

    def _apply_lut(self):
        if self._lut is None:
            return
        for key, idx in self._TYPE_INDEX.items():
            r, g, b = self._TYPE_COLORS[idx]
            alpha = 0.0 if key in self._hidden_types else 1.0
            self._lut.SetTableValue(idx, r, g, b, alpha)
        self._lut.Modified()
        self.vtkWidget.GetRenderWindow().Render()

    def setSliders(self, layerSlider, lineSlider):
        """Inject the QSlider widgets created by the pageCreator system."""
        self._layerSlider = layerSlider
        self._lineSlider = lineSlider

    def removeGcode(self):
        if self._gcode_actor is not None:
            self.renderer.RemoveActor(self._gcode_actor)
            self._gcode_actor = None
        self._gcode_threshold = None
        self._lut = None
        self._gcode_visible = True

        #Set the opacity of all existing actors back to 100%

    def displayGcode(self, filepath):
        """Parse a gcode file and display the toolpath with wall/infill/support coloring."""
        # Remove previous gcode actor
        self.removeGcode()

        

        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        type_array = vtk.vtkIntArray()
        type_array.SetName("Type")
        order_array = vtk.vtkIntArray()
        order_array.SetName("Order")

        TYPE_MAP = {'wall': self.GCODE_TYPE_WALL, 'infill': self.GCODE_TYPE_INFILL, 'support': self.GCODE_TYPE_SUPPORT, 'top_bottom': self.GCODE_TYPE_TOP_BOTTOM}

        cur_x, cur_y, cur_z = 0.0, 0.0, 0.0
        current_section = 'wall'
        current_feedrate = 2700.0  # default rapid feedrate
        travel_time_s = 0.0
        type_counts = {'wall': 0, 'infill': 0, 'support': 0, 'top_bottom': 0, 'travel': 0}
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
                if line == ';top_bottom':
                    current_section = 'top_bottom'
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
                    elif p[0] == 'F':
                        try:
                            current_feedrate = float(p[1:])
                        except ValueError:
                            pass  # ignore malformed feedrate tokens

                # Accumulate travel time for all moves
                dist = math.sqrt((new_x - cur_x)**2 + (new_y - cur_y)**2 + (new_z - cur_z)**2)
                if current_feedrate > 0:
                    travel_time_s += (dist / current_feedrate) * 60.0

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
                    if current_section in type_counts:
                        type_counts[current_section] += 1
                elif cmd == 'G0' and in_layer:
                    id0 = points.InsertNextPoint(cur_x, cur_y, cur_z)
                    id1 = points.InsertNextPoint(new_x, new_y, new_z)
                    vtkLine = vtk.vtkLine()
                    vtkLine.GetPointIds().SetId(0, id0)
                    vtkLine.GetPointIds().SetId(1, id1)
                    lines.InsertNextCell(vtkLine)
                    type_array.InsertNextValue(self.GCODE_TYPE_TRAVEL)
                    order_array.InsertNextValue(global_order)
                    global_order += 1
                    layer_line_count += 1
                    # G0 travel moves counted separately
                    type_counts['travel'] += 1

                cur_x, cur_y, cur_z = new_x, new_y, new_z

        if in_layer:
            layers_info.append(layer_line_count)

        import slicer as _slicer_mod
        self._gcode_stats = {
            'wall':       type_counts['wall'],
            'infill':     type_counts['infill'],
            'support':    type_counts['support'],
            'top_bottom': type_counts['top_bottom'],
            'travel':     type_counts['travel'],
            'total':      global_order,
            'est_time_s': travel_time_s,
            'volume_cm3': getattr(_slicer_mod, 'last_volume_cm3', 0.0),
        }

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

        # Lookup table: wall=blue, infill=orange, support=green, top_bottom=red, travel=grey
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(5)
        lut.Build()
        self._lut = lut
        self._apply_lut()   # populate colors, respecting any pre-existing hidden types

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(self._gcode_threshold.GetOutputPort())
        mapper.SetScalarModeToUseCellData()
        mapper.SelectColorArray("Type")
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(0, 4)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1.5)

        # Configure sliders
        # max_layer = max(len(layers_info) - 1, 0)
        # self._layerSlider.blockSignals(True)
        # self._layerSlider.setMaximum(max_layer)
        # self._layerSlider.setValue(max_layer)
        # self._layerSlider.blockSignals(False)
        # self._layerValue.setText(f"{max_layer} / {max_layer}")

        # last_layer_lines = layers_info[-1] if layers_info else 0
        # self._lineSlider.blockSignals(True)
        # self._lineSlider.setMaximum(last_layer_lines)
        # self._lineSlider.setValue(last_layer_lines)
        # self._lineSlider.blockSignals(False)
        # self._lineValue.setText(f"{last_layer_lines} / {last_layer_lines}")

        # # Show gcode controls
        # self._layerSliderWidget.show()
        # self._lineSliderWidget.show()
        # self._legendWidget.show()

        self._gcode_actor = actor
        self._gcode_actor.SetVisibility(self._gcode_visible)
        self.renderer.AddActor(actor)

        
        return layers_info
        #self._updateGcodeDisplay()

    def _onLayerChanged(self, value):
        if self._gcode_layers_info and 0 <= value < len(self._gcode_layers_info):
            line_count = self._gcode_layers_info[value]
        else:
            line_count = 0
        if self._lineSlider:
            self._lineSlider.blockSignals(True)
            self._lineSlider.setMaximum(line_count)
            self._lineSlider.setValue(line_count)
            self._lineSlider.blockSignals(False)
        self._updateGcodeDisplay(value, line_count)

    def _onLineChanged(self, value):
        layer_idx = self._layerSlider.value() if self._layerSlider else 0
        self._updateGcodeDisplay(layer_idx, value)

    def _updateGcodeDisplay(self, layer_idx, line_in_layer):
        if self._gcode_threshold is None:
            return
        
        # Configure sliders
        # max_layer = max(len(layers_info) - 1, 0)
        # self._layerSlider.blockSignals(True)
        # self._layerSlider.setMaximum(max_layer)
        # self._layerSlider.setValue(max_layer)
        # self._layerSlider.blockSignals(False)
        # self._layerValue.setText(f"{max_layer} / {max_layer}")

        # last_layer_lines = layers_info[-1] if layers_info else 0
        # self._lineSlider.blockSignals(True)
        # self._lineSlider.setMaximum(last_layer_lines)
        # self._lineSlider.setValue(last_layer_lines)
        # self._lineSlider.blockSignals(False)
        # self._lineValue.setText(f"{last_layer_lines} / {last_layer_lines}")

        # # Show gcode controls
        # self._layerSliderWidget.show()
        # self._lineSliderWidget.show()
        # self._legendWidget.show()

        # layer_idx = self._layerSlider.value()
        # line_in_layer = self._lineSlider.value()

        # Compute the max global order index to show
        if layer_idx < len(self._gcode_layer_cumulative):
            max_order = self._gcode_layer_cumulative[layer_idx] + line_in_layer - 1
        else:
            max_order = self._gcode_total_lines - 1

        if max_order < 0:
            self._gcode_actor.SetVisibility(False)
        else:
            self._gcode_actor.SetVisibility(self._gcode_visible)
            self._gcode_threshold.SetLowerThreshold(0)
            self._gcode_threshold.SetUpperThreshold(max_order)
            self._gcode_threshold.SetThresholdFunction(self._gcode_threshold.THRESHOLD_BETWEEN)
            self._gcode_threshold.Update()

        self.vtkWidget.GetRenderWindow().Render()