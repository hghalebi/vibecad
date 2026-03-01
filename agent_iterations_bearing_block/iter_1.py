from build123d import *

# --- Base ---
base = Box(100, 30, 10)

# --- Cylindrical Housing (centered on base, rising from bottom) ---
# Housing outer diameter = 50mm, total height from base bottom = 40mm
# So housing extends 30mm above the base top (base is 10mm tall)
housing_outer = Cylinder(25, 40)  # radius=25, height=40
# Move housing so its bottom aligns with base bottom (Z=0 in centered coords)
# Box is centered at origin: Z goes from -5 to +5
# Cylinder centered at origin: Z goes from -20 to +20
# We want cylinder bottom at Z=-5, so shift up by 15
housing_outer = housing_outer.translate((0, 0, 15))

# --- Central bore (30mm diameter = 15mm radius, full height) ---
bore = Cylinder(15, 42)  # slightly taller to ensure clean cut
bore = bore.translate((0, 0, 15))

# --- Mounting holes (10mm diameter = 5mm radius, 80mm apart, through base) ---
hole1 = Cylinder(5, 12).translate((40, 0, 0))   # +40mm from center
hole2 = Cylinder(5, 12).translate((-40, 0, 0))  # -40mm from center

# --- Combine ---
pillow_block = base + housing_outer - bore - hole1 - hole2

OBJ = pillow_block

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_1.png'

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
