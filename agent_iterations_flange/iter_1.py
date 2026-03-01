from build123d import *

# --- Parameters ---
flange_length = 50      # mm, each arm of the L
flange_width  = 50      # mm, depth of the bracket (into the page)
thickness     = 3       # mm, sheet metal thickness

# --- 2D L-shaped profile (in XZ plane) ---
# The L sits with its corner at the origin
# Outer points go to (50,0), (50,3), (3,3), (3,50), (0,50), (0,0)
pts = [
    (0, 0),
    (flange_length, 0),
    (flange_length, thickness),
    (thickness, thickness),
    (thickness, flange_length),
    (0, flange_length),
]

profile = Face.make_from_wires(Wire.make_polygon([Vector(p[0], p[1], 0) for p in pts]))

# Extrude along Y axis to give the bracket its depth
bracket = extrude(profile, flange_width)

OBJ = bracket

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations/render_1.png'

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
