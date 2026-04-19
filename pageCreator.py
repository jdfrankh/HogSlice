from VulkanWrapper.Printer import Printer
from QtWrapper.pageManger import QType

#Page creator is designed to be specific to hogsclice, and is a way
# to define all variables and assign boxes to vairables for each class
# Hogforge application then links the functions defined here to do a specific thing.
# No reference to actual Qt Widgets is made here

class ToolBarDisplay:
    File = [
        ["Open", "openFile"],
        ["Separator"],
        ["Import Printer Profile", "importPrinter"]

    ]

    Import = [


    ]


class PageID:
    HOMEPAGE = 0
    SETTINGSPAGE = 1
    PRINTERPAGE = 2




class DisplayBase:

    isHorizontal = None
    scrollable = False

    QTTYPE = 0 
    SHOWNAME = 1
    FUNCTIONELEMENT = 2
    LISTELEMENT = 3
    BUTTON = 4
    VTK = 5

    def getAllSettings(self):
        listOfSettings = []

        #Pick all items in order of declaration in the list
        for cls in type(self).__mro__:
            if cls is object:
                continue
            for attr, value in cls.__dict__.items():
                if not attr.startswith("__") and isinstance(value, list):
                    if not any(v is value for v in listOfSettings):
                        listOfSettings.append(value)

        return listOfSettings

#Instead of harf-coding. Import these profiles in using the profile too?

class PrinterDisplay(DisplayBase):

    isHorizontal = True
    scrollable = True

    generalBarPage = ["CREATE PAGE",  0]

    generalBar = ["LIST", "Printer Settings", "printerList", ["Printer 1", "Printer 2"], [100]]

    generalBarFinishPage = ["FINISH PAGE", "New Page"]

    settingsList = ["CREATE PAGE", 0]

    bedWRow = ["SETTING", "Bed Width (mm)",'bedWidth', [1,1000, Printer.bedWidth, 1, .1]]
    bedHRow = ["SETTING", "Bed Height (mm)", 'bedHeight', [1,1000, Printer.bedHeight, 1, .1]]
    bedDRow = ["SETTING", "Bed Depth (mm)", 'bedDepth', [1,1000, Printer.bedDepth, 1, .1]]

    
    printText = ["LABEL", "===================="]

    offsetX = ["SETTING", "Offsets In X (mm)", 'offsetx', [0,1000, Printer.offsetx, 1, .1]]
    offsetY = ["SETTING", "Offsets In Y (mm)", 'offsety', [0,1000, Printer.offsety, 1, .1]]

    laserPower = ["SETTING","Laser Power (W)", 'power', [1,1000, Printer.power, 1, .1]]
    focalLength = ["SETTING", "Focal Length (mm)", 'focalLength', [1,1000, Printer.focalLength, 1, .1]]

    spacing1 = ["SPACING", 20]

    newPage2  = ["CREATE PAGE",  1] # False for horizontal, True for veritcal 

    printSettings  = ["BUTTON", "Print Settings", "savePrinter"]
    importSettings  = ["BUTTON", "Import Settings", "importPrinter"]

    finishPage = ["FINISH PAGE", "New Page"]

    finishSettingsList = ["FINISH PAGE", "New Page"]


class SettingsDisplay(DisplayBase):
    isHorizontal = True
    scrollable = True

    generalBarPage = ["CREATE PAGE",  0]

    generalBar = ["LIST", "Printer Settings", "printerList", ["General"], [100]]

    generalBarFinishPage = ["FINISH PAGE", "New Page"]

    settingsList = ["CREATE PAGE", 0]

    settingsLabel = ["LABEL", "General Settings"]
    settingsSpacing = ["SPACING", 10]

    numWalls = ["SETTING", "Number of Walls:", 'numWalls', [1, 200, Printer.numWalls, 0, 1]]
    supportInfill = ["SETTING", "Support Infill %:", 'supportInfill', [0, 100, Printer.supportInfill, 1, 5.0]]
    extrudeWidth = ["SETTING", "Extrude Width (mm):", 'extrudeWidth', [0.01, 5.0, Printer.extrudeWidth, 2, 0.01]]
    laserWidth = ["SETTING", "Laser Width (mm):", 'laserWidth', [0.001, 1.0, Printer.laserWidth, 3, 0.001]]
    sweepTime = ["SETTING", "Sweep Time (ms):", 'sweepTime', [0, 10000, Printer.sweepTime, 0, 50]]
    layerDownTime = ["SETTING", "Layer Down Time (ms):", 'layerDownTime', [0, 10000, Printer.layerDownTime, 0, 50]]

    topBottomLabel = ["LABEL", "== Bottom & Top Walls =="]
    topBottomSpacing = ["SPACING", 5]
    bottomLayers = ["SETTING", "Bottom Layers:", 'bottomLayers', [0, 50, Printer.bottomLayers, 0, 1]]
    topLayers = ["SETTING", "Top Layers:", 'topLayers', [0, 50, Printer.topLayers, 0, 1]]

    finishSettingsList = ["FINISH PAGE", "New Page"]

class TopBarDisplay(DisplayBase):

    isHorizontal = True

    homeButton = ["BUTTON", "Home", "goHome"]
    spacing1 = ["SPACING", 20]
    settingsButton = ["BUTTON", "Settings", "goSettings"]
    spacing2 = ["SPACING", 20]
    printerButton = ["BUTTON", "Printer", "goPrinter"]
    spacing3 = ["SPACING", 5]

class HomeDisplay(DisplayBase):

    isHorizontal = True

    # Column 1: VTK widget with horizontal (line) slider underneath
    vtkColumn = ["CREATE PAGE", 0]  # VBox
    vtkView = ["VTK"]
    hSlider = ["SLIDER", 1, ["getHorizontallMin", "getHorizontalMax", "getHorizontalCurrentValue"]]
    vtkColumnFinish = ["FINISH PAGE", "VTK Column"]

    # Column 2: vertical (layer) slider beside the VTK column
    vSlider = ["SLIDER", 0, ["getVerticalMin", "getVeritcalMax", "getVerticalCurrentValue"]]


    sidebarPage = ["CREATE PAGE", 0]

    printSettingsLabel = ["LABEL", "Print Settings"]

    buttonPage = ["CREATE PAGE", 1]
    
    
    exportButton = ["SELFREF_BUTTON", "Export Gcode", "exportGcode", "exportGcodeButton"]
    saveButton = ["SELFREF_BUTTON", "Save Gcode", "saveToFile", "saveToFileButton"]

    buttonPageFinish = ["FINISH PAGE", "ButtonPage"]

    

    progressBar = ["PROGRESS", "", "progressBar", [0, 100]]

    sidebarSpacing = ["SPACING", 10]
    materialRow = ["COMBOBOX", "Material Settings:", "material", ["M2 Steel", "M1 Steel", "316L Steel", "1080 Steel"]]
    powerRow = ["SETTING", "Power:", "power", [1, 100, Printer.power]]
    speedRow = ["SETTING", "Speed mm/min:", "speed", [1, 10000, Printer.speed]]
    infillRow = ["SETTING", "Infill:", "infill", [0, 100, Printer.infill]]
    layerHeightRow = ["COMBOBOX", "Layer Height mm:", "layerHeight", ["0.05", "0.1", "0.15", "0.2", "0.25"]]

    printQueue = ["UPDATE_LIST", "Print Queue", "selectActor", [""]]

    sidebarFinish = ["FINISH PAGE", "Sidebar"]


currentDisplays = [HomeDisplay(), PrinterDisplay(), SettingsDisplay()]



