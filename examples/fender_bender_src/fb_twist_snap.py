from build123d import (
    add,
    export_stl,
    extrude,
    fillet,
    loft,
    Align,
    Axis,
    Cylinder,
    BuildPart,
    BuildSketch,
    Circle,
    Location,
    Mode,
    Part,
    Plane,
    RegularPolygon,
    Text,
)
from ocp_vscode import show, Camera
from bd_warehouse.thread import TrapezoidalThread
from fb_library import twist_snap_socket

from filament_bracket_config import TubeConfig, ConnectorConfig

TWIST_SNAP_RADIUS = 3.5


def fb_twist_snap_socket(
    connector: ConnectorConfig,
    socket_tube: TubeConfig,
    twist_snap_radius: float = TWIST_SNAP_RADIUS,
    wall_thickness: float = 2,
    label: str = "MMU",
    display_label: str = "twist-snap collet socket",
) -> Part:
    with BuildPart(Location((0, 0, wall_thickness * 3))) as skt:
        add(
            twist_snap_socket(connector_radius=twist_snap_radius),
            rotation=(180, 0, 45),
        )
        with BuildPart() as handle:
            with BuildSketch(Plane.XY.offset(wall_thickness * 3)) as hexbase:
                Circle(5.5 + 2 / 3)
            with BuildSketch(
                Plane.XY.offset(wall_thickness * 1.5 + connector.length * 2)
            ) as hexmid:
                RegularPolygon(radius=7.5, side_count=6)
                fillet(hexmid.vertices(), wall_thickness * 2)
            with BuildSketch(
                Plane.XY.offset(wall_thickness * 3 + connector.length * 2)
            ) as hextop:
                # RegularPolygon(radius=3.5 + wall_thickness * 2 + 0.5, side_count=6)
                RegularPolygon(radius=7.5, side_count=6)
                fillet(hextop.vertices(), wall_thickness * 2)
            loft(ruled=True)
        with BuildPart(mode=Mode.SUBTRACT) as hollow:
            with BuildSketch(Plane.XY.offset(wall_thickness * 2)) as funnel_end:
                Circle(socket_tube.inner_radius)
            with BuildSketch(
                Plane.XY.offset(wall_thickness + connector.length * 2)
            ) as funnel_start:
                Circle(connector.tube.inner_radius)
            loft(ruled=True)
            with BuildSketch(
                Plane.XY.offset(6 + connector.length * 2 - connector.length - 2)
            ) as straight_start:
                Circle(connector.tube.outer_radius)
            with BuildSketch(
                Plane.XY.offset(6 + connector.length * 2 - connector.length)
            ) as straight_start:
                Circle(connector.tube.outer_radius)
            loft(ruled=True)
            with BuildPart(
                Plane.XY.offset(6 + connector.length * 2 - connector.length)
            ):
                Cylinder(
                    radius=connector.diameter / 2,
                    height=connector.length,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )
            with BuildSketch(skt.faces().sort_by(Axis.Y)[1].center_location):
                Text(
                    label,
                    font_size=5,
                    font="Flamante Round Bold",
                    align=(Align.CENTER, Align.CENTER),
                )
            extrude(amount=0.5, both=True)
        with BuildPart(Plane.XY.offset(6 + connector.length * 2 - connector.length)):
            TrapezoidalThread(
                diameter=connector.diameter,
                pitch=connector.thread_pitch,
                length=connector.length,
                thread_angle=connector.thread_angle,
                external=False,
                interference=connector.thread_interference,
                hand="right",
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            Cylinder(
                radius=connector.diameter / 2,
                height=connector.length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.INTERSECT,
            )
    skt.part.label = display_label
    return skt.part


if __name__ == "__main__":
    skt = fb_twist_snap_socket(
        ConnectorConfig(
            thread_pitch=1.059,
            thread_angle=60,
            thread_interference=0.2,
            diameter=10.4,
            length=7.7,
            tube=TubeConfig(inner_diameter=3.7, outer_diameter=6.5),
        ),
        TubeConfig(inner_diameter=2.4, outer_diameter=4.25),
        label="MMU",
    )
    show(skt, reset_camera=Camera.KEEP)
    export_stl(skt, "stl/mmu3-twist-snap-socket.stl")
