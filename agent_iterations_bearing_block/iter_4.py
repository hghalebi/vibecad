from build123d import *

# --- Base (centered at origin, Z from -5 to +5) ---
base = Box(100, 30, 10)

# --- Cylindrical Housing ---
# Housing from Z=+5 to Z=+45 => center at Z = +25
housing_outer = Cylinder(25, 40).translate((0, 0, 25))

# --- Union base + housing ---
pillow_block = base + housing_outer

# --- Manual fillet blend at junction using a swept torus quarter-circle profile ---
# Create a quarter-circle fillet profile revolved 360 degrees
# The fillet sits at the base of the cylinder (radius=25) at Z=+5
# It fills the concave corner between the flat base top and the cylinder side
fillet_r = 5  # 5mm fillet radius

# Quarter circle profile: center of arc at (25+fillet_r, 0, 5+fillet_r) = (30, 0, 10)
# Arc goes from (30, 0, 5) to (25, 0, 10) — filling the corner
fillet_profile = (
    Circle(fillet_r, plane=Plane.XZ)
    .translate((25 + fillet_r, 0, 5 + fillet_r))
)

# Make it a face and revolve
fillet_face = make_face(fillet_profile)

# We want the solid quarter that fills the concave corner
# Revolve the face 360 degrees around Z axis
fillet_torus = revolve(fillet_face, Axis.Z, 360)

# Subtract the quarter-circle solid from the torus to get just the fillet material
# The fillet material is the torus minus the cylinder and minus the half-space above Z=5
inner_cyl = Cylinder(25 + fillet_r, 20).translate((0, 0, 5 + 10))
above_plane = Box(200, 200, 20).translate((0, 0, 5 + 10))
outer_cyl_cut = Cylinder(25, 20).translate((0, 0, 5 + 10))

fillet_solid = fillet_torus - above_plane - outer_cyl_cut

# Add fillet blend to pillow block
pillow_block = pillow_block + fillet_solid

# --- Central bore (30mm diameter = 15mm radius, full height) ---
bore = Cylinder(15, 52).translate((0, 0, 20))

# --- Mounting holes (10mm diameter, 80mm apart, through base) ---
hole1 = Cylinder(5, 12).translate(( 40, 0, 0))
hole2 = Cylinder(5, 12).translate((-40, 0, 0))

# --- Subtract bore and mounting holes ---
pillow_block = pillow_block - bore - hole1 - hole2

OBJ = pillow_block

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_4.png'

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
