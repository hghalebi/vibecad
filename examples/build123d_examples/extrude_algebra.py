from build123d import *

simple = extrude(Text("O", font_size=10), amount=5)
both = extrude(Text("O", font_size=10), amount=5, both=True)

multiple = Box(10, 10, 10)
faces = [
    Plane(face) * loc * Text("Ω", font_size=3)
    for face in multiple.faces()
    for loc in GridLocations(5, 5, 2, 2)
]
multiple += [extrude(face, amount=1) for face in faces]

non_planar = Rot(90, 0, 0) * Cylinder(
    10, 20, align=(Align.CENTER, Align.MIN, Align.CENTER)
)
non_planar &= Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
non_planar = extrude(non_planar.faces().sort_by(Axis.Z).first, amount=2)

rad, rev = 3, 25
circle = Pos(0, rev) * Circle(rad)
ex26_target = revolve(circle, Axis.X, revolution_arc=90)
ex26_target = ex26_target + mirror(ex26_target, Plane.XZ)
rect = Rectangle(rad, rev)
ex26 = extrude(rect, until=Until.LAST, target=ex26_target, clean=False)

circle = Pos(0, rev) * Circle(rad)
ex27 = revolve(circle, Axis.X, revolution_arc=90)
circle2 = Plane.XZ * Pos(0, rev) * Circle(rad)
ex27 += revolve(circle2, Axis.X, revolution_arc=150)
rect = Plane.XY.offset(-60) * Rectangle(rad, rev + 25)
extrusion27 = extrude(rect, until=Until.NEXT, target=ex27, mode=Mode.ADD)

ex28 = Rot(0, 90, 0) * Torus(25, 5)
rect = Rectangle(rad, rev)
extrusion28 = extrude(rect, until=Until.NEXT, target=ex28, both=True, clean=False)

combined = Compound(children=[simple, both, multiple, non_planar, ex26, extrusion27, extrusion28])
