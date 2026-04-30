import vtk
import os
import sys

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
    IMAGEPATHELEMENT = 7

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
        self.resizableImageActors = []

    def _resolve_resource_path(self, imagePath):
        if not imagePath:
            return imagePath

        if os.path.isabs(imagePath) and os.path.exists(imagePath):
            return imagePath

        candidates = []

        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, imagePath))

        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, imagePath))

        candidates.append(os.path.join(os.getcwd(), imagePath))

        # Source-tree fallback when running from development environment.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates.append(os.path.join(project_root, imagePath))

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return imagePath


    def getTexture(self, imagePath):
        if not hasattr(self, 'textureCache'):
            self.textureCache = {}
        resolvedPath = self._resolve_resource_path(imagePath)
        if resolvedPath not in self.textureCache:
            reader = vtk.vtkPNMReader() if str(resolvedPath).endswith('.ppm') else vtk.vtkPNGReader()
            reader.SetFileName(resolvedPath)
            reader.Update()
            texture = vtk.vtkTexture()
            texture.SetInputConnection(reader.GetOutputPort())
            self.textureCache[resolvedPath] = texture
        return self.textureCache[resolvedPath]

    def resizeOverlay(self):
        if not self.overlayEnabled:
            return
        
        window_width, window_height = self.vtkWidget.GetRenderWindow().GetSize()
        aspect_ratio = window_width / window_height if window_height > 0 else 1.0

        # We stored the linked vtkPoints inside the actor instances manually for exactly this.
        for actorData in self.resizableImageActors:
            element = actorData['element']
            pointsObj = actorData['points']
            
            center_x, center_y = element[self.LOCATIONELEMENT][0], element[self.LOCATIONELEMENT][1]
            eff_width = element[self.PRESSEDTHRESHOLD][0]
            eff_height = eff_width * aspect_ratio
            
            pointsObj.SetPoint(0, center_x - eff_width/2, center_y - eff_height/2, 0.0)
            pointsObj.SetPoint(1, center_x + eff_width/2, center_y - eff_height/2, 0.0)
            pointsObj.SetPoint(2, center_x + eff_width/2, center_y + eff_height/2, 0.0)
            pointsObj.SetPoint(3, center_x - eff_width/2, center_y + eff_height/2, 0.0)
            
            # Notify VTK that the underlying points data changed
            pointsObj.Modified()

    def createOverlayActor(self):
        self.destroyOverlay(skipRender=True) # Clean up existing actors before rebuilding

        window_width, window_height = self.vtkWidget.GetRenderWindow().GetSize()
        aspect_ratio = window_width / window_height if window_height > 0 else 1.0

        points = vtk.vtkPoints()
        self.resizableImageActors = []
        #print(f"Displaypoints: {self.displayPoints}")
        if self.displayPoints:
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

        self.shownElements = []

        for element in self.elements:
            if(element[self.TYPEELEMENT] == "BUTTON" or element[self.TYPEELEMENT] == "LABEL"):
                print(f"Building {element[self.TYPEELEMENT]}: {element[self.IDELEMENT]}")
                
                if element[self.IMAGEPATHELEMENT]:
                    # Retrieve cached texture
                    texture = self.getTexture(element[self.IMAGEPATHELEMENT])
                    
                    center_x, center_y = element[self.LOCATIONELEMENT][0], element[self.LOCATIONELEMENT][1]
                    
                    # Flex button to maintain a square aspect ratio driven by horizontal window width
                    width = element[self.PRESSEDTHRESHOLD][0]
                    height = width * aspect_ratio
                    
                    # Create quad based on location and size
                    points = vtk.vtkPoints()
                    points.InsertNextPoint(center_x - width/2, center_y - height/2, 0.0) # bottom-left
                    points.InsertNextPoint(center_x + width/2, center_y - height/2, 0.0) # bottom-right
                    points.InsertNextPoint(center_x + width/2, center_y + height/2, 0.0) # top-right
                    points.InsertNextPoint(center_x - width/2, center_y + height/2, 0.0) # top-left
                    
                    tcoords = vtk.vtkFloatArray()
                    tcoords.SetNumberOfComponents(2)
                    tcoords.SetName("TextureCoordinates")
                    tcoords.InsertNextTuple2(0.0, 0.0)
                    tcoords.InsertNextTuple2(1.0, 0.0)
                    tcoords.InsertNextTuple2(1.0, 1.0)
                    tcoords.InsertNextTuple2(0.0, 1.0)
                    
                    polygon = vtk.vtkPolygon()
                    polygon.GetPointIds().SetNumberOfIds(4)
                    for i in range(4):
                        polygon.GetPointIds().SetId(i, i)
                        
                    polygons = vtk.vtkCellArray()
                    polygons.InsertNextCell(polygon)
                    
                    poly_data = vtk.vtkPolyData()
                    poly_data.SetPoints(points)
                    poly_data.SetPolys(polygons)
                    poly_data.GetPointData().SetTCoords(tcoords)
                    
                    mapper = vtk.vtkPolyDataMapper2D()
                    mapper.SetInputData(poly_data)
                    coord = vtk.vtkCoordinate()
                    coord.SetCoordinateSystemToNormalizedViewport()
                    mapper.SetTransformCoordinate(coord)
                    
                    temp = vtk.vtkTexturedActor2D()
                    temp.SetMapper(mapper)
                    temp.SetTexture(texture)
                    self.renderer.AddActor2D(temp)
                    self.shownElements.append(temp)

                    # Store weak-ref for blazing-fast resizeEvent handling without GC thrashing
                    self.resizableImageActors.append({
                        'element': element,
                        'points': points
                    })
                    
                else:
                    # Text fallback
                    temp = vtk.vtkTextActor()
                    temp.SetInput(element[self.IDELEMENT])
                    temp.GetTextProperty().SetColor(self.colors.GetColor3d(element[self.COLORELEMENT]))
                    temp.GetTextProperty().SetFontSize(element[self.FONTSIZEELEMENT])
                    
                    # Normalized Viewport approach for Text
                    coord = temp.GetPositionCoordinate()
                    coord.SetCoordinateSystemToNormalizedViewport()
                    coord.SetValue(element[self.LOCATIONELEMENT][0], element[self.LOCATIONELEMENT][1])
                    
                    self.renderer.AddActor2D(temp)
                    self.shownElements.append(temp)
                    
        self.overlayEnabled = True
        

    def destroyOverlay(self, skipRender=False):
        if self.actor:
            self.renderer.RemoveActor2D(self.actor)
            self.actor = None

        for actor in self.shownElements:
            self.renderer.RemoveActor2D(actor)
        self.shownElements = []

        for actorData in self.resizableImageActors:
            actorData['points'] = None
        self.resizableImageActors = []

        self.overlayEnabled = False

        if not skipRender:
            self.renderer.GetRenderWindow().Render()

    def determineIfOverlayPressed(self, click_pos):
        if(not self.enablePressing):
            return False
        
        if(self.overlayEnabled):
            window_width, window_height = self.vtkWidget.GetRenderWindow().GetSize()
            if window_width <= 0 or window_height <= 0:
                return False

            normalized_x = click_pos[0] / window_width
            normalized_y = click_pos[1] / window_height
            aspect_ratio = window_width / window_height if window_height > 0 else 1.0

            # Determine if any element is pressed
            for i, element in enumerate(self.elements):

                # Assume LOCATIONELEMENT and PRESSEDTHRESHOLD are now in normalized coordinates
                # since we are proportioning to VTK Window
                # Calculate the dynamically skewed height to match the drawing square aspect
                eff_width = element[self.PRESSEDTHRESHOLD][0]
                eff_height = eff_width * aspect_ratio

                pressedRangeX = [ element[self.LOCATIONELEMENT][0] - eff_width/2 , element[self.LOCATIONELEMENT][0] + eff_width/2] 
                pressedRangeY = [ element[self.LOCATIONELEMENT][1] - eff_height/2 , element[self.LOCATIONELEMENT][1] + eff_height/2]

                if pressedRangeX[0] <= normalized_x <= pressedRangeX[1] and pressedRangeY[0] <= normalized_y <= pressedRangeY[1]:
                    print(f"Element {element[self.IDELEMENT]} Pressed ")
                    if element[self.FUNTIONELEMENT] is not None:
                        element[self.FUNTIONELEMENT]()
                        return True

        print("No Buttons Pressed")
        return False
    
    def addElement(self, id, elementType, location = [], function = None, fontSize = 24, color = "White", pressedThreshold = [0.05, 0.05], imagePath = None):
        print(f"Adding Element {id} at {location}")
        self.elements.append([id, function, elementType, location, fontSize, color, pressedThreshold, imagePath ])
        


    def removeElement(self, id):
        for element in self.elements:
            if element[self.IDELEMENT] == id:
                self.elements.remove[element]


    

