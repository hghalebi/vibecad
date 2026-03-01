from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (into the page)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, from outer edge (free end of flange)
hole_pos1     = 12.5    # mm, along flange depth (Z)
hole_pos2     = 37.5    # mm, along flange depth (Z)

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

# Extrude along Z axis — bracket depth
bracket = extrude(profile, flange_width)

# --- Mounting holes ---

# Horizontal flange (Y=0..3mm, top face at Y=3)
# Drill straight down along Y-axis through 3mm thickness
# Holes at X=12.5 & 37.5, inset 9mm from front face (Z=9), centered in thickness
h_hole1 = Pos(hole_pos1, 0, hole_inset) * Rot(90, 0, 0) * Cylinder(
    hole_dia / 2, thickness * 4,
    align=(Align.CENTER, Align.CENTER, Align.MIN))

h_hole2 = Pos(hole_pos2, 0, hole_inset) * Rot(90, 0, 0) * Cylinder(
    hole_dia / 2, thickness * 4,
    align=(Align.CENTER, Align.CENTER, Align.MIN))

# Vertical flange (X=0..3mm, outer face at X=0)
# Drill straight through along X-axis through 3mm thickness
# Holes at Z=12.5 & 37.5, inset 9mm from top free edge (Y = flange_length - hole_inset = 41)
v_hole1 = Pos(0, flange_length - hole_inset, hole_pos1) * Rot(0, 90, 0) * Cylinder(
    hole_dia / 2, thickness * 4,
    align=(Align.CENTER, Align.CENTER, Align.MIN))

v_hole2 = Pos(0, flange_length - hole_inset, hole_pos2) * Rot(0, 90, 0) * Cylinder(
    hole_dia / 2, thickness * 4,
    align=(Align.CENTER, Align.CENTER, Align.MIN))

bracket = bracket - [h_hole1, h_hole2, v_hole1, v_hole2]

# --- Inner corner fillet for stress relief ---
# Select the inner vertical edge at (X=3, Y=3) running along Z
inner_edges = bracket.edges().filter_by(Axis.Z).filter_by_position(
    Axis.X, thickness - 0.01, thickness + 0.01
).filter_by_position(
    Axis.Y, thickness - 0.01, thickness + 0.01
)

bracket = bracket.fillet(1.5, inner_edges)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_5.png'

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
