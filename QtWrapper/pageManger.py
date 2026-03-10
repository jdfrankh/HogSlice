
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
    elements = []


    def __init__(self, layoutType=0):
        self.Page = QWidget()
        if(layoutType == 0):
            self.layout = QVBoxLayout()
        else:
            self.layout = QHBoxLayout()

        self.Page.setLayout(self.layout)

        #self.layouts.append(QVBoxLayout())
        #self.Page.setLayout(self.layouts[0])

    def createElement(self,elementType, layoutType=-1, function=None, displayText="", listEleements = [] ):
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
            item.addItems(listEleements)
            self.layout.addWidget(item)
        elif elementType == QType.LABEL:
            item = QLabel(displayText)
            self.layout.addWidget(item)
        elif elementType == QType.LIST:
            item = QListWidget()

            item.addItems(listEleements)
            item.itemClicked.connect(function)
            self.layout.addWidget(item)
        else:
            return

        self.elements.append(item)

    def addSpacing(self, layoutType=-1, spacing=10):
        self.layout.addSpacing(spacing)
    
    def addPage(self, page):
        self.layout.addWidget(page)

    def setWidth(self, width):
        self.Page.setFixedWidth(width)

    def SetHeight(self, height):
        self.Page.setFixedHeight(height)

    def getPage(self):
        return self.Page


  