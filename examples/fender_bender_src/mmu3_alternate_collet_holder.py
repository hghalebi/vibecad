from dataclasses import field
from typing import Optional
from build123d import (
    add,
    chamfer,
    extrude,
    fillet,
    loft,
    make_face,
    Align,
    Axis,
    Box,
    Color,
    Cylinder,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    GridLocations,
    Location,
    Mode,
    Part,
    Polyline,
    Text,
)
from ocp_vscode import show, Camera
from fb_library import (
    shifted_midpoint,
    teardrop_cylinder,
    twist_snap_connector,
    Point,
)
from partomatic import Partomatic, PartomaticConfig, AutomatablePart

from filament_bracket_config import TubeConfig, ConnectorConfig


class AlternateColletHolderConfig(PartomaticConfig):
    yaml_tree: str = "FilamentBracket"

    stl_folder: str = "NONE"
    file_prefix: str = ""
    file_suffix: str = ""

    # these are MMU3 values that should not be changed by config files
    COLLET_HOLDER_REVISION: str = "R1"
    COLLET_HOLDER_LENGTH = 65.2
    COLLET_HOLDER_ANGLE = 10
    COLLET_HOLDER_TOP_STRAIGHT_DEPTH = 4.925
    COLLET_HOLDER_TOP_BENT_DEPTH = 16.189
    COLLET_HOLDER_WIDTH = 10.0
    COLLET_HOLDER_CHAMFER_RADIUS = 1
    COLLET_HOLDER_TUBE_DISTANCE = 14
    COLLET_HOLDER_TUBE_RADIUS = 2.125


