from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (Z direction)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, inset from all free edges

# Hole positions along Z (bracket depth): inset from both ends
z1 = hole_inset                  # 9mm from front face
z2 = flange_width - hole_inset   # 41mm from front face

# Hole positions along flange arm: inset from free end
x1 = hole_inset                  # 9mm from free end of horizontal flange
x2 = flange_length - hole_inset  # 41mm (9mm from corner end)

# --- 2D L-shaped profile (in XY plane) ---
# Horizontal flange: X=0..50, Y=0..3
# Vertical flange:   X=0..3,  Y=0..50
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
bracket = extrude(profile, flange_width)

# =============================================================================
# MOUNTING HOLES — 2 per flange face, 4 total
# Each hole is inset 9mm from the free edge AND 9mm from the front/back face
# =============================================================================
hole_r    = hole_dia / 2
drill_len = thickness * 4   # generous to guarantee full penetration

# --- Horizontal flange holes (Y=0..3, drill along Y via Rot(90,0,0)) ---
# 2 holes: at (x1, z1) and (x2, z2) — diagonally spread across the flange face
h_holes = [
    Pos(x1, thickness / 2, z1) * Rot(90, 0, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    Pos(x2, thickness / 2, z2) * Rot(90, 0, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
]

# --- Vertical flange holes (X=0..3, drill along X via Rot(0,90,0)) ---
# 2 holes: at (y1, z1) and (y2, z2) — diagonally spread across the flange face
y1 = hole_inset
y2 = flange_length - hole_inset

v_holes = [
    Pos(thickness / 2, y1, z1) * Rot(0, 90, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    Pos(thickness / 2, y2, z2) * Rot(0, 90, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
]

bracket = bracket - h_holes - v_holes

# =============================================================================
# INNER CORNER FILLET — stress relief at the bend
# =============================================================================
inner_edges = (
    bracket.edges()
    .filter_by(Axis.Z)
    .filter_by_position(Axis.X, thickness - 0.01, thickness + 0.01)
    .filter_by_position(Axis.Y, thickness - 0.01, thickness + 0.01)
)
bracket = bracket.fillet(1.5, inner_edges)

# =============================================================================
# OUTER EDGE FILLETS — deburring, industry-standard sheet metal practice
# =============================================================================
outer_edges = ShapeList(
    e for e in bracket.edges().filter_by(Axis.Z)
    if (
        abs(e.center().X) < 0.01                        # X=0 outer corner
        or abs(e.center().X - flange_length) < 0.01     # X=50 outer corner
        or abs(e.center().Y - flange_length) < 0.01     # Y=50 outer corner
    )
)
bracket = bracket.fillet(0.5, outer_edges)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_14.png'

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
