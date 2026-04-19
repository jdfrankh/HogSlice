
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



#Referece all items concerning your application here
from pageCreator import DisplayBase, SettingsDisplay, PrinterDisplay, TopBarDisplay, HomeDisplay, currentDisplays, PageID
from slicer import sliceItem

#This page acts as a linker between the window manager, the VTK manager, and all 
#External values accosciated with the slicer 

class HogforgeApplication(WindowManager):

    Printers = ["Hogforge Printer"]

    currentPrinter = Printer(2,2,2)
    laserWidth = .01 # in mm, for the raycus printer
    progressBar = None

    shaper = None


    def __init__(self):

        layout = super().__init__()

        #Create top bar layout as it's own unit
        ButtonLayout = self.pageCreation(TopBarDisplay())

        layout.addWidget(ButtonLayout.getPage())

        # Create and store a persistent VulkanManager instance
        self.vtk_manager = HogforgeVulkan(self.currentPrinter.getBedSettings(), self.updatePages)

        self.vtk_manager.onLeftButtonPress(None, None)
        #Create the multiple pages
        self.stackedLayout = QStackedLayout()

        for display in pg.currentDisplays:
            dis = self.pageCreation(display)
            self.stackedLayout.addWidget(dis.getPage())

        layout.addLayout(self.stackedLayout)

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
        setattr(self.currentPrinter, attr, value)


    def saveToFile(self):
        name = QFileDialog.getSaveFileName(self, 'Save Gcode', '', "Gcode files (*.gcode)")

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
        self.worker = SlicerWorker('enviroment.gcode', float(self.currentPrinter.layerHeight), infillNormalized, self.currentPrinter.power, self.currentPrinter.speed, self.exportGcodeButton, self.currentPrinter.bottomLayers, self.currentPrinter.topLayers)
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.gcodeReady.connect(self.showGcodeEnvironment)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def showGcodeEnvironment(self):
        layers_info = self.vtk_manager.displayGcode(self.currentPrinter)
        max_layer = max(len(layers_info) - 1, 0)
        last_layer_lines = layers_info[-1] if layers_info else 0

        # Retrieve the slider widgets stored by pageCreation via setattr
        layer_slider = self.getVerticalCurrentValue    # QSlider (vertical, layers)
        line_slider = self.getHorizontalCurrentValue  # QSlider (horizontal, lines)

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

        layer_slider.show()
        line_slider.show()

        self.updatePages()
        self.vtk_manager.gcodeManager._updateGcodeDisplay(max_layer, last_layer_lines)



    def savePrinter(self):
        import os
        printersDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Printers")
        name = QFileDialog.getSaveFileName(self, 'Save Printer Profile', printersDir, "JSON files (*.json)")
        if name[0]:
            self.currentPrinter.saveToFile(name[0])
            print(f"Printer profile saved to {name[0]}")

    def importPrinter(self):
        import os
        printersDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Printers")
        name = QFileDialog.getOpenFileName(self, 'Import Printer Profile', printersDir, "JSON files (*.json)")
        if name[0]:
            try:
                self.currentPrinter = Printer.loadFromFile(name[0])
                print(f"Printer profile loaded from {name[0]}")
                # Rebuild settings and printer pages to reflect new values
                self.stackedLayout.removeWidget(self.stackedLayout.widget(2))
                self.stackedLayout.removeWidget(self.stackedLayout.widget(1))
                newSettings = self.pageCreation(SettingsDisplay())
                self.stackedLayout.insertWidget(1, newSettings.getPage())
                newPrinter = self.pageCreation(PrinterDisplay())
                self.stackedLayout.insertWidget(2, newPrinter.getPage())
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to load printer profile:\n{e}")

    def setPage(self, index):

        self.stackedLayout.setCurrentIndex(index)

        #if index == 0:
            #self.vtk_manager.reset()

    def goHome(self):
        self.setPage(PageID.HOMEPAGE)

    def goSettings(self):
        self.setPage(PageID.SETTINGSPAGE)

    def goPrinter(self):
        self.setPage(PageID.PRINTERPAGE)
    
    

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
            # self.info_label.setText(f"Loaded: {file_path}")
        self.updatePages()

    

    def updatePages(self):
        for page in self.PageList:
            #print(page.elements)
            page.update(self.vtk_manager.printActors())   


# A separate worker is necesarry to handle the slicing process. 
class SlicerWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    gcodeReady = pyqtSignal(str)

    def __init__(self, filename, layerThickness, infillPercent, power, speed, exportButton, bottomLayers=3, topLayers=3):
        super().__init__()
        self.filename = filename
        self.layerThickness = layerThickness
        self.infillPercent = infillPercent
        self.power = power
        self.speed = speed
        self.exportButton = exportButton
        self.bottomLayers = bottomLayers
        self.topLayers = topLayers

    def run(self):
        sliceItem(self.filename, self.layerThickness, self.infillPercent, self.power, self.speed, self.bottomLayers, self.topLayers, progressCallback=self.progress.emit)
        self.exportButton.setEnabled(True)  # Re-enable the export button after slicing is done
        gcode_path =   self.filename
        self.gcodeReady.emit(gcode_path)
        self.finished.emit()
