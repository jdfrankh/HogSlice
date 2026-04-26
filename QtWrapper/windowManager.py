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


import sys


from constants import WindowSettings, AppTheme
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

        self.settingWidgets = {}

        self.setWindowTitle(WindowSettings.WindowTitle)
        self.resize(*WindowSettings.windowLayout)
        self.setStyleSheet(AppTheme.stylesheet())

        self.createMenuBar()
        
        # Central widget and layout
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        # Avoid fixed size so the central widget flexes with the window resize
        self.setCentralWidget(central)

        self.setAcceptDrops(WindowSettings.acceptDropsSetting)


        
        return layout

    def _registerSettingWidget(self, attr_name, widget, widget_type):
        if not attr_name or widget is None:
            return
        if attr_name not in self.settingWidgets:
            self.settingWidgets[attr_name] = []
        self.settingWidgets[attr_name].append((widget, widget_type))

    def _updatePrinterSetting(self, attr_name, value):
        if hasattr(self, "changeCurrentPrinter") and callable(getattr(self, "changeCurrentPrinter")):
            self.changeCurrentPrinter(attr_name, value)
        else:
            self.currentPrinter.changeSetting(attr_name, value)

    def syncSettingWidgets(self, attr_name, value):
        if attr_name not in self.settingWidgets:
            return

        alive_widgets = []
        for widget, widget_type in self.settingWidgets[attr_name]:
            try:
                if widget_type == QType.BOX:
                    numeric_value = float(value)
                    if widget.value() != numeric_value:
                        widget.blockSignals(True)
                        widget.setValue(numeric_value)
                        widget.blockSignals(False)
                elif widget_type == QType.COMBOBOX:
                    text_value = str(value)
                    if widget.currentText() != text_value:
                        widget.blockSignals(True)
                        index = widget.findText(text_value)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                        widget.blockSignals(False)

                alive_widgets.append((widget, widget_type))
            except RuntimeError:
                continue

        self.settingWidgets[attr_name] = alive_widgets

    def syncAllSettingWidgets(self):
        for attr_name in list(self.settingWidgets.keys()):
            if hasattr(self.currentPrinter, attr_name):
                self.syncSettingWidgets(attr_name, getattr(self.currentPrinter, attr_name))

        

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
                if isinstance(setting[DisplayBase.LISTELEMENT], list):
                    list_elements = list(setting[DisplayBase.LISTELEMENT])
                    attr_name = setting[DisplayBase.FUNCTIONELEMENT]
                    if hasattr(self.currentPrinter, attr_name) and len(list_elements) > 2:
                        list_elements[2] = getattr(self.currentPrinter, attr_name)

                    box = row.createElement(elementType=QType.BOX, layoutType=0,
                        function=lambda value, s=setting: self._updatePrinterSetting(s[DisplayBase.FUNCTIONELEMENT], value),
                        displayText=setting[DisplayBase.SHOWNAME], listElements=list_elements)
                    self._registerSettingWidget(attr_name, box, QType.BOX)

            elif setting[DisplayBase.QTTYPE] == "BUTTON":
                row.createElement(elementType=QType.BUTTON, layoutType=0,
                    function=getattr(self, setting[DisplayBase.FUNCTIONELEMENT]), displayText=setting[DisplayBase.SHOWNAME])

            elif setting[DisplayBase.QTTYPE] == "LABEL":
                row.createElement(elementType=QType.LABEL, layoutType=0, displayText=setting[DisplayBase.SHOWNAME])

            elif setting[DisplayBase.QTTYPE] == "SPACING":
                row.addSpacing(layoutType=0, spacing=setting[DisplayBase.SHOWNAME])

            elif setting[DisplayBase.QTTYPE] == "STRETCH":
                row.addStretch(1)

            
            elif setting[DisplayBase.QTTYPE] == "LIST":
                callback_name = setting[DisplayBase.FUNCTIONELEMENT]
                if hasattr(self, callback_name) and callable(getattr(self, callback_name)):
                    callback = getattr(self, callback_name)
                else:
                    callback = lambda value, s=setting: self._updatePrinterSetting(s[DisplayBase.FUNCTIONELEMENT], value.text())
                row.createElement(elementType=QType.LIST, layoutType=0,
                    function=callback,
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT] )

            elif setting[DisplayBase.QTTYPE] == "COMBOBOX":
                callback_name = setting[DisplayBase.FUNCTIONELEMENT]
                if hasattr(self, callback_name) and callable(getattr(self, callback_name)):
                    callback = getattr(self, callback_name)
                else:
                    callback = lambda value, s=setting: self._updatePrinterSetting(s[DisplayBase.FUNCTIONELEMENT], value)
                item = row.createElement(elementType=QType.COMBOBOX, layoutType=0,
                    function=callback,
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT])

                attr_name = setting[DisplayBase.FUNCTIONELEMENT]
                if hasattr(self.currentPrinter, attr_name):
                    current_value = str(getattr(self.currentPrinter, attr_name))
                    index = item.findText(current_value)
                    if index >= 0:
                        item.blockSignals(True)
                        item.setCurrentIndex(index)
                        item.blockSignals(False)
                self._registerSettingWidget(attr_name, item, QType.COMBOBOX)

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
                item = row.createElement(elementType=QType.LIST, layoutType=0,
                    function=lambda value, s=setting: self.vtk_manager.selectActorById(value.text()),
                    displayText=setting[DisplayBase.SHOWNAME], listElements=setting[DisplayBase.LISTELEMENT],
                    updateFunction=1)
                if item is not None:
                    item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.PageList.append(row)

            elif setting[DisplayBase.QTTYPE] == "VTK":
                if(self.vtk_manager):
                    self.vtk_manager.getVTKWidget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    row.addPage(self.vtk_manager.getVTKWidget())

                
            elif setting[DisplayBase.QTTYPE] == "SLIDER":
                methods = setting[DisplayBase.FUNCTIONELEMENT]  # [minGetter, maxGetter, changeHandler]
                func = getattr(self, methods[2])
                item = row.createElement(
                    elementType=QType.SLIDER,
                    layoutType=setting[DisplayBase.SHOWNAME],
                    function=func,
                    listElements=[0, 0]
                )
                item.hide()
                setattr(self, f"{methods[2]}_slider", item)


            elif setting[DisplayBase.QTTYPE] == "ACTOR_SETTING":
                callback_name = setting[DisplayBase.FUNCTIONELEMENT]
                callback = None
                if hasattr(self, callback_name) and callable(getattr(self, callback_name)):
                    callback = getattr(self, callback_name)
                
                list_elements = setting[DisplayBase.LISTELEMENT]
                box = row.createElement(elementType=QType.BOX, layoutType=0, function=callback, displayText=setting[DisplayBase.SHOWNAME], listElements=list_elements)
                if len(setting) > 4 and setting[4]:
                    setattr(self, setting[4], box)
                    
            elif setting[DisplayBase.QTTYPE] == "ACTOR_CHECKBOX":
                callback_name = setting[DisplayBase.FUNCTIONELEMENT]
                callback = None
                if hasattr(self, callback_name) and callable(getattr(self, callback_name)):
                    callback = getattr(self, callback_name)
                    
                list_elements = setting[DisplayBase.LISTELEMENT]
                box = row.createElement(elementType=QType.CHECKBOX, layoutType=0, function=callback, displayText=setting[DisplayBase.SHOWNAME], listElements=list_elements)
                if len(setting) > 4 and setting[4]:
                    setattr(self, setting[4], box)


            elif setting[DisplayBase.QTTYPE] == "FIXED_WIDTH":
                row.setWidth(int(setting[DisplayBase.SHOWNAME]))

            elif setting[DisplayBase.QTTYPE] == "CREATE PAGE":
               # print("Adding new Row: ", setting[DisplayBase.SHOWNAME])
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
              #  print("Adding row to page: ", row)
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




