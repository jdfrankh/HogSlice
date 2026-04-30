
from VulkanWrapper.ConfigProfileBase import ConfigProfileBase


# Density in g/cm³ and default cost in $/g for common SLM/SLS powders.
# Users can override cost per-printer via materialUnitCost.
MATERIAL_PROPERTIES = {
    'M2 Steel':   {'density': 8.16,  'default_cost_per_g': 0.12},
    'M1 Steel':   {'density': 7.85,  'default_cost_per_g': 0.10},
    '316L Steel': {'density': 7.99,  'default_cost_per_g': 0.15},
    '1080 Steel': {'density': 7.83,  'default_cost_per_g': 0.09},
}


class Laser:

    id = ""
    laserWattage = 50 # In watts
    focalLens = 240 #mm

    def __init__(self, _id, _wattage, _focal):
        self.id = _id
        self.laserWattage = _wattage
        self.focalLens = _focal



class Printer(ConfigProfileBase):

    

    bedWidth = 2
    bedHeight = 2
    bedDepth = 2.5

    sweepTime = 1000
    layerDownTime = 200

    infill = 0 # In percent
    infillPattern = "Lines"
    power = 50 # In watts
    focalLength = 240 # In mm
    speed = 100 # In mm/min
    
    laserWidth = 0.01 # in mm, for the raycus printer
    layerHeight = 0.1 # In mm

    layerHeight = 0.1 # In mm
    material = "M2 Steel"
    materialUnitCost = 0.0   # $/g override; 0 = use MATERIAL_PROPERTIES default
    numSideWalls = 2
    supportInfill = 50.0
    extrudeWidth = 0.71
    topBottomSpacing = layerHeight
    topBottomDetectionHeight = 0.5  # mm – gap above/below with no geometry triggers a top/bottom surface
    radialMaxSpacing = 5.0  # mm – max arc gap between adjacent radial lines at perimeter
    bottomLayers = 0.3   # mm thickness of solid bottom walls
    topLayers    = 0.3   # mm thickness of solid top walls


    offsetx = 0
    offsety = 0

    laser = None

    def __init__(self, _bedWidth, _bedHieght, _bedDepth, _laser= None):
        super().__init__()
        self.bedWidth = _bedWidth
        self.bedHieght = _bedHieght
        self.bedDepth = _bedDepth
        if _laser:
            self.laser = _laser
        else:
            self.laser = Laser("Raycus 50W", 50, 140)

        self.capture_defaults()

    def getMaterialDensity(self):
        """Returns density in g/cm³ for the selected material."""
        return MATERIAL_PROPERTIES.get(self.material, {}).get('density', 7.9)

    def getMaterialCostPerGram(self):
        """Returns $/g: uses materialUnitCost override if > 0, else table default."""
        if self.materialUnitCost and float(self.materialUnitCost) > 0:
            return float(self.materialUnitCost)
        return MATERIAL_PROPERTIES.get(self.material, {}).get('default_cost_per_g', 0.10)

    def changeSetting(self, settingName, value):
        if hasattr(self, settingName):
            setattr(self, settingName, value)

    def getBedSettings(self):
        temp = []
        temp.append(self.bedWidth)
        temp.append(self.bedHieght)
        temp.append(self.bedDepth)


        return temp

    def toDict(self):
        return {
            "bedWidth": self.bedWidth,
            "bedHieght": self.bedHieght,
            "bedDepth": self.bedDepth,
            "sweepTime": self.sweepTime,
            "layerDownTime": self.layerDownTime,
            "infill": self.infill,
            "infillPattern": self.infillPattern,
            "power": self.power,
            "speed": self.speed,
            "layerHeight": self.layerHeight,
            "laserWidth": self.laserWidth,
            "material": self.material,
            "numSideWalls": self.numSideWalls,
            "supportInfill": self.supportInfill,
            "extrudeWidth": self.extrudeWidth,
            "topBottomSpacing": self.topBottomSpacing,
            "bottomLayers": self.bottomLayers,
            "topLayers": self.topLayers,
            "offsets": list(self.offsets),
            "laser": {
                "id": self.laser.id,
                "laserWattage": self.laser.laserWattage,
                "focalLens": self.laser.focalLens,
            }
        }

    def saveToFile(self, filepath):
        self.save_settings(filepath)

    @staticmethod
    def loadFromFile(filepath):
        printer = Printer(2, 2, 2.5)
        printer.import_settings(filepath)
        return printer
    

    