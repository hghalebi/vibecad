from build123d import *

# --- Main Body ---
# 40mm diameter, 10mm height, centered at origin
main_body = Cylinder(radius=20, height=10)

# --- Central Hub ---
# 20mm diameter (10mm radius), 15mm height
# Centered vertically with the main body center
hub = Cylinder(radius=10, height=15)

# --- Flanges ---
# 45mm diameter (22.5mm radius), 2mm thick
# One on each side of the main body (main body is 10mm tall, so ±5mm from center)
flange_bottom = Pos(0, 0, -5 - 1) * Cylinder(radius=22.5, height=2)  # bottom flange center at Z=-6
flange_top    = Pos(0, 0,  5 + 1) * Cylinder(radius=22.5, height=2)  # top flange center at Z=+6

# --- Bore ---
# 8mm diameter (4mm radius) through everything
bore = Cylinder(radius=4, height=20)  # tall enough to pass through hub

# --- Assemble ---
pulley = main_body + hub + flange_bottom + flange_top - bore

OBJ = pulley

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_pulley/render_1.png'

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
