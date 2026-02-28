from build123d import *

sheet_thickness = 4 * MM

with BuildPart() as side:
    d = Vector(1, 0, 0).rotate(Axis.Y, 60)
    with BuildLine(Plane.XZ) as side_line:
        l1 = Line((0, 65), (170 / 2, 65))
        l2 = PolarLine(l1 @ 1, length=65, direction=d, length_mode=LengthMode.VERTICAL)
        l3 = Line(l2 @ 1, (170 / 2, 0))
        fillet(side_line.vertices(), 7)
    make_brake_formed(
        thickness=sheet_thickness,
        station_widths=[40, 40, 40, 112.52 / 2, 112.52 / 2, 112.52 / 2],
        side=Side.RIGHT,
    )
    fe = side.edges().filter_by(Axis.Z).group_by(Axis.Z)[0].sort_by(Axis.Y)[-1]
    fillet(fe, radius=7)

with BuildPart() as wing:
    with BuildLine(Plane.YZ) as wing_line:
        l1 = Line((0, 65), (80 / 2 + 1.526 * sheet_thickness, 65))
        PolarLine(l1 @ 1, 20.371288916, direction=Vector(0, 1, 0).rotate(Axis.X, -75))
        fillet(wing_line.vertices(), 7)
    make_brake_formed(
        thickness=sheet_thickness,
        station_widths=110 / 2,
        side=Side.RIGHT,
    )
    bottom_edge = wing.edges().group_by(Axis.X)[-1].sort_by(Axis.Z)[0]
    fillet(bottom_edge, radius=7)

tab_line = Plane.XZ * Polyline(
    (20, 65 - sheet_thickness), (56 / 2, 65 - sheet_thickness), (56 / 2, 88)
)
tab_line = fillet(tab_line.vertices(), 7)
tab = make_brake_formed(sheet_thickness, 8, tab_line, Side.RIGHT)
tab = fillet(tab.edges().filter_by(Axis.X).group_by(Axis.Z)[-1].sort_by(Axis.Y)[-1], 5)
tab -= Pos((0, 0, 80)) * Rot(0, 90, 0) * Hole(5, 100)

with BuildPart() as sm_hanger:
    add([side.part, wing.part])
    mirror(about=Plane.XZ)
    with BuildSketch(Plane.XY.offset(65)) as h1:
        with Locations((20, 0)):
            Rectangle(30, 30, align=(Align.MIN, Align.CENTER))
            fillet(h1.vertices().group_by(Axis.X)[-1], 7)
        SlotCenterPoint((154, 0), (154 / 2, 0), 20)
    extrude(amount=-40, mode=Mode.SUBTRACT)
    with BuildSketch() as h2:
        SlotCenterPoint((206, 0), (206 / 2, 0), 20)
    extrude(amount=40, mode=Mode.SUBTRACT)
    add(tab)
    mirror(about=Plane.YZ)
    mirror(about=Plane.XZ)
