

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