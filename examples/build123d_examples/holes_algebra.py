from build123d import *

thru_hole = Cylinder(radius=3, height=2)
thru_hole -= Hole(radius=1, depth=2)

recessed_counter_bore = Cylinder(radius=3, height=2)
recessed_counter_bore -= CounterBoreHole(
    radius=1, depth=2, counter_bore_radius=1.5, counter_bore_depth=0.5
)

recessed_counter_sink = Cylinder(radius=3, height=2)
recessed_counter_sink -= CounterSinkHole(radius=1, depth=2, counter_sink_radius=1.5)

flush_counter_sink = Cylinder(radius=3, height=2)
plane = Plane(flush_counter_sink.faces().sort_by().last)
flush_counter_sink -= plane * CounterSinkHole(
    radius=1, depth=2, counter_sink_radius=1.5
)

combined = Compound(children=[thru_hole, Pos(10, 0) * recessed_counter_bore, Pos(0, 10) * recessed_counter_sink, Pos(10, 10) * flush_counter_sink])
