# noinspection PyUnresolvedReferences
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox, QPushButton
from PyQt5.QtCore import Qt
import sys
from windowManager import WindowManager 


#TODO:



def main():
    
    app = QApplication(sys.argv)
    window = WindowManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()