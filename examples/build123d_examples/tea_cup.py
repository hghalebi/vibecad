from build123d import *

wall_thickness = 3 * MM
fillet_radius = wall_thickness * 0.49

with BuildPart() as tea_cup:
    with BuildSketch(Plane.XZ) as bowl_section:
        with BuildLine():
            s = Spline(
                (30 * MM, 10 * MM),
                (69 * MM, 105 * MM),
                tangents=((1, 0.5), (0.7, 1)),
                tangent_scalars=(1.75, 1),
            )
            Polyline(s @ 0, s @ 0 + (10 * MM, -10 * MM), (0, 0), (0, (s @ 1).Y), s @ 1)
        make_face()
    revolve(axis=Axis.Z)
    offset(amount=-wall_thickness, openings=tea_cup.faces().filter_by(GeomType.PLANE))
    with Locations((0, 0, (s @ 0).Y)):
        Cylinder(radius=(s @ 0).X, height=wall_thickness)
    fillet(tea_cup.edges(), radius=fillet_radius)

    handle_intersections = [
        tea_cup.part.find_intersection(
            Axis(origin=(0, 0, vertical_offset), direction=(1, 0, 0))
        )[-1][0]
        for vertical_offset in [35 * MM, 80 * MM]
    ]
    with BuildLine(Plane.XZ) as handle_path:
        path_spline = Spline(
            handle_intersections[0] - (wall_thickness / 2, 0),
            handle_intersections[0] + (35 * MM, 30 * MM),
            handle_intersections[0] + (40 * MM, 60 * MM),
            handle_intersections[1] - (wall_thickness / 2, 0),
            tangents=((1, 1.25), (-0.2, -1)),
        )
    with BuildSketch(
        Plane(origin=path_spline @ 0, z_dir=path_spline % 0)
    ) as handle_cross_section:
        RectangleRounded(wall_thickness, 8 * MM, fillet_radius)
    sweep()
