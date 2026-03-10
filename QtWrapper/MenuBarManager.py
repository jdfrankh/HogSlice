from enum import Enum
from PyQt5.QtWidgets import QMenu, QAction
#Class to store all widget instances and manage them per layout


class MenuBarType(Enum):
    """Enum for different widget types"""
    MENU = 1
    #SLIDER = 2
    #TEXTBOX = 3




class MenuBarManager:

    WidgetItem = None
    widgetId = ""
    displayText = ""
    widgetType = None
    QItems = []
    parent = None


    def __init__(self, _widgetType, _widgetId, _displayText, _parent=None ):
        
        if _widgetType in MenuBarType:
            self.widgetType = _widgetType
            if _widgetType == MenuBarType.MENU:
                self.parent = _parent
                self.WidgetItem = QMenu(_displayText, _parent)
                self.displayText = _displayText
                self.widgetId = _widgetId
        else:
            print("Widget Type not recognized")
            return

    def addWidget(self, _name, function = None):
        #Add try & except here for fallback
        if self.widgetType == MenuBarType.MENU:
            action = QAction(_name, self.parent)
            self.QItems.append(action)
            self.QItems[-1].triggered.connect(function)
            self.WidgetItem.addAction(self.QItems[-1])

    def addSeparator(self):
        if self.widgetType == MenuBarType.MENU:
            self.WidgetItem.addSeparator()