

import math
import copy as _copy_mod

#for floating point comparison
def close(f1, f2, delta=0.001):
    comp = (max(f1, f2) - min(f1, f2))
    return (comp > -delta) and (comp < delta)



class Point:
    def __init__(self, x_, y_, z_):
        self.x = x_
        self.y = y_
        self.z = z_

    def dotProduct(self, p):
        return self.x*p.x + self.y*p.y + self.z*p.z

    def normalize(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def toString(self):
        return "Point("+str(self.x)+","+str(self.y)+","+str(self.z)+")"
    def equals(self, p2, delta=0.001):
        if close(self.x, p2.x, delta) and close(self.y, p2.y, delta) and close(self.z, p2.z, delta):
            return True
        else:
            return False
        

class Line:
    def __init__(self, p0_, p1_):
        self.p0 = p0_
        self.p1 = p1_

    def toString(self):
        return "Line("+self.p0.toString()+","+self.p1.toString()+")"
    def reverse(self):
        x_ = _copy_mod.copy(self.p0.x)
        y_ = _copy_mod.copy(self.p0.y)
        z_ = _copy_mod.copy(self.p0.z)
        self.p0.x = _copy_mod.copy(self.p1.x)
        self.p0.y = _copy_mod.copy(self.p1.y)
        self.p0.z = _copy_mod.copy(self.p1.z)
        self.p1.x = x_
        self.p1.y = y_
        self.p1.z = z_
        return self
    

class Triangle:
    def __init__(self, p0_, p1_, p2_, norm_):
        self.p0 = p0_
        self.p1 = p1_
        self.p2 = p2_
        self.norm = norm_
    def toString(self):
        return "Triangle("+self.p0.toString()+","+self.p1.toString()+","+self.p2.toString()+")"


