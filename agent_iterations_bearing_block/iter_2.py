from build123d import *

# --- Base (centered at origin, Z from -5 to +5) ---
base = Box(100, 30, 10)

# --- Cylindrical Housing ---
# Housing outer diameter = 50mm (radius=25), height = 40mm
# Should rise from base bottom (Z=-5) to Z=+35
# Cylinder is centered by default, so center at Z = (-5 + 35) / 2 = +15
# But we want it to sit ON TOP of the base, starting at Z=+5
# Housing from Z=+5 to Z=+45 => center at Z = (5+45)/2 = +25
housing_outer = Cylinder(25, 40).translate((0, 0, 25))

# --- Union base + housing FIRST, then fillet the junction ---
pillow_block = base + housing_outer

# --- Fillet at the junction where housing meets base top (Z = +5) ---
# The circular edge at Z=+5 is where the cylinder base meets the top of the base plate
junction_edges = pillow_block.edges().filter_by(GeomType.CIRCLE).filter_by_position(
    Axis.Z, 4.5, 5.5
)
pillow_block = pillow_block.fillet(5, junction_edges)

# --- Central bore (30mm diameter = 15mm radius, full height) ---
# Bore must go through entire housing + base: from Z=-6 to Z=+46
bore = Cylinder(15, 52).translate((0, 0, 20))

# --- Mounting holes (10mm diameter, 80mm apart, through base) ---
hole1 = Cylinder(5, 12).translate(( 40, 0, 0))
hole2 = Cylinder(5, 12).translate((-40, 0, 0))

# --- Subtract bore and mounting holes ---
pillow_block = pillow_block - bore - hole1 - hole2

OBJ = pillow_block

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_2.png'

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
