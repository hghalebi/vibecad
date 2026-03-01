from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (into the page / Z)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, from free outer edge of each flange
hole_pos1     = 12.5    # mm, along bracket depth (Y)
hole_pos2     = 37.5    # mm, along bracket depth (Y)

# --- 2D L-shaped profile (in XY plane) ---
# Horizontal flange: X=0..50, Y=0..3  (thickness along Y)
# Vertical flange:   X=0..3,  Y=0..50 (thickness along X)
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

# After extrusion:
# Horizontal flange: X=0..50, Y=0..3,  Z=0..50  (face normal along Y)
# Vertical flange:   X=0..3,  Y=0..50, Z=0..50  (face normal along X)

# --- Mounting holes ---

# Horizontal flange holes — drill through Y-axis (thickness direction of horizontal flange)
# Inset 9mm from free X-edge (X=50) → X = flange_length - hole_inset = 41
# Along depth at Y_pos=12.5 and 37.5 → these are Z positions
# Cylinder along Y, starting below Y=0, passing through Y=0..3
h_hole1 = (
    Pos(flange_length - hole_inset, 0, hole_pos1)
    * Rot(90, 0, 0)
    * Cylinder(hole_dia / 2, thickness * 4,
               align=(Align.CENTER, Align.CENTER, Align.MIN))
)
h_hole2 = (
    Pos(flange_length - hole_inset, 0, hole_pos2)
    * Rot(90, 0, 0)
    * Cylinder(hole_dia / 2, thickness * 4,
               align=(Align.CENTER, Align.CENTER, Align.MIN))
)

# Vertical flange holes — drill through X-axis (thickness direction of vertical flange)
# Inset 9mm from free Z-edge (Z=50) → Z = flange_width - hole_inset = 41
# Along depth at Z_pos=12.5 and 37.5 → these are Z positions
# Cylinder along X, starting at X=0, passing through X=0..3
v_hole1 = (
    Pos(0, hole_pos1, flange_width - hole_inset)
    * Rot(0, 90, 0)
    * Cylinder(hole_dia / 2, thickness * 4,
               align=(Align.CENTER, Align.CENTER, Align.MIN))
)
v_hole2 = (
    Pos(0, hole_pos2, flange_width - hole_inset)
    * Rot(0, 90, 0)
    * Cylinder(hole_dia / 2, thickness * 4,
               align=(Align.CENTER, Align.CENTER, Align.MIN))
)

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

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_6.png'

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