class AlternateColletHolder(Partomatic):
    _config: AlternateColletHolderConfig = AlternateColletHolderConfig()

    def _screwcut(self) -> Part:
        """
        returns the screw cut for the collet holder
        """
        with BuildPart() as new_screwcut:
            add(
                teardrop_cylinder(
                    radius=1.7,
                    peak_distance=2.1,
                    height=55,
                    rotation=(0, 0, 180),
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )
            )
            add(
                teardrop_cylinder(
                    radius=2.85,
                    peak_distance=7.5,
                    height=55,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                )
            )
            with BuildPart(Location((0, -3.6, 0)), mode=Mode.INTERSECT) as inters:
                Box(6, 15, 150, align=(Align.CENTER, Align.MIN, Align.CENTER))
        new_screwcut.part.label = "screw cut"
        return new_screwcut.part

    def _tube_channel(self) -> Part:
        with BuildPart() as channel:
            base_expansion_point = Point(
                0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH / 2
            )
            base_expansion_full = Point(
                0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH * 0.75
            )

            angle_point = Point(0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH)
            top_point = Point(
                0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH
            ).related_point(
                90 - self._config.COLLET_HOLDER_ANGLE,
                self._config.COLLET_HOLDER_TOP_BENT_DEPTH,
            )
            angle_epansion_point = shifted_midpoint(
                angle_point,
                top_point,
                -self._config.COLLET_HOLDER_TOP_BENT_DEPTH / 2
                + self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH * 0.5,
            )
            angle_epansion_full = shifted_midpoint(
                angle_point,
                angle_epansion_point,
                0,
            )

            with BuildSketch(Location((0, 0, 0))):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            with BuildSketch(Location((0, 0, base_expansion_point.Y))):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            loft(ruled=True)
            with BuildSketch(Location((0, 0, base_expansion_point.Y))):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            with BuildSketch(Location((0, 0, base_expansion_full.Y))):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS * 1.1)
            with BuildSketch(
                Location((0, 0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH))
            ):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS * 1.1)
            with BuildSketch(
                Location((0, angle_epansion_full.X, angle_epansion_full.Y))
            ):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS * 1.1)
            with BuildSketch(
                Location((0, angle_epansion_point.X, angle_epansion_point.Y))
            ):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            loft(ruled=False)
            with BuildSketch(
                Location((0, angle_epansion_point.X, angle_epansion_point.Y))
            ):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            with BuildSketch(
                Location(
                    (
                        0,
                        Point(0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH)
                        .related_point(
                            90 - self._config.COLLET_HOLDER_ANGLE,
                            self._config.COLLET_HOLDER_TOP_BENT_DEPTH,
                        )
                        .X,
                        Point(0, self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH)
                        .related_point(
                            90 - self._config.COLLET_HOLDER_ANGLE,
                            self._config.COLLET_HOLDER_TOP_BENT_DEPTH,
                        )
                        .Y,
                    )
                )
            ):
                Circle(self._config.COLLET_HOLDER_TUBE_RADIUS)
            loft(ruled=True)
        channel.part.label = "tube channel"
        return channel.part

    def collet_holder(self) -> Part:
        cut_angle = 5
        with BuildPart() as holder:
            Box(
                self._config.COLLET_HOLDER_LENGTH,
                self._config.COLLET_HOLDER_WIDTH,
                self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH,
                align=[Align.MIN, Align.MIN, Align.MIN],
            )
            bottom_face_location = holder.faces().sort_by(Axis.Z)[0].center_location
            bottom_face_location.orientation = (0, 0, 180)
            with BuildPart(
                Location(
                    (
                        0,
                        self._config.COLLET_HOLDER_WIDTH,
                        self._config.COLLET_HOLDER_TOP_STRAIGHT_DEPTH,
                    ),
                    (self._config.COLLET_HOLDER_ANGLE, 0, 0),
                )
            ) as tipped:
                Box(
                    self._config.COLLET_HOLDER_LENGTH,
                    self._config.COLLET_HOLDER_WIDTH,
                    self._config.COLLET_HOLDER_TOP_BENT_DEPTH,
                    align=[Align.MIN, Align.MAX, Align.MIN],
                )
                topface_location = tipped.faces().sort_by(Axis.Z)[-1].center_location
                topface_location.orientation = (
                    180 + self._config.COLLET_HOLDER_ANGLE,
                    0,
                    0,
                )
                chamfer(
                    tipped.edges().sort_by(Axis.Z)[-1],
                    self._config.COLLET_HOLDER_CHAMFER_RADIUS,
                )
                with BuildPart(mode=Mode.SUBTRACT):
                    with BuildSketch(tipped.faces().sort_by(Axis.Y)[-1]):
                        with BuildLine():
                            Polyline(
                                (
                                    -self._config.COLLET_HOLDER_TOP_BENT_DEPTH / 2 + 6,
                                    -4.5,
                                ),
                                (
                                    -self._config.COLLET_HOLDER_TOP_BENT_DEPTH / 2 + 6,
                                    4.5,
                                ),
                                (
                                    -self._config.COLLET_HOLDER_TOP_BENT_DEPTH / 2
                                    + 0.5,
                                    0,
                                ),
                                close=True,
                            )
                        make_face()
                    extrude(amount=-0.5)
                with BuildPart(mode=Mode.SUBTRACT):
                    with BuildSketch(tipped.faces().sort_by(Axis.Y)[0]):
                        Text(
                            self._config.COLLET_HOLDER_REVISION,
                            font_size=8,
                            font="Flamante Round Bold",
                            align=(Align.CENTER, Align.MIN),
                            rotation=90,
                        )
                    extrude(amount=-0.5)

            with BuildPart(
                Location(
                    (
                        self._config.COLLET_HOLDER_LENGTH / 2 - 0.125,
                        self._config.COLLET_HOLDER_WIDTH / 2,
                        10.45,
                    ),
                    (90 + self._config.COLLET_HOLDER_ANGLE * 1.5 + cut_angle, 0, 0),
                ),
                mode=Mode.SUBTRACT,
            ):
                with GridLocations(42, 0, 2, 1):
                    add(self._screwcut())
            with BuildPart(bottom_face_location, mode=Mode.SUBTRACT):
                with GridLocations(
                    self._config.COLLET_HOLDER_TUBE_DISTANCE,
                    0,
                    5,
                    1,
                    align=[Align.CENTER, Align.CENTER, Align.MIN],
                ):
                    add(self._tube_channel())
            with BuildPart(topface_location, mode=Mode.ADD):
                with GridLocations(self._config.COLLET_HOLDER_TUBE_DISTANCE, 0, 5, 1):
                    add(
                        twist_snap_connector(connector_radius=3.5), rotation=(180, 0, 0)
                    )
                    Cylinder(
                        self._config.COLLET_HOLDER_TUBE_RADIUS,
                        4,
                        rotation=(180, 0, 0),
                        align=[Align.CENTER, Align.CENTER, Align.MIN],
                        mode=Mode.SUBTRACT,
                    )

            holder.part.color = Color("blue")
            holder.part.label = "New Collet Holder"
        return holder.part

    def compile(self):
        self.parts.clear()
        self.parts.append(
            AutomatablePart(self.collet_holder(), "mmu3_alternate_collet_holder")
        )


if __name__ == "__main__":
    mmu = AlternateColletHolder()
    mmu._config.stl_folder = "stl/"
    mmu.compile()
    mmu.display()
    mmu.export_stls()
