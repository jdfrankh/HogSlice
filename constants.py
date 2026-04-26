

class WindowSettings:
    WindowTitle = "Hogforge Slicer"
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

class moverOverlayPositions:

    OverlayScreenLocation = [
        [0.10, 0.10, 0],
        [0.90, 0.10, 0],
        [0.90, 0, 0.0],
        [0.10,0,0]

    ]

    buttonSize = [0.035, 0.035] # normalized width (height dynamically flexes to stay geometrically square)
    
    # We will position them smoothly across the bottom.
    TranslateButtonCenter = [0.25, 0.08]
    RotateButtonCenter = [0.4, 0.08]
    ScaleButtonCenter = [0.55, 0.08]
    SetFlatButtonCenter = [0.7, 0.08]
    
    TranslateButton = [TranslateButtonCenter, buttonSize]
    RotateButton = [RotateButtonCenter, buttonSize]
    ScaleButton = [ScaleButtonCenter, buttonSize]
    SetFlatButton = [SetFlatButtonCenter, buttonSize]


class GcodeInformerPositions:

    #Top left to corner
    cornerDistance = .75

    OverlayScreenLocation = [
        [1, 1, 0],
        [cornerDistance, 1, 0],
        [1, cornerDistance, 0.0],
        [cornerDistance, cornerDistance ,0]

    ]

    WallDisplayLocation = [800, 200]
    InfillDisplayLocation = [800, 175]
    SupportDisplayLocation = [800, 150]
    TotalFillDisplayLocation = [800, 125]
    TimeToCompleteLocation = [800, 100]

class BuildChamberDisplay:
    wallThickess = .1

    displayOrigin = True

    backgroundColor1 = (0.1, 0.1, 0.1) # bottom color
    backgroundColor2 = (0.3, 0.3, 0.3) # top color

