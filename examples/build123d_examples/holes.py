from build123d import *

with BuildPart() as thru_hole:
    Cylinder(radius=3, height=2)
    Hole(radius=1)

with BuildPart() as recessed_counter_bore:
    with Locations((10, 0)):
        Cylinder(radius=3, height=2)
        CounterBoreHole(radius=1, counter_bore_radius=1.5, counter_bore_depth=0.5)

with BuildPart() as recessed_counter_sink:
    with Locations((0, 10)):
        Cylinder(radius=3, height=2)
        CounterSinkHole(radius=1, counter_sink_radius=1.5)

with BuildPart() as flush_counter_sink:
    with Locations((10, 10)):
        Cylinder(radius=3, height=2)
        with Locations(
            (0, 0, flush_counter_sink.part.faces().sort_by(Axis.Z)[-1].center().Z)
        ):
            CounterSinkHole(radius=1, counter_sink_radius=1.5)

combined = Compound(children=[thru_hole.part, recessed_counter_bore.part, recessed_counter_sink.part, flush_counter_sink.part])
