from build123d import *

with BuildSketch() as inset_pattern:
    with BuildLine() as bl:
        Polyline((9, 9), (1, 5), (-0.5, 0))
        offset(amount=1, side=Side.LEFT)
    make_face()
    split(bisect_by=Plane(origin=(0, 0, 0), z_dir=(-1, 1, 0)))
    mirror(about=Plane(origin=(0, 0, 0), z_dir=(-1, 1, 0)))
    mirror(about=Plane.YZ)
    mirror(about=Plane.XZ)

with BuildPart() as outset_builder:
    with BuildSketch():
        Rectangle(20, 20)
        add(inset_pattern.sketch, mode=Mode.SUBTRACT)
    extrude(amount=1)

with BuildPart() as inset_builder:
    add(inset_pattern.sketch)
    extrude(amount=1)

outset = outset_builder.part
outset.color = Color(0.137, 0.306, 0.439)
inset = inset_builder.part
inset.color = Color(0.980, 0.973, 0.749)

tile = Compound(children=[inset, outset])
