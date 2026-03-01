from build123d import *

clock_radius = 10
with BuildSketch() as minute_indicator:
    with BuildLine() as outline:
        l1 = CenterArc((0, 0), clock_radius * 0.975, 0.75, 4.5)
        l2 = CenterArc((0, 0), clock_radius * 0.925, 0.75, 4.5)
        Line(l1 @ 0, l2 @ 0)
        Line(l1 @ 1, l2 @ 1)
    make_face()
    fillet(minute_indicator.vertices(), radius=clock_radius * 0.01)

with BuildSketch() as clock_face:
    Circle(clock_radius)
    with PolarLocations(0, 60):
        add(minute_indicator.sketch, mode=Mode.SUBTRACT)
    with PolarLocations(clock_radius * 0.875, 12):
        SlotOverall(clock_radius * 0.05, clock_radius * 0.025, mode=Mode.SUBTRACT)
    for hour in range(1, 13):
        with PolarLocations(clock_radius * 0.75, 1, -hour * 30 + 90, 360, rotate=False):
            Text(
                str(hour),
                font_size=clock_radius * 0.175,
                font_style=FontStyle.BOLD,
                mode=Mode.SUBTRACT,
            )
