
from enum import Enum
from PyQt5.QtWidgets import (
    QApplication, QProgressBar, QToolBar, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QFrame, QFormLayout, QComboBox,
    QSizePolicy, QMenu, QAction, QShortcut, QLineEdit, QListWidget, QStackedLayout, QCheckBox
)
from PyQt5.QtCore import Qt

class QType(Enum):
    """Enum for different widget types"""
    itemType = 0


    BUTTON = 1
    BOX = 2
    COMBOBOX = 3
    LABEL = 4
    VTK = 5
    LIST = 6
    PROGRESS = 7
    SPACING = 8
    SLIDER = 9
    CHECKBOX = 10



class PageManager:

    Page = None
    layout = None
    elements = [] # Element containting item, widget, and function to update widget if necessary


    def __init__(self, layoutType=0, alignTopLeft=False):
        self.Page = QWidget()
        if(layoutType == 0):
            self.layout = QVBoxLayout()
        else:
            self.layout = QHBoxLayout()

        # By default Qt will spread items or honor their size policies.
        # Use addStretch() inside your specific layouts to pack items.
        self.Page.setLayout(self.layout)

        #self.layouts.append(QVBoxLayout())
        #self.Page.setLayout(self.layouts[0])

    def update(self, updateItems = []): # Flesh this out with a list coordinating elements whenever
        for element in self.elements:
            
            if element[3] != None:
                #print("Updating element: ", element[0])
                if(element[2] == QType.LIST and element[3] == 1): # element[3] = 1 is to set update function to update with element array
                    # Clear the list and repopulate it with the updated items

                #    print("Updating list widget: ", element[4])
                    element[0].clear()
                    #element[0].addItems(element[3])
                    element[0].addItems(updateItems)

    def createElement(self,elementType, layoutType=-1, function=None, displayText="", listElements = [] , updateFunction = None, scaleFuction = [QSizePolicy.Fixed, QSizePolicy.Fixed]):
        if elementType == QType.BUTTON:
            item = QPushButton(displayText)
            # If the parent layout is horizontal, use Minimum for horizontal policy so stretch works
            if isinstance(self.layout, QHBoxLayout):
                item.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            else:
                item.setSizePolicy(scaleFuction[0], scaleFuction[1])
            item.clicked.connect(function)
            self.layout.addWidget(item)
        elif elementType == QType.BOX:
            item = QDoubleSpinBox()
            item.valueChanged.connect(function)
            item.setMinimum(listElements[0])
            item.setMaximum(listElements[1])
            if(len(listElements) > 2):
                item.setValue(listElements[2])
            if(len(listElements) > 3):
                item.setDecimals(listElements[3])
            if(len(listElements) > 4):
                item.setSingleStep(listElements[4])
            item.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if displayText:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(QLabel(displayText))
                row_layout.addWidget(item)
                self.layout.addWidget(row)
            else:
                self.layout.addWidget(item)
        elif elementType == QType.COMBOBOX:
            item = QComboBox()
            item.currentTextChanged.connect(function)
            item.addItems(listElements)
            item.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if displayText:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(QLabel(displayText))
                row_layout.addWidget(item)
                self.layout.addWidget(row)
            else:
                self.layout.addWidget(item)
        elif elementType == QType.LABEL:
            item = QLabel(displayText)
            self.layout.addWidget(item)
        elif elementType == QType.LIST:
            item = QListWidget()
            item.addItems(listElements)
            item.itemClicked.connect(function)
            if isinstance(self.layout, QVBoxLayout):
                item.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            else:
                item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                
            self.layout.addWidget(item)
        elif elementType == QType.PROGRESS:
            item = QProgressBar()
            item.setMinimum(listElements[0])
            item.setMaximum(listElements[1])
            self.layout.addWidget(item)
            item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
 
        elif elementType == QType.SPACING:
            self.layout.addSpacing(listElements if listElements else 10)
            item = None

        elif elementType == QType.SLIDER:
            orientation = Qt.Horizontal if layoutType == 1 else Qt.Vertical
            item = QSlider(orientation)
            item.setMinimum(listElements[0])
            item.setMaximum(listElements[1])
            if len(listElements) > 2:
                item.setValue(listElements[2])
            if len(listElements) > 3:
                item.setSingleStep(listElements[3])
            if function:
                item.valueChanged.connect(function)
            if layoutType == 1:  # horizontal slider expands width
                item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:                 # vertical slider expands height
                item.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            self.layout.addWidget(item)
            
        elif elementType == QType.CHECKBOX:
            item = QCheckBox(displayText)
            if listElements and len(listElements) > 0:
                item.setChecked(listElements[0])
            if function:
                item.stateChanged.connect(function)
            item.setSizePolicy(scaleFuction[0], scaleFuction[1])
            self.layout.addWidget(item)

        else:
            return

        self.elements.append([item, function, elementType, updateFunction, displayText])

        return item # Just in case that the item needs to be accessed later

    def addSpacing(self, layoutType=-1, spacing=10):
        self.layout.addSpacing(spacing)
        
    def addStretch(self, stretch=1):
        self.layout.addStretch(stretch)
    
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


  