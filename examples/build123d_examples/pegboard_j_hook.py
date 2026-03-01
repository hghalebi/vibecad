from build123d import *

pegd = 6.35 + 0.1
c2c = 25.4
arcd = 7.2
both = 10
topx = 6
midx = 8
maind = 0.82 * pegd
midd = 1.0 * pegd
hookd = 23
hookx = 10
splitz = maind / 2 - 0.1
topangs = 70

with BuildPart() as mainp:
    with BuildLine(mode=Mode.PRIVATE) as sprof:
        l1 = Line((-both, 0), (c2c - arcd / 2 - 0.5, 0))
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=arcd / 2, arc_size=topangs)
        l3 = PolarLine(
            start=l2 @ 1,
            length=topx,
            direction=l2 % 1,
        )
        l4 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=arcd / 2, arc_size=-topangs)
        l5 = PolarLine(
            start=l4 @ 1,
            length=topx,
            direction=l4 % 1,
        )
        l6 = JernArc(
            start=l1 @ 0, tangent=(l1 % 0).reverse(), radius=hookd / 2, arc_size=170
        )
        l7 = PolarLine(
            start=l6 @ 1,
            length=hookx,
            direction=l6 % 1,
        )
    with BuildSketch(Plane.YZ):
        Circle(radius=maind / 2)
    sweep(path=sprof.wires()[0])
    with BuildLine(mode=Mode.PRIVATE) as stub:
        l7 = Line((0, 0), (0, midx + maind / 2))
    with BuildSketch(Plane.XZ):
        Circle(radius=midd / 2)
    sweep(path=stub.wires()[0])
    split(bisect_by=Plane(origin=(0, 0, -splitz)))
    split(bisect_by=Plane(origin=(0, 0, splitz)), keep=Keep.BOTTOM)
