from build123d import *

# --- Base (centered at origin, Z from -5 to +5) ---
base = Box(100, 30, 10)

# --- Cylindrical Housing ---
# Housing from Z=+5 to Z=+45 => center at Z = +25
housing_outer = Cylinder(25, 40).translate((0, 0, 25))

# --- Union base + housing ---
pillow_block = base + housing_outer

# --- Manual fillet blend using a revolved quarter-circle profile ---
# Fillet fills the concave corner between base top (Z=+5) and cylinder side (r=25)
fillet_r = 5  # 5mm fillet radius

# Arc center at (25 + fillet_r, 0, 5 + fillet_r) = (30, 0, 10)
# p1 is on the cylinder wall at Z = 5+fillet_r
# p2 is on the base top at r = 25+fillet_r
p1 = Vector(25, 0, 5 + fillet_r)           # on cylinder wall
p2 = Vector(25 + fillet_r, 0, 5)           # on base top
arc_center = Vector(25 + fillet_r, 0, 5 + fillet_r)

# Use make_three_point_arc with a midpoint on the arc
# Midpoint at 45 degrees: center + fillet_r * (cos(225°), 0, sin(225°))
import math
mid = Vector(
    arc_center.X + fillet_r * math.cos(math.radians(225)),
    0,
    arc_center.Z + fillet_r * math.sin(math.radians(225))
)

arc = Edge.make_three_point_arc(p1, mid, p2)

# Close the profile with straight lines to form a filled triangle-like region
line1 = Edge.make_line(p2, arc_center)
line2 = Edge.make_line(arc_center, p1)

profile_wire = Wire.make_wire([arc, line1, line2])
profile_face = Face.make_from_wires(profile_wire)

# Revolve 360 degrees around Z axis to create the fillet solid
fillet_solid = revolve(profile_face, Axis.Z, 360)

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

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_6.png'

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
