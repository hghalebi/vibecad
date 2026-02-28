from build123d import *

segment_count = 6

handle_center_line = Spline(
    (-10, 0, 0),
    (0, 0, 5),
    (10, 0, 0),
    tangents=((0, 0, 1), (0, 0, -1)),
    tangent_scalars=(1.5, 1.5),
)
handle_path = handle_center_line.edges()[0]

sections = Sketch()
for i in range(segment_count + 1):
    plane = Plane(
        origin=handle_path @ (i / segment_count),
        z_dir=handle_path % (i / segment_count),
    )
    if i % segment_count == 0:
        circle = plane * Circle(1)
    else:
        circle = plane * Rectangle(1.25, 3)
        circle = fillet(circle.vertices(), radius=0.2)
    sections += circle

handle = sweep(sections, path=handle_path, multisection=True)
