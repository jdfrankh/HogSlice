with open("HogforgeApplication.py", "r") as f:
    text = f.read()

text = text.replace("actor.refreshBounds()", "actor.refactorGizmo(self.vtk_manager.selectedMoveType)")

with open("HogforgeApplication.py", "w") as f:
    f.write(text)
print("Fixed bounds calls")
