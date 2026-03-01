from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (Z direction)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, inset from free outer edge of each flange arm
mid_depth     = flange_width / 2  # 25mm — single row of holes at mid-depth

# --- 2D L-shaped profile (in XY plane) ---
# Horizontal flange: X=0..50, Y=0..3
# Vertical flange:   X=0..3,  Y=3..50
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
# MOUNTING HOLES — 2 per flange, 4 total
# =============================================================================
#
# Horizontal flange: X=0..50, Y=0..3, Z=0..50
#   Holes pierce through Y (the 3mm thickness)
#   X positions: hole_inset=9 and flange_length-hole_inset=41
#   Z position: mid_depth=25 (single row centred on bracket depth)
#   Cylinder axis = Y → Rot(90, 0, 0)
#
# Vertical flange: X=0..3, Y=0..50, Z=0..50
#   Holes pierce through X (the 3mm thickness)
#   Y positions: hole_inset=9 and flange_length-hole_inset=41
#   Z position: mid_depth=25 (single row centred on bracket depth)
#   Cylinder axis = X → Rot(0, -90, 0)

def h_hole(x_pos):
    """Through-hole in horizontal flange, piercing Y=0..3"""
    return (
        Pos(x_pos, -1, mid_depth)
        * Rot(90, 0, 0)
        * Cylinder(hole_dia / 2, thickness + 2,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
    )

def v_hole(y_pos):
    """Through-hole in vertical flange, piercing X=0..3"""
    return (
        Pos(-1, y_pos, mid_depth)
        * Rot(0, -90, 0)
        * Cylinder(hole_dia / 2, thickness + 2,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
    )

# Horizontal flange: holes at X=9 and X=41, both at Z=25
h_hole1 = h_hole(hole_inset)
h_hole2 = h_hole(flange_length - hole_inset)

# Vertical flange: holes at Y=9 and Y=41, both at Z=25
v_hole1 = v_hole(hole_inset)
v_hole2 = v_hole(flange_length - hole_inset)

bracket = bracket - [h_hole1, h_hole2, v_hole1, v_hole2]

# --- Inner corner fillet for stress relief ---
# The inner vertical edge runs along Z at (X=thickness, Y=thickness)
inner_edges = (
    bracket.edges()
    .filter_by(Axis.Z)
    .filter_by_position(Axis.X, thickness - 0.01, thickness + 0.01)
    .filter_by_position(Axis.Y, thickness - 0.01, thickness + 0.01)
)

bracket = bracket.fillet(1.5, inner_edges)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_10.png'

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
