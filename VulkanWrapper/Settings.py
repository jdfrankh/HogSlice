from VulkanWrapper.ConfigProfileBase import ConfigProfileBase
from VulkanWrapper.Printer import Printer


class Settings(ConfigProfileBase):
    """Holds grouped settings metadata used to build the Settings page."""

    def __init__(self):
        super().__init__()

        self.add_group("Front Page", [
            self.make_combobox("Material Settings:", "material", ["M2 Steel", "M1 Steel", "316L Steel", "1080 Steel"]),
            self.make_setting("Power:", "power", [1, 100, Printer.power, 0, 1]),
            self.make_setting("Speed mm/min:", "speed", [1, 10000, Printer.speed, 0, 1]),
            self.make_setting("Infill:", "infill", [0, 100, Printer.infill, 0, 1]),
            self.make_combobox("Infill Pattern:", "infillPattern", ["Lines", "Radial", "Honeycomb"]),
            self.make_combobox("Layer Height mm:", "layerHeight", ["0.05", "0.1", "0.15", "0.2", "0.25"]),
        ])

        self.add_group("General", [
            self.make_setting("Number of Side Walls:", "numSideWalls", [1, 200, Printer.numSideWalls, 0, 1]),
            self.make_setting("Support Infill %:", "supportInfill", [0, 100, Printer.supportInfill, 1, 5.0]),
            self.make_setting("Extrude Width (mm):", "extrudeWidth", [0.01, 5.0, Printer.extrudeWidth, 2, 0.01]),
            self.make_setting("Laser Width (mm):", "laserWidth", [0.001, 1.0, Printer.laserWidth, 3, 0.001]),
            self.make_setting("Sweep Time (ms):", "sweepTime", [0, 10000, Printer.sweepTime, 0, 50]),
            self.make_setting("Layer Down Time (ms):", "layerDownTime", [0, 10000, Printer.layerDownTime, 0, 50]),
        ])

        self.add_group("Top and Bottom", [
            self.make_setting("Bottom Wall Thickness (mm):", "bottomLayers", [0.0, 10.0, Printer.bottomLayers, 2, 0.05]),
            self.make_setting("Top Wall Thickness (mm):",    "topLayers",    [0.0, 10.0, Printer.topLayers,    2, 0.05]),
            self.make_setting("Top/Bottom Wall Spacing (mm):", "topBottomSpacing", [0.01, 5.0, Printer.topBottomSpacing, 3, 0.01]),
            self.make_setting("Surface Detection Height (mm):", "topBottomDetectionHeight", [0.05, 10.0, Printer.topBottomDetectionHeight, 2, 0.05]),
        ])

        self.add_group("Radial Infill", [
            self.make_setting("Max Radial Spacing (mm):", "radialMaxSpacing", [0.001, 50.0, Printer.radialMaxSpacing, 3, 0.001]),
        ])

        self.add_group("Material", [
            self.make_setting("Unit Cost ($/g):", "materialUnitCost", [0.0, 1000.0, 0.0, 4, 0.001]),
        ])
