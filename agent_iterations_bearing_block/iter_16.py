from build123d import *

with BuildPart() as pb:
    # Base plate: 100x30x10mm, centered at origin (Z from -5 to +5)
    Box(100, 30, 10)

    # Cylindrical housing: OD=50mm (r=25), height=40mm
    # Placed at Z=5 (top of base), growing upward
    with Locations((0, 0, 5)):
        Cylinder(25, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Find and fillet the circular edges at the housing-base junction
    # The cylinder (r=25) is wider than the base (Y=30), so the junction
    # is a partial arc — try small radii to find what works
    junction_edges = pb.part.edges().filter_by(GeomType.CIRCLE).filter_by_position(
        Axis.Z, 4.5, 5.5
    )
    for r in [2, 1.5, 1, 0.5]:
        try:
            fillet(junction_edges, radius=r)
            break
        except Exception:
            continue

    # Central bore: 30mm diameter (r=15), through entire housing + base
    with Locations((0, 0, -6)):
        Cylinder(15, 52, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)

    # Mounting holes: 10mm diameter (r=5), 80mm apart, through base
    with Locations((40, 0, -6), (-40, 0, -6)):
        Cylinder(5, 12, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)

OBJ = pb.part

OUTPUT_FILENAME = r'/home/joosep/mistral-hackathon/vibecad/agent_iterations_bearing_block/render_16.png'

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
