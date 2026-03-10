
from enum import Enum
from PyQt5.QtWidgets import (
    QApplication, QToolBar, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QFrame, QFormLayout, QComboBox,
    QSizePolicy, QMenu, QAction, QShortcut, QLineEdit, QListWidget, QStackedLayout
)

class QType(Enum):
    """Enum for different widget types"""
    itemType = 0


    BUTTON = 1
    BOX = 2
    COMBOBOX = 3
    LABEL = 4
    VTK = 5
    LIST = 6


class PageManager:

    Page = None
    layout = None
    elements = [] # Element containting item, widget, and function to update widget if necessary


    def __init__(self, layoutType=0):
        self.Page = QWidget()
        if(layoutType == 0):
            self.layout = QVBoxLayout()
        else:
            self.layout = QHBoxLayout()

        self.Page.setLayout(self.layout)

        #self.layouts.append(QVBoxLayout())
        #self.Page.setLayout(self.layouts[0])

    def update(self, updateItems = []): # Flesh this out with a list coordinating elements whenever
        for element in self.elements:
            
            if element[3] != None:
                print("Updating element: ", element[0])
                if(element[2] == QType.LIST and element[3] == 1): # element[3] = 1 is to set update function to update with element array
                    # Clear the list and repopulate it with the updated items

                    print("Updating list widget: ", element[4])
                    element[0].clear()
                    #element[0].addItems(element[3])
                    element[0].addItems(updateItems)

    def createElement(self,elementType, layoutType=-1, function=None, displayText="", listElements = [] , updateFunction = None):
        if elementType == QType.BUTTON:
            item = QPushButton(displayText)
            item.clicked.connect(function)
            self.layout.addWidget(item)
        elif elementType == QType.BOX:
            item = QDoubleSpinBox()
            item.valueChanged.connect(function)
            self.layout.addWidget(item)
        elif elementType == QType.COMBOBOX:
            item = QComboBox()
            item.currentTextChanged.connect(function)
            item.addItems(listElements)
            self.layout.addWidget(item)
        elif elementType == QType.LABEL:
            item = QLabel(displayText)
            self.layout.addWidget(item)
        elif elementType == QType.LIST:
            item = QListWidget()
            item.addItems(listElements)
            item.itemClicked.connect(function)
            self.layout.addWidget(item)
        else:
            return

        self.elements.append([item, function, elementType, updateFunction, displayText])

    def addSpacing(self, layoutType=-1, spacing=10):
        self.layout.addSpacing(spacing)
    
    def addPage(self, page):
        self.layout.addWidget(page)
        
        #self.elements.append([page, None, QType.itemType, None])

    def setWidth(self, width):
        self.Page.setFixedWidth(width)

    def SetHeight(self, height):
        self.Page.setFixedHeight(height)

    def getPage(self):
        return self.Page
    
    def getElements(self):
        return self.elements
    
    def appendElements(self, elements):
        self.elements.extend(elements)


  