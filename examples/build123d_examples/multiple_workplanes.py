from build123d import *

with BuildPart() as obj:
    Box(5, 5, 1)
    with BuildPart(*obj.faces().filter_by(Axis.Z), mode=Mode.SUBTRACT):
        Sphere(1.8)
