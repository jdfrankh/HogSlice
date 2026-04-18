from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QToolBar, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QFrame, QFormLayout, QComboBox,
    QSizePolicy, QMenu, QAction, QShortcut, QLineEdit, QListWidget, QStackedLayout,
    QMessageBox, QScrollArea
)
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QSize, QPoint, QEvent, QThread, pyqtSignal, QObject

from QtWrapper.MenuBarManager import MenuBarManager, MenuBarType
from QtWrapper.pageManger import PageManager, QType

from VulkanWrapper.Printer import Printer

import threading
#from turtleTest import gcodeShaper
from slicer import sliceItem

import sys


from constants import WindowSettings
from pageCreator import DisplayBase, ToolBarDisplay

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

   

    def __init__(self):
        super().__init__()

        self.setWindowTitle(WindowSettings.WindowTitle)
        self.resize(*WindowSettings.windowLayout)

        self.createMenuBar()
        
        # Central widget and layout
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        central.setFixedSize(WindowSettings.windowLayout[0], WindowSettings.windowLayout[1])
        self.setCentralWidget(central)

        self.setAcceptDrops(WindowSettings.acceptDropsSetting)


        
        return layout

        

    def createMenuBar(self):
        menu_bar = self.menuBar()

        for name, items in ToolBarDisplay.__dict__.items():
            if name.startswith("__") or not isinstance(items, list):
                continue
            menu = MenuBarManager(MenuBarType.MENU, name, name, self)
            for entry in items:
                if entry[0] == "Separator":
                    menu.addSeparator()
                else:
                    menu.addWidget(entry[0], getattr(self, entry[1]))
            menu_bar.addMenu(menu.WidgetItem)

    


    
    #Create each page with reference to constants.py
    def pageCreation(self, currentPage, vtkManager=None):

        tempRow = []
        currentDirection = False
        justPopped = False

        page = PageManager(currentPage.isHorizontal)
        currentSettings = currentPage.getAllSettings()

        for setting in currentSettings:
            #print("Current setting: ", setting)
            justPopped = False
            # Add to mini page if neceassary
            if tempRow == []:
                row = PageManager(currentDirection)
            else:
                row = tempRow[len(tempRow) - 1]

            if setting[DisplayBase.QTTYPE] == "SETTING":
                
                row.createElement(elementType=QType.LABEL, layoutType=0, displayText=setting[DisplayBase.SHOWNAME])
                if isinstance(setting[ DisplayBase.LISTELEMENT], list):
                    box = row.createElement(elementType=QType.BOX, layoutType=0,
                        function=lambda value, s=setting: self.currentPrinter.changeSetting(s[DisplayBase.FUNCTIONELEMENT], value),
                        displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT])

            elif setting[DisplayBase.QTTYPE] == "BUTTON":
                row.createElement(elementType=QType.BUTTON, layoutType=0,
                    function=getattr(self, setting[DisplayBase.FUNCTIONELEMENT]), displayText=setting[DisplayBase.SHOWNAME])

            elif setting[DisplayBase.QTTYPE] == "LABEL":
                row.createElement(elementType=QType.LABEL, layoutType=0, displayText=setting[DisplayBase.SHOWNAME])

            elif setting[DisplayBase.QTTYPE] == "SPACING":

                row.addSpacing(layoutType=0, spacing=setting[DisplayBase.SHOWNAME])

            
            elif setting[DisplayBase.QTTYPE] == "LIST":
                row.createElement(elementType=QType.LIST, layoutType=0,
                    function=lambda value, s=setting: self.currentPrinter.changeSetting(s[DisplayBase.FUNCTIONELEMENT], value.text()),
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT] )

            elif setting[DisplayBase.QTTYPE] == "COMBOBOX":
                row.createElement(elementType=QType.COMBOBOX, layoutType=0,
                    function=lambda value, s=setting: self.currentPrinter.changeSetting(s[DisplayBase.FUNCTIONELEMENT], value),
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT])

            elif setting[DisplayBase.QTTYPE] == "PROGRESS":
                item = row.createElement(elementType=QType.PROGRESS, layoutType=0,
                    listElements=setting[DisplayBase.LISTELEMENT], function=None, displayText="")
                if len(setting) > DisplayBase.FUNCTIONELEMENT and setting[DisplayBase.FUNCTIONELEMENT]:
                    setattr(self, setting[DisplayBase.FUNCTIONELEMENT], item)

            elif setting[DisplayBase.QTTYPE] == "SELFREF_BUTTON":
                item = row.createElement(elementType=QType.BUTTON, layoutType=0,
                    function=getattr(self, setting[DisplayBase.FUNCTIONELEMENT]), displayText=setting[DisplayBase.SHOWNAME])
                if len(setting) > DisplayBase.LISTELEMENT and setting[DisplayBase.LISTELEMENT]:
                    setattr(self, setting[DisplayBase.LISTELEMENT], item)

            elif setting[DisplayBase.QTTYPE] == "UPDATE_LIST":
                row.createElement(elementType=QType.LIST, layoutType=0,
                    function=lambda value, s=setting: self.vtk_manager.selectActorById(value.text()),
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT],
                    updateFunction=1)
                self.PageList.append(row)

            elif setting[DisplayBase.QTTYPE] == "VTK":
                row.addPage(self.vtk_manager.vtkWidget)
                

            elif setting[DisplayBase.QTTYPE] == "CREATE PAGE":
                print("Adding new Row: ", setting[DisplayBase.SHOWNAME])
                tempRow.append(PageManager(setting[DisplayBase.SHOWNAME]))
            
            elif setting[DisplayBase.QTTYPE] == "FINISH PAGE":
                if tempRow != []:
                    finished = tempRow.pop()
                    if tempRow:
                        tempRow[-1].addPage(finished.getPage())
                    else:
                        page.addPage(finished.getPage())
                    justPopped = True
            #print(tempRow)
            if tempRow == [] and justPopped == False:
                print("Adding row to page: ", row)
                page.addPage(row.getPage())   
            
    

        if currentPage.scrollable:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page.getPage())
            wrapper = PageManager(0)
            wrapper.addPage(scroll)
            return wrapper

        return page


    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindowManager()
    window.show()
    sys.exit(app.exec_())




