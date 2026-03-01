from build123d import *

# Note: This requires low_poly_benchy.stl to be present
importer = Mesher()
benchy_stl = importer.read("low_poly_benchy.stl")[0]

with BuildPart() as benchy:
    add(benchy_stl)
    vertices = benchy.vertices()
    roof_vertices = vertices.filter_by_position(Axis.Z, 38, 42)
    roof_plane_vertices = [
        roof_vertices.group_by(Axis.Y, tol_digits=2)[-1].sort_by(Axis.X)[0],
        roof_vertices.sort_by(Axis.Z)[0],
        roof_vertices.group_by(Axis.Y, tol_digits=2)[0].sort_by(Axis.X)[0],
    ]
    roof_plane = Plane(
        Face.make_from_wires(
            Wire.make_polygon([v.to_tuple() for v in roof_plane_vertices])
        )
    )
    split(bisect_by=roof_plane, keep=Keep.BOTTOM)
    smoke_stack_vertices = vertices.group_by(Axis.Z, tol_digits=0)[-1]
    smoke_stack_center = sum(
        [Vector(v.X, v.Y, v.Z) for v in smoke_stack_vertices], Vector()
    ) * (1 / len(smoke_stack_vertices))
    smoke_stack_radius = max(
        [
            (Vector(*v.to_tuple()) - smoke_stack_center).length
            for v in smoke_stack_vertices
        ]
    )
    with BuildSketch(Plane(smoke_stack_center)):
        Circle(smoke_stack_radius)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=-3 * MM)
    with BuildSketch(Plane(smoke_stack_center)):
        Circle(smoke_stack_radius - 0.5 * MM)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=roof_plane_vertices[1].Z - smoke_stack_center.Z)
