from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF
import os

out_dir = "assets/overlay_icons"
os.makedirs(out_dir, exist_ok=True)

def create_icon(name, draw_func):
    img = QImage(64, 64, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0)) # transparent background
    
    # Optional dark rounded rect for the button background
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(40, 44, 52, 200)))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 10, 10)
    
    # Setup drawing style
    pen = QPen(QColor(230, 236, 243))
    pen.setWidth(4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    
    draw_func(painter)
    painter.end()
    
    img.save(os.path.join(out_dir, name))
    print(f"Generated {name}")

def draw_translate(p):
    p.drawLine(32, 12, 32, 52)
    p.drawLine(12, 32, 52, 32)
    p.drawLine(32, 12, 24, 20)
    p.drawLine(32, 12, 40, 20)
    p.drawLine(32, 52, 24, 44)
    p.drawLine(32, 52, 40, 44)
    p.drawLine(12, 32, 20, 24)
    p.drawLine(12, 32, 20, 40)
    p.drawLine(52, 32, 44, 24)
    p.drawLine(52, 32, 44, 40)

def draw_rotate(p):
    p.drawArc(QRectF(16, 16, 32, 32), 45 * 16, 270 * 16)
    p.drawLine(48, 16, 40, 12)
    p.drawLine(48, 16, 44, 24)

def draw_scale(p):
    p.drawLine(20, 44, 44, 20)
    p.drawLine(44, 20, 32, 20)
    p.drawLine(44, 20, 44, 32)
    p.drawLine(20, 44, 32, 44)
    p.drawLine(20, 44, 20, 32)
    p.drawRect(28, 28, 8, 8)

def draw_setflat(p):
    p.setPen(QPen(QColor(98, 166, 255), 4, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(12, 50, 52, 50)
    
    p.setPen(QPen(QColor(230, 236, 243), 4, Qt.SolidLine, Qt.RoundCap))
    poly = QPolygonF([QPointF(24, 40), QPointF(40, 30), QPointF(46, 42), QPointF(30, 50)])
    p.drawPolygon(poly)
    
    p.setPen(QPen(QColor(98, 166, 255), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(32, 14, 32, 26)
    p.drawLine(32, 26, 26, 20)
    p.drawLine(32, 26, 38, 20)

create_icon('translate.png', draw_translate)
create_icon('rotate.png', draw_rotate)
create_icon('scale.png', draw_scale)
create_icon('setflat.png', draw_setflat)
