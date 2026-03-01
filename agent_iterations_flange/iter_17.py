from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (Z direction)
thickness     = 3       # mm, sheet metal thickness
hole_dia      = 5       # mm, M4 clearance hole
hole_inset    = 9       # mm, inset from front/back faces along Z

# Hole Z positions: inset from both ends of the 50mm depth
z1 = hole_inset                  # 9mm from front face
z2 = flange_width - hole_inset   # 41mm from front face (9mm from back)

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
# MOUNTING HOLES — 2 per flange, 4 total
# Centred on each flange width, spaced 9mm from front and back faces
# =============================================================================
hole_r    = hole_dia / 2
drill_len = thickness * 4

# Horizontal flange holes — centred at X=25, drill through Y, at Z=9 and Z=41
h_holes = [
    Pos(flange_length / 2, thickness / 2, z1) * Rot(90, 0, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    Pos(flange_length / 2, thickness / 2, z2) * Rot(90, 0, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
]

# Vertical flange holes — centred at Y=25, drill through X, at Z=9 and Z=41
v_holes = [
    Pos(thickness / 2, flange_length / 2, z1) * Rot(0, 90, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    Pos(thickness / 2, flange_length / 2, z2) * Rot(0, 90, 0) * Cylinder(
        hole_r, drill_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)),
]

bracket = bracket - h_holes - v_holes

# =============================================================================
# INNER CORNER FILLET — stress relief at the bend (1.5mm)
# =============================================================================
inner_edges = (
    bracket.edges()
    .filter_by(Axis.Z)
    .filter_by_position(Axis.X, thickness - 0.01, thickness + 0.01)
    .filter_by_position(Axis.Y, thickness - 0.01, thickness + 0.01)
)
bracket = bracket.fillet(1.5, inner_edges)

# =============================================================================
# OUTER EDGE FILLETS — deburring, industry-standard sheet metal practice (0.5mm)
# =============================================================================
outer_edges = ShapeList(
    e for e in bracket.edges().filter_by(Axis.Z)
    if (
        abs(e.center().X) < 0.01
        or abs(e.center().X - flange_length) < 0.01
        or abs(e.center().Y - flange_length) < 0.01
    )
)
bracket = bracket.fillet(0.5, outer_edges)

# =============================================================================
# HOLE RIM FILLETS — deburr hole entry edges (0.3mm)
# =============================================================================
hole_edges = ShapeList(
    e for e in bracket.edges()
    if e.geom_type == GeomType.CIRCLE and abs(e.radius - hole_r) < 0.01
)
bracket = bracket.fillet(0.3, hole_edges)

# =============================================================================
# EXPORT — manufacturing handoff
# =============================================================================
export_step(bracket, "L_bracket_50x50x3mm.step")
export_stl(bracket, "L_bracket_50x50x3mm.stl")

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_17.png'

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
