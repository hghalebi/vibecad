from build123d import *

with BuildPart() as bp:
    Box(3, 3, 3)
    with BuildSketch(*bp.faces()):
        Rectangle(1, 2, rotation=45)
    extrude(amount=0.1)
