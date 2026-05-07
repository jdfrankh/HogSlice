
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QToolBar, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QFrame, QFormLayout, QComboBox,
    QSizePolicy, QMenu, QAction, QShortcut, QLineEdit, QListWidget, QStackedLayout,
    QMessageBox, QScrollArea
)
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QSize, QPoint, QEvent, QThread, pyqtSignal, QObject


from QtWrapper.windowManager import WindowManager
from VulkanWrapper.Printer import Printer
from HogforgeVulkan import HogforgeVulkan
import pageCreator as pg
import json
import os
import sys
import shutil
from runtime_paths import get_runtime_path



#Referece all items concerning your application here
from pageCreator import DisplayBase, SettingsDisplay, PrinterDisplay, TopBarDisplay, HomeDisplay, currentDisplays, PageID
#from slicer import sliceItem

from SlicerWrapper.SlicerManager import SlicerManager

#This page acts as a linker between the window manager, the VTK manager, and all 
#External values accosciated with the slicer 

class HogforgeApplication(WindowManager):

    Printers = ["Hogforge V1", "Hogforge V2"]

    SlicerManager = None 

    currentPrinter = Printer(2,2,2)
    laserWidth = .01 # in mm, for the raycus printer
    progressBar = None

    shaper = None


    def __init__(self):

        layout = super().__init__()

        self.SlicerManager = SlicerManager()

        self.printerProfilesPath = self._printer_profiles_file()
        self.printerProfiles = {}
        self.currentPrinterName = ""
        self._load_profiles_from_file(self.printerProfilesPath)

        self.selectedSettingsGroup = "General"
        self.selectedPrinterGroup = "Bed"
        self.homePageWidget = None
        self.settingsPageWidget = None
        self.printerPageWidget = None
        self.settingsSavePath = self.printerProfilesPath

        #Create top bar layout as it's own unit
        ButtonLayout = self.pageCreation(TopBarDisplay())

        layout.addWidget(ButtonLayout.getPage())

        # Create and store a persistent VulkanManager instance
        self.vtk_manager = HogforgeVulkan(self.currentPrinter.getBedSettings(), self.updatePages)
        #Create the multiple pages
        self.stackedLayout = QStackedLayout()

        for display in pg.currentDisplays:
            if isinstance(display, HomeDisplay):
                display = HomeDisplay(self.currentPrinterName)
            elif isinstance(display, SettingsDisplay):
                display = SettingsDisplay(self.selectedSettingsGroup)
            elif isinstance(display, PrinterDisplay):
                display = PrinterDisplay(list(self.printerProfiles.keys()), self.currentPrinterName, self.selectedPrinterGroup)
            dis = self.pageCreation(display)
            page_widget = dis.getPage()
            self.stackedLayout.addWidget(page_widget)
            if isinstance(display, HomeDisplay):
                self.homePageWidget = page_widget
            elif isinstance(display, SettingsDisplay):
                self.settingsPageWidget = page_widget
            elif isinstance(display, PrinterDisplay):
                self.printerPageWidget = page_widget

        layout.addLayout(self.stackedLayout)

        # Ensure startup visuals always reflect the active printer profile.
        self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())
        self.rebuildRenderer()
        self.vtk_manager.onLeftButtonPress(None, None)
        self.vtk_manager.onLeftButtonRelease(None, None)

    # --- Slider getter/callback methods referenced by pageCreator HomeDisplay ---

    def getVerticalMin(self):
        return 0

    def getVeritcalMax(self):  # matches the typo in pageCreator
        return 0

    def getVerticalCurrentValue(self, value):
        self.vtk_manager.gcodeManager._onLayerChanged(value)

    def getHorizontallMin(self):  # matches the typo in pageCreator
        return 0

    def getHorizontalMax(self):
        return 0

    def getHorizontalCurrentValue(self, value):
        self.vtk_manager.gcodeManager._onLineChanged(value)

    # -------------------------------------------------------------------------

    def changeCurrentPrinter(self, attr, value):
        #print(f"Changing printer setting: {attr} to value: {value}")
        if attr in ("bedHeight", "bedHieght"):
            setattr(self.currentPrinter, "bedHeight", value)
            setattr(self.currentPrinter, "bedHieght", value)
            self.syncSettingWidgets("bedHeight", value)
            self.syncSettingWidgets("bedHieght", value)
            self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())
        else:
            setattr(self.currentPrinter, attr, value)
            self.syncSettingWidgets(attr, value)
            if attr in ("bedWidth", "bedDepth"):
                self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())

        self.rebuildRenderer()
        self._save_profiles_to_file(self.printerProfilesPath)

    def rebuildRenderer(self):
        if self.vtk_manager and self.vtk_manager.getVTKWidget():
            self.vtk_manager.getVTKWidget().GetRenderWindow().Render()


    def saveToFile(self):
        src = get_runtime_path('enviroment.gcode')
        if not os.path.exists(src):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, 'No Gcode', 'No gcode has been generated yet. Please slice first.')
            return
        name = QFileDialog.getSaveFileName(self, 'Save Gcode', '', 'Gcode files (*.gcode)')
        if name[0]:
            shutil.copy2(src, name[0])
            print(f'Gcode saved to {name[0]}')

    def exportGcode(self):
        print("Exporting Gcode with settings:")
        self.exportGcodeButton.setEnabled(False)  # Disable the button to prevent multiple clicks
        print(f"Infill: {self.currentPrinter.infill}")
        print(f"Power: {self.currentPrinter.power}")
        print(f"Speed: {self.currentPrinter.speed}")
        print(f"Layer Height: {self.currentPrinter.layerHeight}")
        self.vtk_manager.getScene()
        infillNormalized = float(self.currentPrinter.infill) / 100.0

        self.progressBar.setValue(0)  # Reset progress bar
        self.thread = QThread()
        self.worker = SlicerWorker(
            get_runtime_path('enviroment.gcode'),
            float(self.currentPrinter.layerHeight),
            infillNormalized,
            self.currentPrinter.power,
            self.currentPrinter.speed,
            self.exportGcodeButton,
            self.currentPrinter.bottomLayers,
            self.currentPrinter.topLayers,
            self.currentPrinter
        )
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.gcodeReady.connect(self.showGcodeEnvironment)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def showGcodeEnvironment(self, gcode_path=None):
        if not gcode_path:
            return
        layers_info = self.vtk_manager.displayGcode(self.currentPrinter)
        max_layer = max(len(layers_info) - 1, 0)
        last_layer_lines = layers_info[-1] if layers_info else 0

        # Retrieve the slider widgets stored by pageCreation.
        layer_slider = getattr(self, "getVerticalCurrentValue_slider", None)
        line_slider = getattr(self, "getHorizontalCurrentValue_slider", None)
        if layer_slider is not None and line_slider is not None:
            layer_slider.blockSignals(True)
            layer_slider.setMaximum(max_layer)
            layer_slider.setValue(max_layer)
            layer_slider.blockSignals(False)

            line_slider.blockSignals(True)
            line_slider.setMaximum(last_layer_lines)
            line_slider.setValue(last_layer_lines)
            line_slider.blockSignals(False)

            # Inject slider refs into gcodeManager so _onLayerChanged/_onLineChanged work
            self.vtk_manager.gcodeManager.setSliders(layer_slider, line_slider)

            # Force display update — sliders were set with blockSignals so valueChanged never fired
            self.vtk_manager.gcodeManager._updateGcodeDisplay(max_layer, last_layer_lines)

            layer_slider.show()
            line_slider.show()

        self.updatePages()
        self.vtk_manager.gcodeManager._updateGcodeDisplay(max_layer, last_layer_lines)



    def savePrinter(self):
        printersDir = self._profiles_dir()
        name = QFileDialog.getSaveFileName(self, 'Save Printer Profile', printersDir, "JSON files (*.json)")
        if name[0]:
            self.currentPrinter.saveToFile(name[0])
            print(f"Printer profile saved to {name[0]}")

    def importPrinter(self):
        printersDir = self._profiles_dir()
        name = QFileDialog.getOpenFileName(self, 'Import Printer Profile', printersDir, "JSON files (*.json)")
        if name[0]:
            try:
                loaded_printer = Printer.loadFromFile(name[0])
                self.printerProfiles[self.currentPrinterName] = loaded_printer
                self.currentPrinter = loaded_printer
                self.currentPrinter.capture_defaults()
                print(f"Printer profile loaded from {name[0]}")
                # Rebuild settings and printer pages to reflect new values
                self.rebuildSettingsPage()
                self.rebuildPrinterPage()
                self.syncAllSettingWidgets()
                self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())
                self._save_profiles_to_file(self.printerProfilesPath)
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to load printer profile:\n{e}")

    def _profiles_dir(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "HogSlice")
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        profiles_dir = os.path.join(base_dir, "Profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        return profiles_dir

    def _printer_profiles_file(self):
        return os.path.join(self._profiles_dir(), "printer_profiles.json")

    def _default_profiles_payload(self):
        fallback_profiles = {}
        for name in self.Printers:
            fallback_profiles[name] = Printer(2, 2, 2).to_settings_dict()

        selected = self.Printers[0] if self.Printers else ""
        return {
            "version": 1,
            "selectedPrinter": selected,
            "printers": fallback_profiles,
        }

    def _serialize_profiles_payload(self):
        return {
            "version": 1,
            "selectedPrinter": self.currentPrinterName,
            "printers": {name: profile.to_settings_dict() for name, profile in self.printerProfiles.items()},
        }

    def _apply_profiles_payload(self, payload):
        printers_data = payload.get("printers", {})
        if not printers_data:
            raise ValueError("No printer profiles found in settings file")

        new_profiles = {}
        default_printer_names = {"Hogforge V1", "Hogforge V2"}
        for name, data in printers_data.items():
            printer = Printer(2, 2, 2.5)
            printer.apply_settings_dict(data)

            # Migrate legacy profiles where topBottomSpacing was set to extrudeWidth
            # (the old default). Reset to layerHeight which is the correct default.
            spacing = float(getattr(printer, "topBottomSpacing", 0.0))
            extrude = float(getattr(printer, "extrudeWidth", 0.71))
            layer = float(getattr(printer, "layerHeight", 0.1))
            if abs(spacing - extrude) < 1e-6 and abs(spacing - layer) > 1e-6:
                printer.topBottomSpacing = layer

            printer.capture_defaults()
            new_profiles[name] = printer

        selected = payload.get("selectedPrinter")
        if selected not in new_profiles:
            selected = next(iter(new_profiles.keys()))

        self.printerProfiles = new_profiles
        self.currentPrinterName = selected
        self.currentPrinter = self.printerProfiles[self.currentPrinterName]
        self.Printers = list(self.printerProfiles.keys())

    def _load_profiles_from_file(self, filepath):
        if not os.path.exists(filepath):
            default_payload = self._default_profiles_payload()
            with open(filepath, "w") as handle:
                json.dump(default_payload, handle, indent=4)
            self._apply_profiles_payload(default_payload)
            return

        with open(filepath, "r") as handle:
            payload = json.load(handle)
        self._apply_profiles_payload(payload)

    def _save_profiles_to_file(self, filepath):
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w") as handle:
            json.dump(self._serialize_profiles_payload(), handle, indent=4)

    def _refresh_settings_views(self):
        self.rebuildHomePage()
        self.rebuildSettingsPage()
        self.rebuildPrinterPage()
        self.syncAllSettingWidgets()
        self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())
        self.rebuildRenderer()
        self._save_profiles_to_file(self.printerProfilesPath)

    def rebuildHomePage(self):
        self.PageList = []
        new_home = self.pageCreation(HomeDisplay(self.currentPrinterName))
        new_widget = new_home.getPage()

        if self.homePageWidget is not None:
            home_index = self.stackedLayout.indexOf(self.homePageWidget)
            if home_index != -1:
                old_widget = self.homePageWidget
                self.stackedLayout.removeWidget(old_widget)
                old_widget.deleteLater()
                self.stackedLayout.insertWidget(home_index, new_widget)
            else:
                self.stackedLayout.addWidget(new_widget)
        else:
            self.stackedLayout.addWidget(new_widget)

        self.homePageWidget = new_widget

    def importSettings(self):
        profiles_dir = self._profiles_dir()
        name = QFileDialog.getOpenFileName(self, 'Import Settings', profiles_dir, "JSON files (*.json)")
        if not name[0]:
            return

        try:
            self._load_profiles_from_file(name[0])
            self.settingsSavePath = name[0]
            self._refresh_settings_views()
            print(f"Settings imported from {name[0]}")
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import settings:\n{e}")

    def exportSettings(self):
        profiles_dir = self._profiles_dir()
        name = QFileDialog.getSaveFileName(self, 'Export Settings', profiles_dir, "JSON files (*.json)")
        if not name[0]:
            return

        try:
            self._save_profiles_to_file(name[0])
            self.settingsSavePath = name[0]
            print(f"Settings exported to {name[0]}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export settings:\n{e}")

    def saveSettings(self):
        try:
            if not self.settingsSavePath:
                default_path = self.printerProfilesPath
                self.settingsSavePath = default_path

            self._save_profiles_to_file(self.settingsSavePath)
            print(f"Settings saved to {self.settingsSavePath}")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save settings:\n{e}")

    def resetToDefaults(self):
        try:
            self.currentPrinter.reset_to_defaults()
            self._refresh_settings_views()
            print("Settings reset to defaults")
        except Exception as e:
            QMessageBox.warning(self, "Reset Error", f"Failed to reset settings:\n{e}")

    def setPage(self, index):

        self.stackedLayout.setCurrentIndex(index)

        #if index == 0:
            #self.vtk_manager.reset()

    def goHome(self):
        self.setPage(PageID.HOMEPAGE)
        self.vtk_manager.onLeftButtonPress(None, None)
        self.vtk_manager.onLeftButtonRelease(None, None)

    def goSettings(self):
        self.setPage(PageID.PRINTERPAGE)

    def goPrinter(self):
        self.setPage(PageID.SETTINGSPAGE)

    def selectPrinterGroup(self, group_name):
        if hasattr(group_name, "text") and callable(group_name.text):
            group_name = group_name.text()

        if not group_name or group_name == self.selectedPrinterGroup:
            return

        old_printer_index = self.stackedLayout.indexOf(self.printerPageWidget)
        was_showing_printer = self.stackedLayout.currentIndex() == old_printer_index

        self.selectedPrinterGroup = group_name
        self.rebuildPrinterPage()

        if was_showing_printer:
            self.stackedLayout.setCurrentWidget(self.printerPageWidget)

    def selectSettingsGroup(self, group_name):
        if hasattr(group_name, "text") and callable(group_name.text):
            group_name = group_name.text()

        if not group_name or group_name == self.selectedSettingsGroup:
            return

        old_settings_index = self.stackedLayout.indexOf(self.settingsPageWidget)
        was_showing_settings = self.stackedLayout.currentIndex() == old_settings_index

        self.selectedSettingsGroup = group_name
        self.rebuildSettingsPage()

        if was_showing_settings:
            self.stackedLayout.setCurrentWidget(self.settingsPageWidget)

    def rebuildSettingsPage(self):
        new_settings = self.pageCreation(SettingsDisplay(self.selectedSettingsGroup))
        new_widget = new_settings.getPage()

        if self.settingsPageWidget is not None:
            settings_index = self.stackedLayout.indexOf(self.settingsPageWidget)
            if settings_index != -1:
                old_widget = self.settingsPageWidget
                self.stackedLayout.removeWidget(old_widget)
                old_widget.deleteLater()
                self.stackedLayout.insertWidget(settings_index, new_widget)
            else:
                self.stackedLayout.addWidget(new_widget)
        else:
            self.stackedLayout.addWidget(new_widget)

        self.settingsPageWidget = new_widget

    def rebuildPrinterPage(self):
        new_printer = self.pageCreation(PrinterDisplay(list(self.printerProfiles.keys()), self.currentPrinterName, self.selectedPrinterGroup))
        new_widget = new_printer.getPage()

        if self.printerPageWidget is not None:
            printer_index = self.stackedLayout.indexOf(self.printerPageWidget)
            if printer_index != -1:
                old_widget = self.printerPageWidget
                self.stackedLayout.removeWidget(old_widget)
                old_widget.deleteLater()
                self.stackedLayout.insertWidget(printer_index, new_widget)
            else:
                self.stackedLayout.addWidget(new_widget)
        else:
            self.stackedLayout.addWidget(new_widget)

        self.printerPageWidget = new_widget

    def selectPrinterProfile(self, printer_name):
        if hasattr(printer_name, "text") and callable(printer_name.text):
            printer_name = printer_name.text()

        if not printer_name or printer_name not in self.printerProfiles:
            return

        if printer_name == self.currentPrinterName:
            return

        self.currentPrinterName = printer_name
        self.currentPrinter = self.printerProfiles[printer_name]

        # Rebuild pages that show printer-backed settings and sync any live widgets.
        self.rebuildHomePage()
        self.rebuildPrinterPage()
        self.rebuildSettingsPage()
        self.syncAllSettingWidgets()
        self.vtk_manager.rebuildBuildChamber(self.currentPrinter.getBedSettings())
        self._save_profiles_to_file(self.printerProfilesPath)
    
    

    def openFile(self):
        print("Open file action triggered")

    
    def dragEnterEvent(self, event):
        
        if event.mimeData().hasUrls():
            #print("Drag event called")
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.stl'):
                    event.acceptProposedAction()
                    return
        event.ignore()

        self.updatePages()

    def dropEvent(self, event):
        #print("Drop event called")

        

        for url in event.mimeData().urls():
           # print("URL: ", url)
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.stl'):
                self.vtk_manager.parseActor(file_path)

                self.vtk_manager.onLeftButtonPress(None, None)
                self.vtk_manager.onLeftButtonRelease(None, None)
            # self.info_label.setText(f"Loaded: {file_path}")
        self.updatePages()

    


    def updatePages(self):
        for page in self.PageList:
            page.update(self.vtk_manager.printActors())
        self.updateActorUI()

    def updateActorUI(self):
        if not hasattr(self, 'act_pos_x'):
            return
            
        selected_actors = [a for a in self.vtk_manager.ActorManager.Actors if a.isSelected]
        if not selected_actors:
            return
            
        # Get the first selected actor
        actor = selected_actors[0]
        
        # Block signals to prevent update feedback loop
        self.act_pos_x.blockSignals(True)
        self.act_pos_y.blockSignals(True)
        self.act_pos_z.blockSignals(True)
        self.act_rot_x.blockSignals(True)
        self.act_rot_y.blockSignals(True)
        self.act_rot_z.blockSignals(True)
        self.act_scale_x.blockSignals(True)
        self.act_scale_y.blockSignals(True)
        self.act_scale_z.blockSignals(True)
        self.act_uniform_scale.blockSignals(True)
        
        pos = actor.actor.GetPosition()
        self.act_pos_x.setValue(pos[0])
        self.act_pos_y.setValue(pos[1])
        self.act_pos_z.setValue(pos[2])
        
        rot = actor.actor.GetOrientation()
        self.act_rot_x.setValue(rot[0])
        self.act_rot_y.setValue(rot[1])
        self.act_rot_z.setValue(rot[2])
        
        scale = actor.actor.GetScale()
        self.act_scale_x.setValue(scale[0])
        self.act_scale_y.setValue(scale[1])
        self.act_scale_z.setValue(scale[2])
        self.act_uniform_scale.setChecked(actor.uniformScale)
        
        self.act_pos_x.blockSignals(False)
        self.act_pos_y.blockSignals(False)
        self.act_pos_z.blockSignals(False)
        self.act_rot_x.blockSignals(False)
        self.act_rot_y.blockSignals(False)
        self.act_rot_z.blockSignals(False)
        self.act_scale_x.blockSignals(False)
        self.act_scale_y.blockSignals(False)
        self.act_scale_z.blockSignals(False)
        self.act_uniform_scale.blockSignals(False)
        self.act_uniform_scale.blockSignals(False)

    def _applyActorTransform(self, type_str, axis, value):
        if not hasattr(self, 'vtk_manager') or not self.vtk_manager or not hasattr(self.vtk_manager, 'ActorManager'):
            return
            
        selected_actors = [a for a in self.vtk_manager.ActorManager.Actors if a.isSelected]
        need_update = False
        for actor in selected_actors:
            if type_str == 'pos':
                pos = list(actor.actor.GetPosition())
                pos[axis] = value
                actor.actor.SetPosition(pos)
                actor.refactorGizmo(self.vtk_manager.selectedMoveType)
            elif type_str == 'rot':
                rot = list(actor.actor.GetOrientation())
                rot[axis] = value
                actor.actor.SetOrientation(rot)
                actor.refactorGizmo(self.vtk_manager.selectedMoveType)
            elif type_str == 'scale':
                scale = list(actor.actor.GetScale())
                if self.act_uniform_scale.isChecked():
                    if scale[axis] != 0:
                        ratio = value / scale[axis]
                        scale = [s * ratio for s in scale]
                    else:
                        scale = [value, value, value]
                    need_update = True
                else:
                    scale[axis] = value
                actor.actor.SetScale(scale)
                actor.refactorGizmo(self.vtk_manager.selectedMoveType)
                
        self.vtk_manager.getVTKWidget().GetRenderWindow().Render()
        if need_update:
            self.updateActorUI()

    def setActorPosX(self, val): self._applyActorTransform('pos', 0, val)
    def setActorPosY(self, val): self._applyActorTransform('pos', 1, val)
    def setActorPosZ(self, val): self._applyActorTransform('pos', 2, val)
    
    def setActorRotX(self, val): self._applyActorTransform('rot', 0, val)
    def setActorRotY(self, val): self._applyActorTransform('rot', 1, val)
    def setActorRotZ(self, val): self._applyActorTransform('rot', 2, val)
    
    def setActorScaleX(self, val): self._applyActorTransform('scale', 0, val)
    def setActorScaleY(self, val): self._applyActorTransform('scale', 1, val)
    def setActorScaleZ(self, val): self._applyActorTransform('scale', 2, val)
    
    def setActorUniformScale(self, state):
        selected_actors = [a for a in self.vtk_manager.ActorManager.Actors if a.isSelected]
        if not selected_actors:
            return
            
        actor = selected_actors[0]
        actor.uniformScale = bool(state)
        
        # If the scale gizmo is currently active, we need to refresh it so it updates visually
        if self.vtk_manager.selectedMoveType == "Scale": 
            actor.refactorGizmo("Scale")
        
        # Manually trigger VTK render since gizmo state changed
        self.vtk_manager.vtkWidget.GetRenderWindow().Render()



