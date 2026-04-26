

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


class AppTheme:
    """
    Centralised Qt stylesheet and window-chrome settings for Hogforge.
    Edit the variables below to restyle the entire application at once.
    """

    # --- Palette ---
    colorBackground     = "#1e1e2e"   # main window / widget background
    colorSurface        = "#2a2a3e"   # panels, group boxes, inputs
    colorBorder         = "#44445a"   # outlines, separators
    colorAccent         = "#7c7cff"   # highlight / selection colour
    colorAccentHover    = "#9d9dff"
    colorAccentPressed  = "#5a5adf"
    colorText           = "#e0e0f0"   # primary text
    colorTextMuted      = "#8888aa"   # labels, placeholders
    colorScrollbar      = "#44445a"

    # --- Typography ---
    fontFamily   = "Segoe UI, Arial, sans-serif"
    fontSizeBase  = "15px"
    fontSizeSmall = "14px"

    # --- Geometry (scale with font size) ---
    borderRadius   = "5px"
    inputHeight    = "34px"
    buttonPadding  = "6px 18px"
    spinboxArrowWidth = "20px"
    comboArrowWidth   = "24px"
    listItemPadding   = "4px"
    progressMinHeight = "18px"
    scrollbarThick    = "10px"
    scrollbarHandle   = "5px"
    scrollHandleMin   = "24px"
    sliderGrooveH     = "5px"
    sliderHandleSize  = "15px"
    sliderHandleRadius = "7px"
    sliderHandleMargin = "-5px"
    checkboxSize       = "17px"
    checkboxRadius     = "4px"
    checkboxSpacing    = "8px"
    menuPadding        = "3px 6px"

    @classmethod
    def stylesheet(cls) -> str:
        """Return the complete Qt stylesheet string."""
        return f"""
/* ── Global ─────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {cls.colorBackground};
    color: {cls.colorText};
    font-family: {cls.fontFamily};
    font-size: {cls.fontSizeBase};
}}

/* ── Menu bar ────────────────────────────────────────────── */
QMenuBar {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border-bottom: 1px solid {cls.colorBorder};
    padding: {cls.menuPadding};
}}
QMenuBar::item:selected {{
    background-color: {cls.colorAccent};
    border-radius: {cls.borderRadius};
}}
QMenu {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border: 1px solid {cls.colorBorder};
}}
QMenu::item:selected {{
    background-color: {cls.colorAccent};
}}
QMenu::separator {{
    height: 1px;
    background: {cls.colorBorder};
    margin: 3px 8px;
}}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.borderRadius};
    padding: {cls.buttonPadding};
    min-height: {cls.inputHeight};
}}
QPushButton:hover {{
    background-color: {cls.colorAccentHover};
    border-color: {cls.colorAccent};
    color: {cls.colorBackground};
}}
QPushButton:pressed {{
    background-color: {cls.colorAccentPressed};
}}
QPushButton:disabled {{
    color: {cls.colorTextMuted};
    border-color: {cls.colorBorder};
}}

/* ── Inputs (spinbox, lineedit) ──────────────────────────── */
QDoubleSpinBox, QLineEdit {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.borderRadius};
    padding: 2px 6px;
    min-height: {cls.inputHeight};
    selection-background-color: {cls.colorAccent};
}}
QDoubleSpinBox:focus, QLineEdit:focus {{
    border-color: {cls.colorAccent};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {cls.colorBorder};
    border: none;
    width: {cls.spinboxArrowWidth};
}}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {cls.colorAccent};
}}

/* ── ComboBox ────────────────────────────────────────────── */
QComboBox {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.borderRadius};
    padding: 2px 6px;
    min-height: {cls.inputHeight};
}}
QComboBox:focus {{
    border-color: {cls.colorAccent};
}}
QComboBox QAbstractItemView {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    selection-background-color: {cls.colorAccent};
    border: 1px solid {cls.colorBorder};
}}
QComboBox::drop-down {{
    border: none;
    width: {cls.comboArrowWidth};
}}

/* ── List widget ─────────────────────────────────────────── */
QListWidget {{
    background-color: {cls.colorSurface};
    color: {cls.colorText};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.borderRadius};
    padding: {cls.listItemPadding};
    font-size: {cls.fontSizeSmall};
}}
QListWidget::item:selected {{
    background-color: {cls.colorAccent};
    color: {cls.colorBackground};
}}
QListWidget::item:hover {{
    background-color: {cls.colorAccentHover};
    color: {cls.colorBackground};
}}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {{
    color: {cls.colorText};
    font-size: {cls.fontSizeSmall};
}}

/* ── Progress bar ────────────────────────────────────────── */
QProgressBar {{
    background-color: {cls.colorSurface};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.borderRadius};
    text-align: center;
    color: {cls.colorText};
    min-height: {cls.progressMinHeight};
}}
QProgressBar::chunk {{
    background-color: {cls.colorAccent};
    border-radius: {cls.borderRadius};
}}

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {cls.colorBackground};
    width: {cls.scrollbarThick};
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {cls.colorScrollbar};
    border-radius: {cls.scrollbarHandle};
    min-height: {cls.scrollHandleMin};
}}
QScrollBar::handle:vertical:hover {{
    background: {cls.colorAccent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {cls.colorBackground};
    height: {cls.scrollbarThick};
}}
QScrollBar::handle:horizontal {{
    background: {cls.colorScrollbar};
    border-radius: {cls.scrollbarHandle};
    min-width: {cls.scrollHandleMin};
}}
QScrollBar::handle:horizontal:hover {{
    background: {cls.colorAccent};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Scroll area ─────────────────────────────────────────── */
QScrollArea {{
    border: none;
}}

/* ── Slider ──────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: {cls.sliderGrooveH};
    background: {cls.colorBorder};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {cls.colorAccent};
    border: none;
    width: {cls.sliderHandleSize};
    height: {cls.sliderHandleSize};
    margin: {cls.sliderHandleMargin} 0;
    border-radius: {cls.sliderHandleRadius};
}}
QSlider::groove:vertical {{
    width: {cls.sliderGrooveH};
    background: {cls.colorBorder};
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    background: {cls.colorAccent};
    border: none;
    width: {cls.sliderHandleSize};
    height: {cls.sliderHandleSize};
    margin: 0 {cls.sliderHandleMargin};
    border-radius: {cls.sliderHandleRadius};
}}

/* ── Checkbox ────────────────────────────────────────────── */
QCheckBox {{
    color: {cls.colorText};
    spacing: {cls.checkboxSpacing};
}}
QCheckBox::indicator {{
    width: {cls.checkboxSize};
    height: {cls.checkboxSize};
    border: 1px solid {cls.colorBorder};
    border-radius: {cls.checkboxRadius};
    background: {cls.colorSurface};
}}
QCheckBox::indicator:checked {{
    background: {cls.colorAccent};
    border-color: {cls.colorAccent};
}}
"""

