from build123d import *
import math

# --- Base (centered at origin, Z from -5 to +5) ---
base = Box(100, 30, 10)

# --- Cylindrical Housing ---
# Housing from Z=+5 to Z=+45 => center at Z = +25
housing_outer = Cylinder(25, 40).translate((0, 0, 25))

# --- Union base + housing as a single solid ---
pillow_block = base + housing_outer

# --- Fillet approximation: add a chamfer-like ring at the junction ---
# Use a truncated cone (frustum) to blend the cylinder into the base
# This sits at Z=5 (base top), transitions from r=25+fillet_r to r=25 over fillet_r height
fillet_r = 5

# Cone frustum: bottom radius = 25+fillet_r, top radius = 25, height = fillet_r
# Positioned so bottom is at Z=5, top at Z=5+fillet_r
cone_blend = Cone(25 + fillet_r, 25, fillet_r).translate((0, 0, 5 + fillet_r / 2))

pillow_block = pillow_block + cone_blend

# --- Central bore (30mm diameter = 15mm radius, full height) ---
bore = Cylinder(15, 52).translate((0, 0, 20))

# --- Mounting holes (10mm diameter, 80mm apart, through base) ---
hole1 = Cylinder(5, 12).translate(( 40, 0, 0))
hole2 = Cylinder(5, 12).translate((-40, 0, 0))

# --- Subtract bore and mounting holes ---
pillow_block = pillow_block - bore - hole1 - hole2

# --- Ensure single solid output ---
all_solids = pillow_block.solids()
if len(all_solids) == 1:
    OBJ = all_solids[0]
else:
    # Fuse all solids into one
    merged = all_solids[0]
    for s in all_solids[1:]:
        merged = merged + s
    OBJ = merged.solids()[0]

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_12.png'

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
