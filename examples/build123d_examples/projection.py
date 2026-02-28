from build123d import *

sphere = Solid.make_sphere(50, angle1=-90)

projection_direction = Vector(0, 1, 0)
square = Face.make_rect(20, 20, Plane.ZX.offset(-80))
square_projected = square.project_to_shape(sphere, projection_direction)
square_solids = Compound.make_compound([f.thicken(2) for f in square_projected])

projection_direction = Vector(0, -1, 0)
flat_planar_text_faces = (
    Compound.make_text("Flat", font_size=30).rotate(Axis.X, 90).faces()
)
flat_projected_text_faces = Compound.make_compound(
    [
        f.project_to_shape(sphere, projection_direction)[0]
        for f in flat_planar_text_faces
    ]
)

arch_path: Edge = (
    sphere.cut(Solid.make_cylinder(80, 100, Plane.YZ).locate(Location((-50, 0, -70))))
    .edges()
    .sort_by(Axis.Z)[0]
)
text = Compound.make_text(
    txt="'the quick brown fox jumped over the lazy dog'",
    font_size=15,
    align=(Align.MIN, Align.CENTER),
)
projected_text = sphere.project_faces(text, path=arch_path)

combined = Compound(children=[sphere, square_solids, flat_projected_text_faces, projected_text])
