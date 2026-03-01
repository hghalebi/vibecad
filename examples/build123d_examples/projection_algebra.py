from build123d import *

sphere = Sphere(50)

projection_direction = Vector(0, 1, 0)
square = Plane.ZX.offset(-80) * Rectangle(20, 20)
square_projected = square.faces()[0].project_to_shape(sphere, projection_direction)
square_solids = Part() + [f.thicken(2) for f in square_projected]

projection_direction = Vector(0, -1, 0)
flat_planar_text = Rot(90, 0, 0) * Text("Flat", font_size=30)
flat_projected_text_faces = Sketch() + [
    f.project_to_shape(sphere, projection_direction)[0]
    for f in flat_planar_text.faces()
]

cyl = Plane.YZ * Cylinder(80, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
obj = sphere - Pos(-50, 0, -70) * cyl
arch_path: Edge = obj.edges().sort_by().first
text = Text(
    "'the quick brown fox jumped over the lazy dog'",
    font_size=15,
    align=(Align.MIN, Align.CENTER),
)
projected_text = sphere.project_faces(text.faces(), path=arch_path)

combined = Compound(children=[sphere, square_solids, flat_projected_text_faces, projected_text])
