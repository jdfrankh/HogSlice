



import json
import os


class Laser:

    id = ""
    laserWattage = 50 # In watts
    focalLens = 240 #mm

    def __init__(self, _id, _wattage, _focal):
        self.id = _id
        self.laserWattage = _wattage
        self.focalLens = _focal



class Printer:

    

    bedWidth = 2
    bedHieght = 2
    bedDepth = 2.5

    sweepTime = 1000
    layerDownTime = 200

    infill = 0 # In percent
    power = 50 # In watts
    focalLength = 240 # In mm
    speed = 100 # In mm/min
    layerHeight = 0.1 # In mm
    laserWidth = 0.01 # in mm, for the raycus printer
    layerHeight = 0.1 # In mm

    material = "M2 Steel"    
    numWalls = 2
    supportInfill = 50.0
    extrudeWidth = 0.71


    offsetx = 0
    offsety = 0

    laser = None

    def __init__(self, _bedWidth, _bedHieght, _bedDepth, _laser= None):
        self.bedWidth = _bedWidth
        self.bedHieght = _bedHieght
        self.bedDepth = _bedDepth
        if _laser:
            self.laser = _laser
        else:
            self.laser = Laser("Raycus 50W", 50, 140)

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
            "power": self.power,
            "speed": self.speed,
            "layerHeight": self.layerHeight,
            "laserWidth": self.laserWidth,
            "material": self.material,
            "numWalls": self.numWalls,
            "supportInfill": self.supportInfill,
            "extrudeWidth": self.extrudeWidth,
            "offsets": list(self.offsets),
            "laser": {
                "id": self.laser.id,
                "laserWattage": self.laser.laserWattage,
                "focalLens": self.laser.focalLens,
            }
        }

    def saveToFile(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.toDict(), f, indent=4)

    @staticmethod
    def loadFromFile(filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        laser_data = data.get("laser", {})
        laser = Laser(
            laser_data.get("id", "Raycus 50W"),
            laser_data.get("laserWattage", 50),
            laser_data.get("focalLens", 140),
        )
        printer = Printer(
            data.get("bedWidth", 2),
            data.get("bedHieght", 2),
            data.get("bedDepth", 2.5),
            _laser=laser,
        )
        for key in ["sweepTime", "layerDownTime", "infill", "power", "speed",
                     "layerHeight", "laserWidth", "material", "numWalls",
                     "supportInfill", "extrudeWidth"]:
            if key in data:
                setattr(printer, key, data[key])
        if "offsets" in data:
            printer.offsets = list(data["offsets"])
        return printer