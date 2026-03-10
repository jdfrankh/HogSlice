

class Widgets:
    """Base Button class that serves as a superclass for Widgets"""
    BUTTON = 1
    widgetId = ""
    widgetTypeSet = ""
    connectedFunction = None
    displayText = ""

    def __init__(self, _widgetId, _widgetType, _connectedFunction, _displayText = "" ):
        
        self.widgetId = _widgetId
        self.widgetTypeSet = _widgetType
        self.connectedFunction = _connectedFunction
        self.displayText = _displayText


    def doAction(self):
        #Method to perform the button's action
        pass

  





