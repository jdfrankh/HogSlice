import vtk


class GcodeStatsOverlay:
    """
    Displays a gcode statistics panel in the top-right corner of the VTK viewport.
    Shows per-type line density and an estimated print time.
    """

    _TYPE_COLORS = {
        'wall':       (0.27, 0.27, 1.0),
        'infill':     (1.0,  0.67, 0.0),
        'support':    (0.27, 0.8,  0.27),
        'top_bottom': (1.0,  0.2,  0.2),
    }

    _TYPE_LABELS = [
        ('wall',       'Walls'),
        ('infill',     'Infill'),
        ('support',    'Support'),
        ('top_bottom', 'Top / Bottom'),
    ]

    def __init__(self, vtkWidget, renderer):
        self.vtkWidget = vtkWidget
        self.renderer = renderer
        self._actors = []

    def show(self, stats, num_layers=0, sweep_time_ms=1000, layer_down_time_ms=200):
        self.hide()
        w, h = self.vtkWidget.GetRenderWindow().GetSize()
        if w <= 0 or h <= 0:
            return

        panel_w, panel_h = 275, 170
        margin = 12
        x0 = w - panel_w - margin
        y0 = h - panel_h - margin

        # Semi-transparent dark background
        self._add(self._make_rect(x0, y0, panel_w, panel_h, (0.08, 0.08, 0.08), 0.80))

        # Title
        self._add(self._make_text("Print Statistics", x0 + 8, y0 + panel_h - 22, 13, (1.0, 1.0, 1.0), bold=True))

        # Divider under title
        self._add(self._make_rect(x0 + 6, y0 + panel_h - 30, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

        total = max(stats.get('total', 1), 1)
        row_y = y0 + panel_h - 52

        for key, label in self._TYPE_LABELS:
            count = stats.get(key, 0)
            pct = count / total * 100
            color = self._TYPE_COLORS[key]

            # Colored swatch
            self._add(self._make_rect(x0 + 8, row_y + 2, 12, 12, color, 1.0))
            # Label
            self._add(self._make_text(f"{label}:", x0 + 26, row_y, 11, (0.85, 0.85, 0.85)))
            # Percentage in the type's color
            self._add(self._make_text(f"{pct:.1f}%", x0 + 148, row_y, 11, color))
            # Raw count in subdued text
            self._add(self._make_text(f"({count:,})", x0 + 200, row_y, 10, (0.60, 0.60, 0.60)))

            row_y -= 22

        # Divider above time estimate
        self._add(self._make_rect(x0 + 6, y0 + 26, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

        # Time estimate
        travel_s = stats.get('est_time_s', 0.0)
        overhead_s = num_layers * (sweep_time_ms + layer_down_time_ms) / 1000.0
        time_str = self._format_time(travel_s + overhead_s)
        self._add(self._make_text(f"Est. Time:  {time_str}", x0 + 8, y0 + 8, 12, (1.0, 0.85, 0.3)))

        for actor in self._actors:
            self.renderer.AddActor2D(actor)

        self.renderer.GetRenderWindow().Render()

    def hide(self):
        for actor in self._actors:
            self.renderer.RemoveActor2D(actor)
        self._actors = []

    # ------------------------------------------------------------------

    def _add(self, actor):
        self._actors.append(actor)

    @staticmethod
    def _format_time(seconds):
        seconds = max(0, int(seconds))
        h  = seconds // 3600
        m  = (seconds % 3600) // 60
        s  = seconds % 60
        if h > 0:
            return f"{h}h {m:02d}m {s:02d}s"
        if m > 0:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    @staticmethod
    def _make_rect(x, y, w, h, rgb, opacity):
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(x,     y,     0)
        pts.InsertNextPoint(x + w, y,     0)
        pts.InsertNextPoint(x + w, y + h, 0)
        pts.InsertNextPoint(x,     y + h, 0)

        poly = vtk.vtkPolygon()
        poly.GetPointIds().SetNumberOfIds(4)
        for i in range(4):
            poly.GetPointIds().SetId(i, i)

        cells = vtk.vtkCellArray()
        cells.InsertNextCell(poly)

        pd = vtk.vtkPolyData()
        pd.SetPoints(pts)
        pd.SetPolys(cells)

        coord = vtk.vtkCoordinate()
        coord.SetCoordinateSystemToDisplay()

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(pd)
        mapper.SetTransformCoordinate(coord)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*rgb)
        actor.GetProperty().SetOpacity(opacity)
        return actor

    @staticmethod
    def _make_text(text, x, y, font_size, rgb, bold=False):
        actor = vtk.vtkTextActor()
        actor.SetInput(text)
        actor.SetPosition(x, y)
        prop = actor.GetTextProperty()
        prop.SetFontSize(font_size)
        prop.SetColor(*rgb)
        prop.SetFontFamilyToArial()
        prop.BoldOn() if bold else prop.BoldOff()
        return actor
