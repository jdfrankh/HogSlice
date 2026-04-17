from VulkanWrapper.Printer import Printer

class WindowSettings:
    windowLayout = (1460, 800)
    acceptDropsSetting = True

class ActorConstants:
    selectColor = "Red"
    defaultColor = "LightSteelBlue"
    outOfBoundsColor = "Yellow"
    outOfBoundsSelectColor = "Orange"

    XAxisColor = "Red"
    YAxisColor = "Green"
    ZAxisColor = "Blue"

    FlatSurfaceColor =  [
                (0.2, 0.8, 0.2),
                (0.2, 0.2, 0.8),
                (0.8, 0.8, 0.2),
                (0.8, 0.2, 0.8),
                (0.2, 0.8, 0.8),
                (0.8, 0.5, 0.2),
            ]
    
    FlatSurfaceAreaFraction = 0.05
    FlatSurfaceAngleThreshold = 5.0

    FloorZ = 0.0

class BuildChamberDisplay:
    wallThickess = .1

    displayOrigin = True

    backgroundColor1 = (0.1, 0.1, 0.1) # bottom color
    backgroundColor2 = (0.3, 0.3, 0.3) # top color




class SettingsDisplay:
    
    SHOWNAME = 0
    FUNCTIONELEMENT = 1
    LISTELEMENT = 2

    bedWRow = ["Bed Width (mm)",'bedWidth', [1,1000, Printer.bedWidth, 1, .1]]
    bedHRow = ["Bed Height (mm)", 'bedHeight', [1,1000, Printer.bedHieght, 1, .1]]
    bedDRow = ["Bed Depth (mm)", 'bedDepth', [1,1000, Printer.bedDepth, 1, .1]]

    offsetX = ["Offsets In X (mm)", 'offsetx', [0,1000, Printer.offsetx, 1, .1]]
    offsetY = ["Offsets In Y (mm)", 'offsety', [0,1000, Printer.offsety, 1, .1]]

    laserPower = ["Laser Power (W)", 'power', [1,1000, Printer.power, 1, .1]]
    focalLength = ["Focal Length (mm)", 'focalLength', [1,1000, Printer.focalLength, 1, .1]]
    


    def getAllSettings(self):
        listOfSettings = []

        for attr in dir(self):
            if not attr.startswith("__") and isinstance(getattr(self, attr), list):
                if(isinstance(getattr(self, attr)[self.LISTELEMENT], list)):

                    listOfSettings.append(getattr(self, attr))
        return listOfSettings