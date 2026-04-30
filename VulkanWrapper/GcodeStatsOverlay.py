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
        'travel':     (0.5,  0.5,  0.5),
    }

    _TYPE_LABELS = [
        ('wall',       'Walls'),
        ('infill',     'Infill'),
        ('support',    'Support'),
        ('top_bottom', 'Top / Bottom'),
        ('travel',     'Travel (G0)'),
    ]

    def __init__(self, vtkWidget, renderer):
        self.vtkWidget = vtkWidget
        self.renderer = renderer
        self._actors = []
        self._toggle_bounds = None
        self._row_bounds = {}   # type_key -> (x, y, w, h)

    def show(self, stats, num_layers=0, sweep_time_ms=1000, layer_down_time_ms=200,
             gcode_visible=True, hidden_types=None, printer=None):
        self.hide()
        hidden_types = hidden_types or set()
        w, h = self.vtkWidget.GetRenderWindow().GetSize()
        if w <= 0 or h <= 0:
            return

        volume_cm3 = stats.get('volume_cm3', 0.0)
        has_material = volume_cm3 > 0 and printer is not None

        panel_w = 275
        panel_h = 220
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
        row_h = 20

        for key, label in self._TYPE_LABELS:
            count = stats.get(key, 0)
            pct = count / total * 100
            hidden = key in hidden_types
            color = self._TYPE_COLORS[key]
            dim_color = tuple(c * 0.35 for c in color)
            text_color = (0.45, 0.45, 0.45) if hidden else (0.85, 0.85, 0.85)
            used_color = dim_color if hidden else color

            # Clickable highlight when visible
            if not hidden:
                self._add(self._make_rect(x0 + 4, row_y - 2, panel_w - 8, row_h, (0.18, 0.18, 0.18), 0.6))

            # Colored swatch (dimmed if hidden)
            self._add(self._make_rect(x0 + 8, row_y + 2, 12, 12, used_color, 1.0))
            # Label
            self._add(self._make_text(f"{label}:", x0 + 26, row_y, 11, text_color))
            # Percentage in the type's color
            self._add(self._make_text(f"{pct:.1f}%", x0 + 148, row_y, 11, used_color))
            # Raw count in subdued text
            self._add(self._make_text(f"({count:,})", x0 + 200, row_y, 10, (0.40, 0.40, 0.40) if hidden else (0.60, 0.60, 0.60)))
            # Strike-through overlay when hidden
            if hidden:
                self._add(self._make_rect(x0 + 6, row_y + 6, panel_w - 12, 1, (0.70, 0.70, 0.70), 0.8))

            self._row_bounds[key] = (x0 + 4, row_y - 2, panel_w - 8, row_h)
            row_y -= 22

        # Divider above toggle row
        self._add(self._make_rect(x0 + 6, y0 + 46, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

        toggle_text = "ON" if gcode_visible else "OFF"
        toggle_color = (0.27, 0.9, 0.27) if gcode_visible else (0.9, 0.35, 0.35)
        self._add(self._make_text("G-code:", x0 + 8, y0 + 30, 11, (0.85, 0.85, 0.85)))
        self._add(self._make_text(toggle_text, x0 + 78, y0 + 30, 11, toggle_color, bold=True))
        self._add(self._make_text("(click to toggle)", x0 + 118, y0 + 30, 10, (0.65, 0.65, 0.65)))
        self._toggle_bounds = (x0 + 6, y0 + 24, panel_w - 12, 18)

        # Divider above time estimate
        self._add(self._make_rect(x0 + 6, y0 + 20, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

        # Time estimate
        travel_s = stats.get('est_time_s', 0.0)
        overhead_s = num_layers * (sweep_time_ms + layer_down_time_ms) / 1000.0
        time_str = self._format_time(travel_s + overhead_s)
        self._add(self._make_text(f"Est. Time:  {time_str}", x0 + 8, y0 + 4, 12, (1.0, 0.85, 0.3)))

        # --- Material stats panel (separate panel below gcode panel) ---
        if has_material:
            density  = printer.getMaterialDensity()       # g/cm³
            cost_per_g = printer.getMaterialCostPerGram() # $/g
            weight_g = volume_cm3 * density
            cost     = weight_g * cost_per_g
            mat_name = getattr(printer, 'material', '')

            mat_panel_h = 100
            gap         = 8
            mx0 = x0
            my0 = y0 - mat_panel_h - gap

            # Background
            self._add(self._make_rect(mx0, my0, panel_w, mat_panel_h, (0.08, 0.08, 0.08), 0.80))
            # Title
            self._add(self._make_text("Material Statistics", mx0 + 8, my0 + mat_panel_h - 22, 13, (1.0, 1.0, 1.0), bold=True))
            # Divider under title
            self._add(self._make_rect(mx0 + 6, my0 + mat_panel_h - 30, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

            row_color = (0.75, 0.95, 0.75)
            self._add(self._make_text(f"Material:", mx0 + 8,  my0 + 72, 11, (0.85, 0.85, 0.85)))
            self._add(self._make_text(mat_name,    mx0 + 88,  my0 + 72, 11, row_color))
            self._add(self._make_text(f"Volume:",  mx0 + 8,  my0 + 50, 11, (0.85, 0.85, 0.85)))
            self._add(self._make_text(f"{volume_cm3:.3f} cm³", mx0 + 88, my0 + 50, 11, row_color))
            self._add(self._make_text(f"Weight:",  mx0 + 8,  my0 + 28, 11, (0.85, 0.85, 0.85)))
            self._add(self._make_text(f"{weight_g:.2f} g",   mx0 + 88, my0 + 28, 11, row_color))
            self._add(self._make_text(f"Cost:",    mx0 + 148, my0 + 28, 11, (0.85, 0.85, 0.85)))
            self._add(self._make_text(f"${cost:.2f}", mx0 + 196, my0 + 28, 11, row_color))
            # Bottom divider
            self._add(self._make_rect(mx0 + 6, my0 + 20, panel_w - 12, 1, (0.55, 0.55, 0.55), 0.9))

        for actor in self._actors:
            self.renderer.AddActor2D(actor)

        self.renderer.GetRenderWindow().Render()

    def hide(self):
        for actor in self._actors:
            self.renderer.RemoveActor2D(actor)
        self._actors = []
        self._toggle_bounds = None
        self._row_bounds = {}

    def consume_type_click(self, click_pos):
        """Returns the type_key clicked (e.g. 'wall') or None."""
        if not click_pos:
            return None
        x, y = click_pos
        for key, (bx, by, bw, bh) in self._row_bounds.items():
            if bx <= x <= (bx + bw) and by <= y <= (by + bh):
                return key
        return None

    def consume_toggle_click(self, click_pos):
        if self._toggle_bounds is None or click_pos is None:
            return False

        x, y = click_pos
        bx, by, bw, bh = self._toggle_bounds
        return bx <= x <= (bx + bw) and by <= y <= (by + bh)

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
