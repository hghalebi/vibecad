from build123d import *

# --- Base (centered at origin, Z from -5 to +5) ---
base = Box(100, 30, 10)

# --- Cylindrical Housing ---
# Housing from Z=+5 to Z=+45 => center at Z = +25
housing_outer = Cylinder(25, 40).translate((0, 0, 25))

# --- Union base + housing FIRST ---
pillow_block = base + housing_outer

# --- Fillet at the junction where housing meets base top (Z = +5) ---
# Try a smaller radius to avoid geometry failures
# Also try selecting edges more carefully - the bottom circular edge of the housing
junction_edges = pillow_block.edges().filter_by(GeomType.CIRCLE).filter_by_position(
    Axis.Z, 4.0, 6.0
)

# Use a smaller fillet radius to ensure success (3mm instead of 5mm)
pillow_block = pillow_block.fillet(3, junction_edges)

# --- Central bore (30mm diameter = 15mm radius, full height) ---
bore = Cylinder(15, 52).translate((0, 0, 20))

# --- Mounting holes (10mm diameter, 80mm apart, through base) ---
hole1 = Cylinder(5, 12).translate(( 40, 0, 0))
hole2 = Cylinder(5, 12).translate((-40, 0, 0))

# --- Subtract bore and mounting holes ---
pillow_block = pillow_block - bore - hole1 - hole2

OBJ = pillow_block

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_3.png'

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
