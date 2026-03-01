from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (Z direction)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, from free outer edge of each flange
hole_z1       = 12.5    # mm, first hole position along Z (bracket depth)
hole_z2       = 37.5    # mm, second hole position along Z (bracket depth)

# --- 2D L-shaped profile (in XY plane) ---
# Horizontal flange: X=0..50, Y=0..3  (free end at X=50, thickness along Y)
# Vertical flange:   X=0..3,  Y=0..50 (free end at Y=50, thickness along X)
pts = [
    (0, 0),
    (flange_length, 0),
    (flange_length, thickness),
    (thickness, thickness),
    (thickness, flange_length),
    (0, flange_length),
    (0, 0),
]

wire = Wire.make_polygon([Vector(p[0], p[1], 0) for p in pts])
profile = make_face(wire)

# Extrude along Z axis — bracket depth (50mm)
bracket = extrude(profile, flange_width)

# =============================================================================
# MOUNTING HOLES
# =============================================================================
# Horizontal flange geometry: X=0..50, Y=0..3, Z=0..50
#   - Hole axis: Y direction (perpendicular to top/bottom face)
#   - X position: inset 9mm from free end (X=50) → X = 41
#   - Z positions: 12.5 and 37.5 (along bracket depth)
#   - Cylinder must span Y=-1 to Y=4 to fully pierce 3mm wall
#
# Vertical flange geometry: X=0..3, Y=0..50, Z=0..50
#   - Hole axis: X direction (perpendicular to left/right face)
#   - Y position: inset 9mm from free end (Y=50) → Y = 41
#   - Z positions: 12.5 and 37.5 (along bracket depth)
#   - Cylinder must span X=-1 to X=4 to fully pierce 3mm wall

# Build a helper: a cylinder aligned to Y axis, long enough to pierce 3mm wall
# Rot(90,0,0) rotates the default Z-axis cylinder to point along Y
def y_hole(x, z):
    """Cylinder piercing through Y=0..3 at given X, Z"""
    return (
        Pos(x, -1, z)
        * Rot(90, 0, 0)
        * Cylinder(hole_dia / 2, thickness + 2,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
    )

# Build a helper: a cylinder aligned to X axis
# Rot(0,-90,0) rotates the default Z-axis cylinder to point along X
def x_hole(y, z):
    """Cylinder piercing through X=0..3 at given Y, Z"""
    return (
        Pos(-1, y, z)
        * Rot(0, -90, 0)
        * Cylinder(hole_dia / 2, thickness + 2,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
    )

# Horizontal flange: 2 holes, X=41, Z=12.5 and Z=37.5
h_hole1 = y_hole(flange_length - hole_inset, hole_z1)
h_hole2 = y_hole(flange_length - hole_inset, hole_z2)

# Vertical flange: 2 holes, Y=41, Z=12.5 and Z=37.5
v_hole1 = x_hole(flange_length - hole_inset, hole_z1)
v_hole2 = x_hole(flange_length - hole_inset, hole_z2)

bracket = bracket - [h_hole1, h_hole2, v_hole1, v_hole2]

# --- Inner corner fillet for stress relief ---
# The inner vertical edge runs along Z at (X=3, Y=3)
inner_edges = (
    bracket.edges()
    .filter_by(Axis.Z)
    .filter_by_position(Axis.X, thickness - 0.01, thickness + 0.01)
    .filter_by_position(Axis.Y, thickness - 0.01, thickness + 0.01)
)

bracket = bracket.fillet(1.5, inner_edges)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_9.png'

import build123d as bd
import pyvista as pv
import numpy as np
import os

pv.start_xvfb()

def _render_to_png(obj, filename):
    try:
        verts, triangles = obj.tessellate(tolerance=0.1)
    except:
        verts, triangles = bd.Compound(children=[obj]).tessellate(tolerance=0.1)
        
    def _to_tuple(v):
        if hasattr(v, "X"): return (v.X, v.Y, v.Z)
        return tuple(v)

    pv_verts = np.array([_to_tuple(v) for v in verts])
    pv_faces = np.hstack([[3, *t] for t in triangles])
    mesh = pv.PolyData(pv_verts, pv_faces)
    
    edges_poly = mesh.extract_feature_edges(boundary_edges=True, feature_edges=True, manifold_edges=True)

    plotter = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(800, 800))
    
    views = [
        ("Isometric", None),
        ("Front", None),
        ("Top", None),
        ("Right", None),
    ]
    
    for i, (name, _) in enumerate(views):
        plotter.subplot(i // 2, i % 2)
        plotter.add_text(name, font_size=12, color="black")
        plotter.add_mesh(mesh, color="lightblue", smooth_shading=True, specular=0.5, ambient=0.3)
        
        if edges_poly:
            plotter.add_mesh(edges_poly, color="black", line_width=2)
            
        plotter.add_axes()
        plotter.show_grid(color='gray')
        plotter.set_background("white")
        
        if name == "Isometric":
            plotter.view_isometric()
        elif name == "Front":
            plotter.view_xz() 
            plotter.camera.up = (0, 0, 1)
        elif name == "Top":
            plotter.view_xy()
        elif name == "Right":
            plotter.view_yz()
            plotter.camera.up = (0, 0, 1)
            
        plotter.reset_camera()

    plotter.screenshot(filename)
    plotter.close()

_render_to_png(OBJ, OUTPUT_FILENAME)
