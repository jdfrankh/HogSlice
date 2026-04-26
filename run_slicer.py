import slicer
class DummyPrinter:
    pass

def cb(progress):
    print("Progress:", progress)

slicer.sliceItem('small_cube.stl', 0.2, 0.2, 50, 900, bottomLayers=2, topLayers=2, printerProfile=DummyPrinter(), progressCallback=cb)
