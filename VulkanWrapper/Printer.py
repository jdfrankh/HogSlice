

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

    offsets = [0,0,0] #x,y,z

    laser = None

    def __init__(self, _bedWidth, _bedHieght, _bedDepth, _laser= None):
        self.bedWidth = _bedWidth
        self.bedHieght = _bedHieght
        self.bedDepth = _bedDepth
        if _laser:
            self.laser = _laser
        else:
            self.laser = Laser("Raycus 50W", 50, 140)

    def getBedSettings(self):
        temp = []
        temp.append(self.bedWidth)
        temp.append(self.bedHieght)
        temp.append(self.bedWidth)

        return temp