from build123d import *

overall_width, top_width, height, thickness, fillet_radius = 35, 27, 7.5, 1, 0.8
rail_length = 1000
slot_width, slot_length, slot_pitch = 6.2, 15, 25

with BuildPart() as rail:
    with BuildSketch(Plane.XZ) as din:
        Rectangle(overall_width, thickness, align=(Align.CENTER, Align.MIN))
        Rectangle(top_width, height, align=(Align.CENTER, Align.MIN))
        Rectangle(
            top_width - 2 * thickness,
            height - thickness,
            align=(Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )
        inside_vertices = (
            din.vertices()
            .filter_by_position(Axis.Y, 0.0, height, inclusive=(False, False))
            .filter_by_position(
                Axis.X,
                -overall_width / 2,
                overall_width / 2,
                inclusive=(False, False),
            )
        )
        fillet(inside_vertices, radius=fillet_radius)
        outside_vertices = filter(
            lambda v: (v.Y == 0.0 or v.Y == height)
            and -overall_width / 2 < v.X < overall_width / 2,
            din.vertices(),
        )
        fillet(list(outside_vertices), radius=fillet_radius + thickness)
    extrude(amount=rail_length / 2, both=True)

    with BuildSketch(Plane.XY) as slots:
        with GridLocations(
            0,
            slot_pitch,
            1,
            rail_length // slot_pitch - 1,
        ):
            SlotOverall(slot_length, slot_width, rotation=90)
    extrude(amount=height, mode=Mode.SUBTRACT)
