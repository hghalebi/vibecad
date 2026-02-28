from build123d import *

with BuildPart() as simple:
    with BuildSketch():
        Text("O", font_size=10)
    extrude(amount=5)

with BuildPart() as both:
    with BuildSketch():
        Text("O", font_size=10)
    extrude(amount=5, both=True)

with BuildPart() as multiple:
    Box(10, 10, 10)
    with BuildSketch(*multiple.faces()):
        with GridLocations(5, 5, 2, 2):
            Text("Ω", font_size=3)
    extrude(amount=1)

with BuildPart() as non_planar:
    Cylinder(10, 20, rotation=(90, 0, 0), align=(Align.CENTER, Align.MIN, Align.CENTER))
    Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.INTERSECT)
    extrude(
        non_planar.part.faces().sort_by(Axis.Z)[0],
        amount=2,
        dir=(0, 0, 1),
        mode=Mode.REPLACE,
    )

rad, rev = 3, 25
with BuildPart() as ex26:
    with BuildSketch() as ex26_sk:
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=90)
    mirror(about=Plane.XZ)
    with BuildSketch() as ex26_sk2:
        Rectangle(rad, rev)
    extrude(until=Until.LAST, clean=False, mode=Mode.REPLACE)

with BuildPart() as ex27:
    with BuildSketch():
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=90)
    with BuildSketch(Plane.XZ):
        with Locations((0, rev)):
            Circle(rad)
    revolve(axis=Axis.X, revolution_arc=150)
    with BuildSketch(Plane.XY.offset(-60)):
        Rectangle(rad, rev + 25)
    extrude(until=Until.NEXT, mode=Mode.ADD)

combined = Compound(children=[simple.part, both.part, multiple.part, non_planar.part, ex26.part, ex27.part])
