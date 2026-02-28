from build123d import *

with BuildPart() as key_cap:
    with BuildSketch() as plan:
        Rectangle(18 * MM, 18 * MM)
    extrude(amount=10 * MM, taper=15)
    with Locations((0, -3 * MM, 47 * MM)):
        Sphere(40 * MM, mode=Mode.SUBTRACT, rotation=(90, 0, 0))
    fillet(
        key_cap.edges().filter_by_position(Axis.Z, 0, 30 * MM, inclusive=(False, True)),
        radius=1 * MM,
    )
    scale(by=(0.925, 0.925, 0.85), mode=Mode.SUBTRACT)

    with BuildSketch(Plane(origin=(0, 0, 4 * MM))):
        Rectangle(15 * MM, 0.5 * MM)
        Rectangle(0.5 * MM, 15 * MM)
        Circle(radius=5.5 * MM / 2)
    extrude(until=Until.NEXT)
    rib_bottom = key_cap.faces().filter_by_position(Axis.Z, 4 * MM, 4 * MM)[0]
    with BuildSketch(rib_bottom) as cruciform:
        Circle(radius=5.5 * MM / 2)
        Rectangle(4.1 * MM, 1.17 * MM, mode=Mode.SUBTRACT)
        Rectangle(1.17 * MM, 4.1 * MM, mode=Mode.SUBTRACT)
    extrude(amount=3.5 * MM, mode=Mode.ADD)
