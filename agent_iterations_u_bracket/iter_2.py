from build123d import *

# U-bracket dimensions
width = 40    # X direction
depth = 40    # Y direction
height = 40   # Z direction
thickness = 2 # material thickness

wall_height = height - thickness  # 38mm so total height = 38 + 2 = 40mm

# --- Base plate (bottom of the U) ---
base = Box(width, depth, thickness)

# --- Left wall ---
left_wall = Pos(-width/2 + thickness/2, 0, thickness/2 + wall_height/2) * Box(thickness, depth, wall_height)

# --- Right wall ---
right_wall = Pos(width/2 - thickness/2, 0, thickness/2 + wall_height/2) * Box(thickness, depth, wall_height)

# Combine into U-shape
u_bracket = base + left_wall + right_wall

# --- Hole in center of base (10mm diameter) ---
hole = Cylinder(5, thickness * 3)  # radius=5 → 10mm dia, tall enough to pierce base
u_bracket = u_bracket - hole

OBJ = u_bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_u_bracket/render_2.png'

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
