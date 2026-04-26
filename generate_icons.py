from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF
import os

out_dir = "assets/overlay_icons"
os.makedirs(out_dir, exist_ok=True)

def create_icon(name, draw_func):
    img = QImage(64, 64, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0)) # transparent background
    
    # optional: draw a soft dark rounded rect background for the button itself
    # so they don't just float invisibly 
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(40, 44, 52, 200)))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 10, 10)
    
    # setup drawing style
    pen = QPen(QColor(230, 236, 243))
    pen.setWidth(4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    
    draw_func(painter)
    painter.end()
    
    img.save(os.path.join(out_dir, name))
    print(f"Generated {name}")

def draw_from PyQt5.QtGui import QImage,   from PyQt5.QtCore import Qt, QPointF, QRectF
import os

out_dir = "asset uimport os

out_dir = "assets/overlay_icons"Li
out_dir2, os.makedirs(out_dir, exist_ok=T.d
def create_icon(name, draw_func):Lin    img = QImage(64, 64, QImage.ef    img.fill(QColor(0, 0, 0, 0)) # transparenne    
    # optional: draw a soft dark rounded rect backg2,   ,     # so they don't just float invisibly 
    painter = QPainter(img)
    pai      painter = QPainter(img 32, 32), 45 * 1    painter.setRenderHint(ea    painter.setBrush(QBrush(QColor(40, 44, 52, (48, 16, 44, 24)

def draw_scale(p):
    # Diagonal line    painter.drawRoundedRect 2    
    # setup drawing style
    pen = QPen(QC 3   20    pen = QPen(QColor(23 4    pen.setWidth(4)
    pen.setCapSt)
    pen.setCapStyl 4    pen.setJoinStyle(Qt.RoundJo p   awRect(28, 28, 8, 8)

def draw_s    
    draw_func(paid    ne
    p.setPen(QPen(QCol    
    img.sav,    Qt    print(f"Generated {name}")

def draw(1
def draw_from PyQt5.QtGui imangimport os

out_dir = "asset uimport os

out_dir = "assets/overlay_icons"Li
out_dir2, o Q
out_dirap)
out_dir = "assets/overlayoinout_dir2, os.makedirs(out_dir, exntdef create_icon(name, draw_func):Lin    imygon(poly)
    
    # Down arrow
    p.setPen(QPen(QColor(98, 166, 255), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(32, 14, 32, 26)
    p.drawLine(32, 26, 26, 20)
    p.drawLine(32, 26, 38, 20)

create_icon('translate.png    pai      painter = QPaicon('rotate.png', draw_rotate)
create_icon('scale.png', draw_scale)
create_icon('setflat.png', draw_setflat)
