from VulkanWrapper.Printer import Printer
from VulkanWrapper.Settings import Settings
from VulkanWrapper.ConfigProfileBase import ConfigProfileBase
from QtWrapper.pageManger import QType

#Page creator is designed to be specific to hogsclice, and is a way
# to define all variables and assign boxes to vairables for each class
# Hogforge application then links the functions defined here to do a specific thing.
# No reference to actual Qt Widgets is made here

class ToolBarDisplay:
    File = [
        ["Open", "openFile"],
        ["Separator"],
        ["Import Printer Profile", "importPrinter"],
        ["Separator"],
        ["Import Settings", "importSettings"],
        ["Export Settings", "exportSettings"],
        ["Save Settings", "saveSettings"],
        ["Reset To Defaults", "resetToDefaults"]

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

class _PrinterSettingsProfile(ConfigProfileBase):
    """Metadata-only class that defines the Printer page settings groups."""
    def __init__(self):
        super().__init__()
        self.add_group("Bed", [
            self.make_setting("Bed Width (mm):", "bedWidth", [1, 1000, Printer.bedWidth, 1, 0.1]),
            self.make_setting("Bed Height (mm):", "bedHeight", [1, 1000, Printer.bedHeight, 1, 0.1]),
            self.make_setting("Bed Depth (mm):", "bedDepth", [1, 1000, Printer.bedDepth, 1, 0.1]),
        ])
        self.add_group("Position", [
            self.make_setting("Offset X (mm):", "offsetx", [0, 1000, Printer.offsetx, 1, 0.1]),
            self.make_setting("Offset Y (mm):", "offsety", [0, 1000, Printer.offsety, 1, 0.1]),
        ])
        self.add_group("Laser", [
            self.make_setting("Laser Power (W):", "power", [1, 1000, Printer.power, 1, 0.1]),
            self.make_setting("Focal Length (mm):", "focalLength", [1, 1000, Printer.focalLength, 1, 0.1]),
        ])


class PrinterDisplay(DisplayBase):

    isHorizontal = True
    scrollable = True

    def __init__(self, printerNames=None, selectedPrinter=None, selectedGroup=None):
        names = list(printerNames) if printerNames else ["Hogforge V1", "Hogforge V2"]
        self.selectedPrinter = selectedPrinter if selectedPrinter in names else (names[0] if names else "")
        self.printerNames = names
        self._profile = _PrinterSettingsProfile()
        groups = self._profile.get_group_names()
        if selectedGroup in groups:
            self.selectedGroup = selectedGroup
        elif groups:
            self.selectedGroup = groups[0]
        else:
            self.selectedGroup = ""

    def getAllSettings(self):
        groups = self._profile.get_group_names()
        if self.selectedGroup not in groups and groups:
            self.selectedGroup = groups[0]

        group_choices = [self.selectedGroup] + [g for g in groups if g != self.selectedGroup]
        printer_choices = [self.selectedPrinter] + [p for p in self.printerNames if p != self.selectedPrinter]

        rows = [
            ["CREATE PAGE", 1],
            ["CREATE PAGE", 0],
            ["LABEL", "Printer Profiles"],
            ["SPACING", 8],
            ["LIST", "Printer Settings", "selectPrinterProfile", printer_choices],
            ["SPACING", 10],
            ["BUTTON", "Save Settings", "savePrinter"],
            ["BUTTON", "Import Settings", "importPrinter"],
            ["SPACING", 20],
            ["LABEL", "Settings Groups"],
            ["SPACING", 8],
            ["LIST", "", "selectPrinterGroup", group_choices],
            ["FINISH PAGE", "PrinterSelector"],
            ["SPACING", 25],
            ["CREATE PAGE", 0],
            ["LABEL", f"{self.selectedGroup} Settings"],
            ["SPACING", 10],
        ]

        rows.extend(self._profile.build_setting_rows(self.selectedGroup))

        rows.extend([
            ["STRETCH", 1],
            ["FINISH PAGE", "PrinterRows"],
            ["FINISH PAGE", "PrinterRoot"],
        ])

        return rows


class SettingsDisplay(DisplayBase):
    isHorizontal = True
    scrollable = True

    def __init__(self, selectedGroup=None):
        self.settingsProfile = Settings()
        groups = self.settingsProfile.get_group_names()
        if selectedGroup in groups:
            self.selectedGroup = selectedGroup
        elif groups:
            self.selectedGroup = groups[0]
        else:
            self.selectedGroup = ""

    def getAllSettings(self):
        groups = self.settingsProfile.get_group_names()
        if self.selectedGroup not in groups and groups:
            self.selectedGroup = groups[0]

        group_choices = [self.selectedGroup] + [g for g in groups if g != self.selectedGroup]

        rows = [
            ["CREATE PAGE", 1],
            ["CREATE PAGE", 0],
            ["LABEL", "Settings Groups"],
            ["SPACING", 8],
            ["LIST", "", "selectSettingsGroup", group_choices],
            ["FINISH PAGE", "SettingsSelector"],
            ["SPACING", 25],
            ["CREATE PAGE", 0],
            ["LABEL", f"{self.selectedGroup} Settings"],
            ["SPACING", 10],
        ]

        rows.extend(self.settingsProfile.build_setting_rows(self.selectedGroup))

        rows.extend([
            ["STRETCH", 1],
            ["FINISH PAGE", "SettingsRows"],
            ["FINISH PAGE", "SettingsRoot"],
        ])

        return rows

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

    def __init__(self, selectedPrinterName=""):
        self.selectedPrinterName = selectedPrinterName

    def getAllSettings(self):
        selected_printer_text = self.selectedPrinterName if self.selectedPrinterName else "No Printer Selected"

        return [
            ["CREATE PAGE", 0],
            ["FIXED_WIDTH", 360],
            ["LABEL", "Print Settings"],
            ["LABEL", f"Selected Printer: {selected_printer_text}"],
            ["CREATE PAGE", 1],
            ["SELFREF_BUTTON", "Export Gcode", "exportGcode", "exportGcodeButton"],
            ["SELFREF_BUTTON", "Save Gcode", "saveToFile", "saveToFileButton"],
            ["FINISH PAGE", "ButtonPage"],
            ["PROGRESS", "", "progressBar", [0, 100]],
            ["SPACING", 10],
            ["COMBOBOX", "Material Settings:", "material", ["M2 Steel", "M1 Steel", "316L Steel", "1080 Steel"]],
            ["SETTING", "Power:", "power", [1, 100, Printer.power]],
            ["SETTING", "Speed mm/min:", "speed", [1, 10000, Printer.speed]],
            ["SETTING", "Infill:", "infill", [0, 100, Printer.infill]],
            ["COMBOBOX", "Layer Height mm:", "layerHeight", ["0.05", "0.1", "0.15", "0.2", "0.25"]],
            ["UPDATE_LIST", "Print Queue", "selectActor", [""]],

            ["CREATE PAGE", 1],
            ["LABEL", "Position X:"],
            ["ACTOR_SETTING", "", "setActorPosX", [-10000, 10000, 0, 2, 1], "act_pos_x"],
            ["SPACING", 5],
            ["LABEL", "Y:"],
            ["ACTOR_SETTING", "", "setActorPosY", [-10000, 10000, 0, 2, 1], "act_pos_y"],
            ["SPACING", 5],
            ["LABEL", "Z:"],
            ["ACTOR_SETTING", "", "setActorPosZ", [-10000, 10000, 0, 2, 1], "act_pos_z"],
            ["FINISH PAGE", "Actor Pos Row"],

            ["CREATE PAGE", 1],
            ["LABEL", "Rotation X:"],
            ["ACTOR_SETTING", "", "setActorRotX", [-360, 360, 0, 2, 5], "act_rot_x"],
            ["SPACING", 5],
            ["LABEL", "Y:"],
            ["ACTOR_SETTING", "", "setActorRotY", [-360, 360, 0, 2, 5], "act_rot_y"],
            ["SPACING", 5],
            ["LABEL", "Z:"],
            ["ACTOR_SETTING", "", "setActorRotZ", [-360, 360, 0, 2, 5], "act_rot_z"],
            ["FINISH PAGE", "Actor Rot Row"],

            ["CREATE PAGE", 1],
            ["LABEL", "Scale X:"],
            ["ACTOR_SETTING", "", "setActorScaleX", [0.01, 1000, 1, 2, 0.1], "act_scale_x"],
            ["SPACING", 5],
            ["LABEL", "Y:"],
            ["ACTOR_SETTING", "", "setActorScaleY", [0.01, 1000, 1, 2, 0.1], "act_scale_y"],
            ["SPACING", 5],
            ["LABEL", "Z:"],
            ["ACTOR_SETTING", "", "setActorScaleZ", [0.01, 1000, 1, 2, 0.1], "act_scale_z"],
            ["SPACING", 5],
            ["ACTOR_CHECKBOX", "Uniform Scale", "setActorUniformScale", [True], "act_uniform_scale"],
            ["STRETCH", 1],
            ["FINISH PAGE", "Actor Scale Row"],


            ["STRETCH", 1],
            ["FINISH PAGE", "Sidebar"],
            ["SLIDER", 0, ["getVerticalMin", "getVeritcalMax", "getVerticalCurrentValue"]],
            ["CREATE PAGE", 0],
            ["VTK"],
            ["SLIDER", 1, ["getHorizontallMin", "getHorizontalMax", "getHorizontalCurrentValue"]],
            

            ["FINISH PAGE", "VTK Column"],
        ]


currentDisplays = [HomeDisplay(), PrinterDisplay(), SettingsDisplay()]



