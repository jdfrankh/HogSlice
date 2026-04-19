import vtk

class OverlayTemplate:

    vtkWidget = None
    renderer = None
    events = None
    colors = None

    IDELEMENT = 0
    FUNTIONELEMENT = 1
    TYPEELEMENT = 2
    LOCATIONELEMENT = 3
    FONTSIZEELEMENT = 4
    COLORELEMENT = 5
    PRESSEDTHRESHOLD = 6

    displayPoints = []  # Should be a ratio of the screen. 4 Points for a rectangle

    actor = None # Current actor for this template

    overlayEnabled = True

    enablePressing = False

    elements = [] # buttons, text, etc
    shownElements = []

    def __init__(self, vtkWidget, colors, renderer, events,displaySizeAndLocation = None, enablePressing = False):
        self.vtkWidget = vtkWidget
        self.renderer = renderer
        self.events = events
        self.colors = colors
        self.widgetName = []
        self.buttons = []
        self.textActors = []
        self.displayPoints = displaySizeAndLocation
        self.enablePressing = enablePressing


    def createOverlayActor(self):
        points = vtk.vtkPoints()
        #print(f"Displaypoints: {self.displayPoints}")
        for display in self.displayPoints:
            print(f"Point: {display}")
            points.InsertNextPoint(display[0], display[1], display[2])

        polygon = vtk.vtkPolygon()
        polygon.GetPointIds().SetNumberOfIds(len(self.displayPoints))
        for index in range(len(self.displayPoints)):
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

        self.actor = vtk.vtkActor2D()
        self.actor.SetMapper(mapper)
        self.actor.GetProperty().SetColor(self.colors.GetColor3d("IndianRed"))
        self.actor.GetProperty().SetOpacity(0.5)

        self.renderer.AddActor2D(self.actor)

        #Remove previous text
        for element in self.shownElements:
            self.renderer.RemoveActor2D(element)
        self.shownElements = []

        for element in self.elements:
            if(element[self.TYPEELEMENT] == "BUTTON"):
                print(f"Building {element[self.TYPEELEMENT]}: {element[self.IDELEMENT]}")

                temp = vtk.vtkTextActor()
                temp.SetInput(element[self.IDELEMENT])
                temp.GetTextProperty().SetColor(self.colors.GetColor3d(element[self.COLORELEMENT]))
                temp.GetTextProperty().SetFontSize(element[self.FONTSIZEELEMENT])
                temp.SetPosition(element[self.LOCATIONELEMENT][0], element[self.LOCATIONELEMENT][1]) # self.LOCATIONELEMENT][0]
                self.renderer.AddActor2D(temp)
            elif(element[self.TYPEELEMENT] == "LABEL"):
                temp = vtk.vtkTextActor()
                temp.SetInput(element[self.IDELEMENT])
                temp.GetTextProperty().SetColor(self.colors.GetColor3d(element[self.COLORELEMENT]))
                temp.GetTextProperty().SetFontSize(element[self.FONTSIZEELEMENT])
                temp.SetPosition(element[self.LOCATIONELEMENT][0], element[self.LOCATIONELEMENT][1]) # self.LOCATIONELEMENT][0]
                


            
                self.shownElements.append(temp)
                                                   
        self.overlayEnabled = True
        

    def destroyOverlay(self):
        if self.actor:
            self.renderer.RemoveActor2D(self.actor)

        for actor in self.shownElements:
            self.renderer.RemoveActor2D(actor)
        self.shownElements = []

        self.overlayEnabled = False

        self.renderer.GetRenderWindow().Render()

    def determineIfOverlayPressed(self, click_pos):
        if(not self.enablePressing):
            return False
        
        if(self.overlayEnabled):
            window_width, window_height = self.vtkWidget.GetRenderWindow().GetSize()
            if window_width <= 0 or window_height <= 0:
                return False

            #normalized_x = click_pos[0] / window_width
            #normalized_y = click_pos[1] / window_height

        

            #If any of the buttons were pressed, run the function and return true

            # Determine if any element is pressed
            for i, element in enumerate(self.elements):

                #print(element[self.LOCATIONELEMENT])
                #print(element[self.PRESSEDTHRESHOLD])

                pressedRangeX = [ element[self.LOCATIONELEMENT][0] -element[self.PRESSEDTHRESHOLD][0]/2 , element[self.LOCATIONELEMENT][0] + element[self.PRESSEDTHRESHOLD][0]/2] 
                pressedRangeY = [ element[self.LOCATIONELEMENT][1] -element[self.PRESSEDTHRESHOLD][1]/2 , element[self.LOCATIONELEMENT][1] + element[self.PRESSEDTHRESHOLD][1]/2]

                if pressedRangeX[0] <= click_pos[0] <= pressedRangeX[1] and pressedRangeY[0] <= click_pos[1] <= pressedRangeY[1]:
                    print(f"Element {element[self.IDELEMENT]} Pressed ")
                    if element[self.FUNTIONELEMENT] is not None:
                        element[self.FUNTIONELEMENT]()
                        return True

            # if 0.10 <= normalized_x <= 0.90 and 0.0 <= normalized_y <= 0.10:
            #     print("Left overlay picked at position:", click_pos)
            #     # Check which button was hit using pixel positions
            #     initPos = 300
            #     button_width = 150
            #     button_height = 40
            #     x, y = click_pos[0], click_pos[1]
            #     for i, button in enumerate(self.buttons):
            #         bx = initPos + i * 200
            #         if bx <= x <= bx + button_width and 30 <= y <= 30 + button_height:
            #             print("Button pressed:", button[self.CONST_BUTTON_ID])
            #             if button[self.FUNTIONELEMENT] is not None:
            #                 button[self.FUNTIONELEMENT]()
            #             return True
            #     return True
        print("No Buttons Pressed")
        return False
    
    def addElement(self, id, elementType,location = [], function = None, fontSize = 24, color = "White", pressedThreshold = [ 350,60]):
        print(f"Adding Element {id} at {location}")
        self.elements.append([id, function, elementType, location, fontSize, color, pressedThreshold ])
        


    def removeElement(self, id):
        for element in self.elements:
            if element[self.IDELEMENT] == id:
                self.elements.remove[element]


    

