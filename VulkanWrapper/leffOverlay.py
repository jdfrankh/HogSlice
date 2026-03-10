import vtk

class leftOverlay:

    vtkWidget = None
    renderer = None
    events = None
    colors = None
    widgetName = []

    CONST_BUTTON_ID = 1
    CONST_BUTTON_FUNCTION = 2

    overlayEnabled = False

    buttons = []
    leftOverlayActor = None

    def __init__(self, vtkWidget, colors, renderer, events):
        self.vtkWidget = vtkWidget
        self.renderer = renderer
        self.events = events
        self.colors = colors
        self.widgetName = []

        #self.createOverlayActor()
        #self.renderer.AddActor2D(self.leftOverlayActor)

    def createOverlayActor(self):
        points = vtk.vtkPoints()
        # x, y, z
        points.InsertNextPoint(0.10, 0.10, 0.0)
        points.InsertNextPoint(0.90, 0.10, 0.0)
        points.InsertNextPoint(0.90, 0, 0.0)
        points.InsertNextPoint(0.10, 0, 0.0)

        polygon = vtk.vtkPolygon()
        polygon.GetPointIds().SetNumberOfIds(4)
        for index in range(4):
            polygon.GetPointIds().SetId(index, index)

        polygons = vtk.vtkCellArray()
        polygons.InsertNextCell(polygon)

        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetPolys(polygons)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(poly_data)

        coordinate = vtk.vtkCoordinate()
        coordinate.SetCoordinateSystemToNormalizedViewport()
        mapper.SetTransformCoordinate(coordinate)

        self.leftOverlayActor = vtk.vtkActor2D()
        self.leftOverlayActor.SetMapper(mapper)
        self.leftOverlayActor.GetProperty().SetColor(self.colors.GetColor3d("IndianRed"))
        self.leftOverlayActor.GetProperty().SetOpacity(0.5)

        self.renderer.AddActor2D(self.leftOverlayActor)

        self.buildButtons()

        self.overlayEnabled = True

    def destroyOverlay(self):
        self.renderer.RemoveActor2D(self.leftOverlayActor)
        self.overlayEnabled = False

    def determineIfOverlayPressed(self, click_pos):

        if(self.overlayEnabled):
            window_width, window_height = self.vtkWidget.GetRenderWindow().GetSize()
            if window_width <= 0 or window_height <= 0:
                return False

            normalized_x = click_pos[0] / window_width
            normalized_y = click_pos[1] / window_height

            if 0.10 <= normalized_x <= 0.90 and 0.10 <= normalized_y <= 0.90:
                print("Left overlay picked at position:", click_pos)
                return True

        return False

    def buildButtons(self):
        for button in self.buttons:
            print("Building button: ", button[self.CONST_BUTTON_ID])
            # Create a vtkTextActor for the button label
            text_actor = vtk.vtkTextActor()
            text_actor.SetInput(button[self.CONST_BUTTON_ID])
            text_actor.GetTextProperty().SetColor(self.colors.GetColor3d("White"))
            text_actor.GetTextProperty().SetFontSize(24)
            text_actor.SetPosition(0.15, 0.15)  # Position within the overlay (normalized coordinates)

            self.renderer.AddActor2D(text_actor)

    def addButton(self, widget_id, function=None):
        


        self.buttons.append([widget_id, function])

    def removeButton(self, widget_id):
        
        for button in self.buttons:
            if button[self.CONST_BUTTON_ID] == widget_id:
                self.buttons.remove(button)
                break

        

