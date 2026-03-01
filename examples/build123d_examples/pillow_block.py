from build123d import *

height, width, thickness, padding = 60, 80, 10, 12
screw_shaft_radius, screw_head_radius, screw_head_height = 1.5, 3, 3
bearing_axle_radius, bearing_radius, bearing_thickness = 4, 11, 7

with BuildPart() as pillow_block:
    with BuildSketch() as plan:
        Rectangle(width, height)
        fillet(plan.vertices(), radius=5)
    extrude(amount=thickness)
    with Locations(pillow_block.faces().sort_by(Axis.Z)[-1]):
        CounterBoreHole(bearing_axle_radius, bearing_radius, bearing_thickness)
        with GridLocations(width - 2 * padding, height - 2 * padding, 2, 2):
            CounterBoreHole(screw_shaft_radius, screw_head_radius, screw_head_height)
