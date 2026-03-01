# BASE_CODE is now just a placeholder. 
# The script will load a random example from the examples directory.
BASE_CODE = """from build123d import *

length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex3:
    with BuildSketch() as ex3_sk:
        Circle(width)
        Rectangle(length / 2, width / 2, mode=Mode.SUBTRACT)
    extrude(amount=2 * thickness)
"""

RENDER_TEMPLATE = """
import build123d as bd
import pyvista as pv
import numpy as np
import os

# Capture logic to find the object to render
def _find_captured_obj():
    builders = []
    others = []
    for name, obj in list(globals().items()):
        if name.startswith("_"): continue
        if isinstance(obj, (bd.BuildPart, bd.BuildSketch, bd.BuildLine)):
            builders.append(obj)
        elif isinstance(obj, (bd.Part, bd.Sketch, bd.Curve, bd.Compound, bd.Solid, bd.Face, bd.Wire, bd.Edge)):
            others.append(obj)

    if builders:
        parts = [b for b in builders if isinstance(b, bd.BuildPart)]
        if parts: return parts[-1].part
        sketches = [b for b in builders if isinstance(b, bd.BuildSketch)]
        if sketches: return sketches[-1].sketch
        lines = [b for b in builders if isinstance(b, bd.BuildLine)]
        if lines: return lines[-1].line

    if others:
        parts = [o for o in others if isinstance(o, (bd.Part, bd.Solid, bd.Compound))]
        if parts: return parts[-1]
        sketches = [o for o in others if isinstance(o, (bd.Sketch, bd.Face))]
        if sketches: return sketches[-1]
        return others[-1]

    return None

_captured_obj = _find_captured_obj()

if _captured_obj is None:
    raise Exception("Could not find a build123d object to render.")

def _render_to_png(obj, filename):
    # Prepare mesh for shading
    try:
        verts, triangles = obj.tessellate(tolerance=0.1)
    except:
        # Fallback for complex objects
        verts, triangles = bd.Compound(children=[obj]).tessellate(tolerance=0.1)
        
    def _to_tuple(v):
        if hasattr(v, "X"): return (v.X, v.Y, v.Z)
        return tuple(v)

    pv_verts = np.array([_to_tuple(v) for v in verts])
    pv_faces = np.hstack([[3, *t] for t in triangles])
    mesh = pv.PolyData(pv_verts, pv_faces)
    
    # Prepare edges for wireframe
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
        
        # Shaded part
        plotter.add_mesh(mesh, color="lightblue", smooth_shading=True, specular=0.5, ambient=0.3)
        
        # CAD Edges (will be masked by mesh if behind it)
        if edges_poly:
            plotter.add_mesh(edges_poly, color="black", line_width=2)
            
        plotter.add_axes()
        plotter.show_grid(color='gray')
        plotter.set_background("white")
        
        # Set view
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

_render_to_png(_captured_obj, OUTPUT_FILENAME)
"""

PROPOSAL_PROMPT = """You are a world-class CAD engineer specializing in build123d.
Your goal is to propose a clear, well-defined 3D modeling task and implement it.

### Step 1: Analysis
Look at the following build123d script and the 4-view render.
Identify the main body and its approximate dimensions.
Determine the coordinate system: X=Red, Y=Green, Z=Blue.

### Step 2: Planning
Choose a strategy from this list: {strategy}
Describe EXACTLY where the change will occur.
Identify the target face/edge using ROBUST SELECTORS.
**Do not use indices like `faces()[2]`!** Indices are fragile and likely to be wrong.
Instead, use selectors like:
- `faces().sort_by(Axis.Z)[-1]` (Top face)
- `faces().sort_by(Axis.X)[0]` (Left face)
- `faces().filter_by(GeomType.PLANE).sort_by(Axis.Y)[-1]` (Plane parallel to XZ, furthest in +Y)
- `edges().sort_by(Axis.Z)[-1]` (Highest edges)

### Step 3: Implementation
Write the updated build123d code.
Ensure you use the robust selectors you identified in the planning phase.

Base Code:
```python
{base_code}
```

Output strictly in JSON format matching this schema:
{{
  "analysis": "Brief analysis of the current geometry and coordinate system",
  "plan": "Detailed description of the proposed change and the selectors to be used",
  "user_prompt": "The natural language instruction",
  "explanation": "Brief technical explanation of the change",
  "task_type": "one of: feature_addition, geometric_variation, dimension_modification, subtractive_geometry",
  "edits": [
    {{
      "search": "exact string from base code to replace",
      "replace": "the new string to insert"
    }}
  ],
  "new_code": "Provide the ENTIRE new file code here. This is MANDATORY."
}}"""

FIX_PROMPT = """You are an expert in python and build123d. 
You previously proposed a change that failed.
The render includes a grid and axes (X=Red, Y=Green, Z=Blue) to help you debug placement. Solid parts are shown in light blue with black CAD edges.

User Request: "{user_prompt}"
Task Type: "{task_type}"

Base Code (original):
```python
{base_code}
```

Failed Code (the code that produced the error or was rejected):
```python
{failed_code}
```

Failed Edits (if any):
{failed_edits}

Error Message / Feedback:
```
{error_message}
```

Please provide a CORRECTED version of the change.
Output strictly in JSON format matching this schema:
{{
  "explanation": "Brief technical explanation of the fix",
  "edits": [
    {{
      "search": "exact string from base code to replace",
      "replace": "the new string to insert"
    }}
  ],
  "new_code": "Alternatively, provide the ENTIRE new file code"
}}"""