# A separate worker is necesarry to handle the slicing process. 
class SlicerWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    gcodeReady = pyqtSignal(str)

    def __init__(self, filename, layerThickness, infillPercent, power, speed, exportButton, bottomLayers=3, topLayers=3, printerProfile=None):
        super().__init__()
        self.filename = filename
        self.layerThickness = layerThickness
        self.infillPercent = infillPercent
        self.power = power
        self.speed = speed
        self.exportButton = exportButton
        self.bottomLayers = bottomLayers
        self.topLayers = topLayers
        self.printerProfile = printerProfile

    def run(self):
        from SlicerWrapper.SlicerManager import SlicerManager
        mgr = SlicerManager()
        mgr.sliceItem(
            self.filename,
            self.layerThickness,
            self.infillPercent,
            self.power,
            self.speed,
            self.topLayers,
            printerProfile=self.printerProfile,
            progressCallback=self.progress.emit
        )
        # Write the G-code file from the freshly sliced layers
        if hasattr(mgr, 'layer_slices') and mgr.layer_slices:
            gcode_path = mgr.writeGcodeFile(mgr.layer_slices, self.filename)
        else:
            gcode_path = self.filename

        self.exportButton.setEnabled(True)  # Re-enable the export button after slicing is done
        if os.path.exists(gcode_path):
            self.gcodeReady.emit(gcode_path)
        else:
            print(f"G-code export did not produce a file: {gcode_path}")
        self.finished.emit()
