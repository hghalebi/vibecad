from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (Z direction)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, inset from free outer edge of each flange arm
mid_z         = flange_width / 2  # 25mm — holes centred along bracket depth

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
# MOUNTING HOLES
# =============================================================================
# Strategy: use Plane objects to define the drill direction unambiguously.
#
# Horizontal flange top face is at Y=3, normal = +Y.
# We extrude a circle downward through the 3mm wall.
# Use Plane with origin on the face, normal along Y.
#
# Vertical flange outer face is at X=3, normal = +X.
# We extrude a circle inward through the 3mm wall.

hole_r = hole_dia / 2
drill_len = thickness + 4   # longer than wall to guarantee clean cut

# --- Horizontal flange holes ---
# Face at Y=thickness, normal +Y. Drill from Y=thickness downward (negative Y).
# Hole centres: X=hole_inset and X=flange_length-hole_inset, Z=mid_z
for hx in [hole_inset, flange_length - hole_inset]:
    plane = Plane(origin=(hx, thickness, mid_z), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    cyl = plane * Cylinder(hole_r, drill_len,
                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    bracket = bracket - cyl

# --- Vertical flange holes ---
# Face at X=thickness, normal +X. Drill from X=thickness inward (negative X).
# Hole centres: Y=hole_inset and Y=flange_length-hole_inset, Z=mid_z
for hy in [hole_inset, flange_length - hole_inset]:
    plane = Plane(origin=(thickness, hy, mid_z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    cyl = plane * Cylinder(hole_r, drill_len,
                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    bracket = bracket - cyl

# --- Inner corner fillet for stress relief ---
inner_edges = (
    bracket.edges()
    .filter_by(Axis.Z)
    .filter_by_position(Axis.X, thickness - 0.01, thickness + 0.01)
    .filter_by_position(Axis.Y, thickness - 0.01, thickness + 0.01)
)
bracket = bracket.fillet(1.5, inner_edges)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_11.png'

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
