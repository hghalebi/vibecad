from build123d import *

# Build the pillow block bearing house using algebraic API
# Base: 100x30x10mm centered at origin (Z: -5 to +5)
# Housing: OD=50mm, H=40mm, sitting on top of base (Z: +5 to +45)
# Bore: 30mm diameter through housing and base
# Mounting holes: 10mm diameter, 80mm apart (at X=±40mm)

# Step 1: Base plate
base = Box(100, 30, 10)

# Step 2: Cylindrical housing on top of base
housing = Cylinder(25, 40).translate((0, 0, 25))

# Step 3: Union
pillow_block = base + housing

# Step 4: Apply fillet at junction (Z=+5) before subtractions
# Select edges at the junction plane between base top and housing bottom
junction_edges = pillow_block.edges().filter_by_position(Axis.Z, 4.8, 5.2)

# Apply the largest fillet that succeeds
for r in [5, 4, 3, 2, 1, 0.5]:
    try:
        pillow_block = pillow_block.fillet(r, junction_edges)
        break
    except Exception:
        # Re-select edges after failed attempt (object unchanged)
        junction_edges = pillow_block.edges().filter_by_position(Axis.Z, 4.8, 5.2)
        continue

# Step 5: Central bore - 30mm diameter through full height
bore = Cylinder(15, 56).translate((0, 0, 20))

# Step 6: Mounting holes - 10mm diameter, through base, at X=±40mm
hole1 = Cylinder(5, 22).translate(( 40, 0, 0))
hole2 = Cylinder(5, 22).translate((-40, 0, 0))

# Step 7: Subtract bore and holes
pillow_block = pillow_block - bore - hole1 - hole2

OBJ = pillow_block

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_21.png'

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
