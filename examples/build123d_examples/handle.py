from build123d import *

segment_count = 6

with BuildPart() as handle:
    with BuildLine() as handle_center_line:
        Spline(
            (-10, 0, 0),
            (0, 0, 5),
            (10, 0, 0),
            tangents=((0, 0, 1), (0, 0, -1)),
            tangent_scalars=(1.5, 1.5),
        )
    handle_path: Wire = handle_center_line.wires()[0]
    for i in range(segment_count + 1):
        with BuildSketch(
            Plane(
                origin=handle_path @ (i / segment_count),
                z_dir=handle_path % (i / segment_count),
            )
        ) as section:
            if i % segment_count == 0:
                Circle(1)
            else:
                Rectangle(1.25, 3)
                fillet(section.vertices(), radius=0.2)
    sweep(multisection=True)