VALIDATION_PROMPT = """You are a strict CAD validation expert. 
A CAD agent was tasked with: "{user_prompt}"

Image 1: Original model (4 views: Isometric, Front, Top, Right with coordinate axes: X=Red, Y=Green, Z=Blue, and a gray grid).
Image 2: Modified model (same views, grid, and coloring).

Your goal is to verify if the modification is exactly as requested and if the rest of the model remains intact.
1. Check if the new features are present and correctly positioned according to the prompt.
2. Verify that NO unintended changes were made to the original geometry.
3. Use the grid and axes to ensure dimensions and placement are correct.

Be highly critical. If there are any discrepancies, missing features, or unintended distortions, you must conclude with FAIL.
Provide a detailed step-by-step analysis of the changes you observe.
Conclude with EXACTLY the word "SUCCESS" or "FAIL" on a new line."""

MUTATION_PROMPT = """You are a world-class CAD engineer specializing in build123d.
Your goal is to modify an existing build123d script to add a new, meaningful feature or modification.

### Guidelines:
1. **Variety**: Choose a modification like adding or removing a hole, a fillet, a chamfer, a pocket, a boss, or modifying a key dimension.
2. **Robustness**: Use ROBUST SELECTORS (e.g., `faces().sort_by(Axis.Z)[-1]`) instead of indices.
3. **Visibility**: Ensure the change is clearly visible in a standard 4-view render (Isometric, Front, Top, Right).
4. **Complexity**: Aim for a single, well-defined change that an engineer might realistically ask for.

Base Code:
```python
{base_code}
```

Suggested Strategy: {strategy}

Output strictly in JSON format matching this schema:
{{
  "analysis": "Brief analysis of the current geometry",
  "mutation_plan": "Description of the change you will make",
  "new_code": "The ENTIRE new file code",
  "task_type": "one of: feature_addition, geometric_variation, dimension_modification, subtractive_geometry"
}}"""

INVERSE_LABEL_PROMPT = """You are a CAD instructor. Your task is to look at a "Before" and "After" state of a 3D model and write the EXACT instruction that a user would have given to achieve this change.

### Context:
- **Image 1**: The "Before" state.
- **Image 2**: The "After" state.
- **Geometric Metrics Change**:
{metrics_diff}
- **Code Diff**:
```diff
{code_diff}
```

### Goal:
Write a concise, professional, and unambiguous natural language instruction (1-2 sentences) that describes the modification. The instruction should be specific enough that a CAD expert could replicate the change just by reading it. Mention specific faces (e.g., "top face", "side face furthest in +X") or dimensions where appropriate.

Output strictly in JSON format matching this schema:
{{
  "instruction": "The natural language instruction",
  "technical_summary": "A brief technical summary of what was changed"
}}"""

COT_MUTATION_PROMPT = """You are a world-class CAD engineer specializing in build123d.
Your goal is to modify an existing build123d script by adding or subtracting a simple primitive shape using boolean operations.

### Chain of Thought Process:
1. **Analyze Current Geometry**: What are the main features and dimensions?
2. **Identify Target Face**: Which face will you modify? Use robust selectors (e.g., `.sort_by(Axis.Z)[-1]`).
3. **Choose Primitive**: Select a simple shape (Box, Cylinder, Sphere) to add or subtract.
4. **Define Parameters**: What are the dimensions and position of the new primitive?
5. **Determine Mode**: Should it be added (`Mode.ADD`) or subtracted (`Mode.SUBTRACT`)?
6. **Code Synthesis**: Write the final code.

Base Code:
```python
{base_code}
```

Suggested Strategy: {strategy}

Output strictly in JSON format matching this schema:
{{
  "thought": "Your step-by-step chain of thought reasoning",
  "analysis": "Brief analysis of the current geometry",
  "mutation_plan": "Description of the change you will make",
  "new_code": "The ENTIRE new file code",
  "task_type": "one of: feature_addition, geometric_variation, dimension_modification, subtractive_geometry"
}}"""

COT_LABEL_PROMPT = """You are a CAD instructor. Compare the "Before" and "After" states of a 3D model and write the EXACT instruction that a user would have given to achieve this change.

### Context:
- **Image 1**: The "Before" state.
- **Image 2**: The "After" state.
- **Geometric Metrics Change**:
{metrics_diff}
- **Code Diff**:
```diff
{code_diff}
```

### Chain of Thought Process:
1. **Observation**: What is the most obvious difference between the images?
2. **Detailed Comparison**: 
   - Is a feature added or removed?
   - What is its shape (circular, rectangular, etc.)?
   - Where is it located relative to the original body and axes?
   - What are its approximate dimensions?
3. **Synthesis**: Combine these observations into a clear, professional instruction.

Output strictly in JSON format matching this schema:
{{
  "thought": "Your step-by-step chain of thought reasoning",
  "instruction": "The final natural language instruction",
  "technical_summary": "A brief technical summary of what was changed"
}}"""
