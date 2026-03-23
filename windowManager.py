from PyQt5.QtWidgets import (
    QApplication, QToolBar, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QFrame, QFormLayout, QComboBox,
    QSizePolicy, QMenu, QAction, QShortcut, QLineEdit, QListWidget, QStackedLayout
)
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QSize, QPoint, QEvent

from QtWrapper.MenuBarManager import MenuBarManager, MenuBarType
from QtWrapper.pageManger import PageManager, QType
from VulkanWrapper.vulkanManager import VulkanManager
from VulkanWrapper.Printer import Printer

from turtleTest import gcodeShaper

import sys


#TODO:
"""
linking system from vtk to QWidgets to determine undos and redos
Integrate the saving functionality here, in which saves the configuration in all Q components,
    as well as vtk elements




"""

#QT Window will manage the entirety of button control -
#as well as contain a vtk element for the window.
# It will also house a settings library than manages the settings
# for the laser, chamber, etc 


class WindowManager(QMainWindow):

    PageList = []

    WindowPages = ["Home", "Settings", "Printer"] 

    Printers = ["Hogforge Printer"]

    currentPrinter = Printer(2,2,2)
    laserWidth = .01 # in mm, for the raycus printer

    shaper = None

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hogforge Slicer")
        self.resize(1460,1080)

        self.createMenuBar()
        
        # Central widget and layout
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.setAcceptDrops(True)

        # Create the top bar
        ButtonLayout = self.topBarCreation()

        layout.addWidget(ButtonLayout.getPage())

        # Create and store a persistent VulkanManager instance
        self.vtk_manager = VulkanManager(self.currentPrinter.getBedSettings(), self.updatePages)

        self.vtk_manager.onLeftButtonPress(None, None)
        #Create the multiple pages
        self.stackedLayout = QStackedLayout()

        HomePage = self.homePageCreation(self.vtk_manager)
        self.stackedLayout.addWidget(HomePage)
        #Reset the vtk manager to ensure the build chamber is created and rendered
        #self.vtk_manager.reset()
        SettingsPage = self.settingsPageCreation()

        self.stackedLayout.addWidget(SettingsPage.getPage())

        PrinterPage = self.printerPageCreation()

        self.shaper = gcodeShaper()

        #add settings and printer pages here later
        self.stackedLayout.addWidget(PrinterPage.getPage())

        layout.addLayout(self.stackedLayout)

        

    def createMenuBar(self):
        # Your WidgetManager menu, now with parent
        menu_bar = self.menuBar()

        fileMenu = MenuBarManager(MenuBarType.MENU, "fileMenu", "File", self)
        fileMenu.addWidget("Open", self.openFile)
        menu_bar.addMenu(fileMenu.WidgetItem)

    def changeCurrentPrinter(self, attr, value):
        print(f"Changing printer setting: {attr} to value: {value}")
        setattr(self.currentPrinter, attr, value)

        

    # ----------------------------- Create Page 1 -----------------------------

    def homePageCreation(self, vtk_manager):
        # Home page will contain the VTK display element -as well as a side bar
        miniLayout = QHBoxLayout()

        
        miniLayout.addWidget(vtk_manager.vtkWidget)

    
        
        materialLabel = PageManager(1)
        materialLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Material Settings:")
        materialLabel.createElement(elementType=QType.COMBOBOX, layoutType=0, function=lambda value: self.changeCurrentPrinter("material", value), displayText="Select Printer", listElements=["M2 Steel", "M1 Steel", "316L Steel", "1080 Steel"])

        infillLabel = PageManager(1)
        infillLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Infill:")
        infillLabel.createElement(elementType=QType.BOX, layoutType=0, function=lambda value: self.changeCurrentPrinter("infill", value), displayText="Infill:")

        powerLabel = PageManager(1)
        powerLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Power:")
        powerLabel.createElement(elementType=QType.BOX, layoutType=0, function=lambda value: self.changeCurrentPrinter("power", value), displayText="Power:")

        speedLabel = PageManager(1)
        speedLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Speed mm/min:")
        speedLabel.createElement(elementType=QType.BOX, layoutType=0, function=lambda value: self.changeCurrentPrinter("speed", value), displayText="Speed:")

        layerHeightLabel = PageManager(1)
        layerHeightLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Layer Height mm:")
        layerHeightLabel.createElement(elementType=QType.COMBOBOX, layoutType=0, function=lambda value: self.changeCurrentPrinter("layerHeight", value), displayText="Select Material", listElements= ["0.05", "0.1", "0.15", "0.2", "0.25"])


        printerLabel = PageManager(1)
        printerLabel.createElement(elementType=QType.LABEL, layoutType=0, displayText="Printers:")
        printerLabel.createElement(elementType=QType.COMBOBOX, layoutType=0, function=lambda value: print(f"Combobox changed to: {value}"), displayText="Select Material", listElements= self.Printers)

        page2 = PageManager(0)  # Vertical layout for side bar
        page2.createElement(elementType=QType.LABEL, layoutType=0, displayText="Print Settings")
        page2.createElement(elementType=QType.BUTTON, layoutType=0, function=lambda: self.shaper.run_mesh(self.currentPrinter.infill, self.currentPrinter.power, self.currentPrinter.speed, self.currentPrinter.laserWidth, self.currentPrinter.layerHeight), displayText="Export to File" )
        page2.addSpacing(layoutType=0, spacing=10)

        page2.addPage(materialLabel.getPage())
        page2.addPage(powerLabel.getPage())
        page2.addPage(speedLabel.getPage())
        page2.addPage(infillLabel.getPage())
        page2.addPage(printerLabel.getPage())
        page2.addPage(layerHeightLabel.getPage())


        page2.createElement(elementType=QType.LIST, layoutType=0, function=lambda value: self.vtk_manager.selectActorById(value.text()), displayText="Print Queue", listElements= [""], updateFunction=1)
        #page2.createElement(elementType=QType.COMBOBOX, layoutType=0, function=lambda value: print(f"Combobox changed to: {value}"), displayText="Select Printer", listEleements=["M2 Steel", "M1 Steel", "316L Steel", "1080 Steel"])
        #page2.createElement(elementType=QType.COMBOBOX, layoutType=0, function=lambda value: print(f"Combobox changed to: {value}"), displayText="Select Material", listEleements= [str(i) for i in range(0,100,10)])

        page2.setWidth(300)

        self.PageList.append(page2)
        #self.PageList.append(materialLabel)
        #self.PageList.append(infillLabel)
        #self.PageList.append(printerLabel)
        #self.PageList.append(layerHeightLabel)

        miniLayout.addWidget(page2.getPage())

        # Wrap in a QWidget for stacking
        container = QWidget()
        container.setLayout(miniLayout)
        return container

    def topBarCreation(self):

        page = PageManager(1)

        #for i in range(len(self.WindowPages)):
        #    print(i)
        #    page.createElement(elementType=QType.BUTTON, layoutType=0, function=lambda: self.setPage(i), displayText=self.WindowPages[i])

        page.createElement(elementType=QType.BUTTON, layoutType=0, function=lambda: self.setPage(0), displayText="Home")
        page.addSpacing(layoutType=0, spacing=20)
        page.createElement(elementType=QType.BUTTON, layoutType=0, function=lambda: self.setPage(1), displayText="Settings")
        page.addSpacing(layoutType=0, spacing=20)
        page.createElement(elementType=QType.BUTTON, layoutType=0, function=lambda: self.setPage(2), displayText="Printer")
        page.addSpacing(layoutType=0, spacing=1000)

        page.setWidth(1460)

        #self.PageList.append(page)

        return page 


    def settingsPageCreation(self):
        
        page = PageManager(0) # Vertical layout

        page.createElement(elementType=QType.LABEL, layoutType=0, displayText="Settings Page - Under Construction")

        #self.PageList.append(page)

        return page

    def printerPageCreation(self):
        
        page = PageManager(0) # Vertical layout

        page.createElement(elementType=QType.LABEL, layoutType=0, displayText="Printer Page - Under Construction")

        return page

    def setPage(self, index):

        self.stackedLayout.setCurrentIndex(index)

        #if index == 0:
            #self.vtk_manager.reset()
    
    

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowManager()
    window.show()
    sys.exit(app.exec_())