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
import math

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
    raise Exception(\"Could not find a build123d object to render.\")

views = {
    \"Isometric\": ((100, -100, 100), (0, 0, 1)),
    \"Front\": ((0, -100, 0), (0, 0, 1)),
    \"Top\": ((0, 0, 100), (0, 1, 0)),
    \"Right\": ((100, 0, 0), (0, 0, 1)),
}

all_visible = []
all_hidden = []
all_labels = []
grid_visible = []

obj_bb = _captured_obj.bounding_box()
obj_size = max(obj_bb.size.X, obj_bb.size.Y, obj_bb.size.Z)
spacing = 1.5 * obj_size if obj_size > 0 else 150

# Determine grid step
if obj_size > 0:
    grid_step = 10 ** math.floor(math.log10(obj_size / 5))
    if obj_size / grid_step > 15: grid_step *= 5
    elif obj_size / grid_step < 3: grid_step /= 2
else:
    grid_step = 10
grid_count = 10

# Add axes
axes_size = obj_size * 0.2 if obj_size > 0 else 20
x_axis = bd.Edge.make_line((0,0,0), (axes_size, 0, 0))
y_axis = bd.Edge.make_line((0,0,0), (0, axes_size, 0))
z_axis = bd.Edge.make_line((0,0,0), (0, 0, axes_size))
axes_visible = {\"X\": [], \"Y\": [], \"Z\": []}

for i, (name, (origin, up)) in enumerate(views.items()):
    try:
        visible, hidden = _captured_obj.project_to_viewport(origin, viewport_up=up)
    except:
        temp_comp = bd.Compound(children=[_captured_obj])
        visible, hidden = temp_comp.project_to_viewport(origin, viewport_up=up)

    col = i % 2
    row = i // 2
    translation = bd.Pos(col * spacing, -row * spacing)
    
    all_visible.extend([s.moved(translation) for s in visible])
    all_hidden.extend([s.moved(translation) for s in hidden])
    
    # Project grid
    g_lines = []
    if name in [\"Top\", \"Isometric\"]:
        g_lines = [bd.Edge.make_line((j*grid_step, -grid_count*grid_step, 0), (j*grid_step, grid_count*grid_step, 0)) for j in range(-grid_count, grid_count + 1)] + \\
                  [bd.Edge.make_line((-grid_count*grid_step, j*grid_step, 0), (grid_count*grid_step, j*grid_step, 0)) for j in range(-grid_count, grid_count + 1)]
    elif name == \"Front\":
        g_lines = [bd.Edge.make_line((j*grid_step, 0, -grid_count*grid_step), (j*grid_step, 0, grid_count*grid_step)) for j in range(-grid_count, grid_count + 1)] + \\
                  [bd.Edge.make_line((-grid_count*grid_step, 0, j*grid_step), (grid_count*grid_step, 0, j*grid_step)) for j in range(-grid_count, grid_count + 1)]
    elif name == \"Right\":
        g_lines = [bd.Edge.make_line((0, j*grid_step, -grid_count*grid_step), (0, j*grid_step, grid_count*grid_step)) for j in range(-grid_count, grid_count + 1)] + \\
                  [bd.Edge.make_line((0, -grid_count*grid_step, j*grid_step), (0, grid_count*grid_step, j*grid_step)) for j in range(-grid_count, grid_count + 1)]
    
    if g_lines:
        vg, _ = bd.Compound(children=g_lines).project_to_viewport(origin, viewport_up=up)
        grid_visible.extend([s.moved(translation) for s in vg])

    # Project axes
    vx, _ = x_axis.project_to_viewport(origin, viewport_up=up)
    vy, _ = y_axis.project_to_viewport(origin, viewport_up=up)
    vz, _ = z_axis.project_to_viewport(origin, viewport_up=up)
    axes_visible[\"X\"].extend([s.moved(translation) for s in vx])
    axes_visible[\"Y\"].extend([s.moved(translation) for s in vy])
    axes_visible[\"Z\"].extend([s.moved(translation) for s in vz])

    # Add label
    with bd.BuildSketch() as label_sk:
        bd.Text(name, font_size=spacing*0.06)
    label_moved = label_sk.sketch.moved(translation * bd.Pos(0, -spacing*0.45))
    all_labels.append(label_moved)

# Add scale bar
scale_bar_len = 10
if obj_size > 100: scale_bar_len = 50
elif obj_size > 500: scale_bar_len = 100
elif obj_size < 5: scale_bar_len = 1

with bd.BuildSketch() as scale_sk:
    bd.Rectangle(scale_bar_len, spacing*0.01)
    with bd.BuildSketch(bd.Location((0, spacing*0.04))) as scale_text:
        bd.Text(f\"{scale_bar_len} units\", font_size=spacing*0.04)
scale_bar_moved = scale_sk.sketch.moved(bd.Pos(spacing*0.5, -spacing*1.8))
all_labels.append(scale_bar_moved)

combined = bd.Compound(children=all_visible + all_hidden + all_labels)
max_dim = max(combined.bounding_box().size.X, combined.bounding_box().size.Y)
if max_dim == 0: max_dim = 1

exporter = bd.ExportSVG(scale=600/max_dim, line_weight=0.6)
exporter.add_layer(\"Visible\", line_color=(0,0,0), line_weight=0.6)
exporter.add_layer(\"Hidden\", line_color=(150, 150, 150), line_type=bd.LineType.ISO_DOT, line_weight=0.3)
exporter.add_layer(\"Grid\", line_color=(220, 220, 220), line_weight=0.2)
exporter.add_layer(\"X-Axis\", line_color=(255, 0, 0), line_weight=1.2)
exporter.add_layer(\"Y-Axis\", line_color=(0, 255, 0), line_weight=1.2)
exporter.add_layer(\"Z-Axis\", line_color=(0, 0, 255), line_weight=1.2)
exporter.add_layer(\"Labels\", line_color=(50, 50, 50), line_weight=0.5)

exporter.add_shape(grid_visible, layer=\"Grid\")
exporter.add_shape(all_visible, layer=\"Visible\")
exporter.add_shape(all_hidden, layer=\"Hidden\")
exporter.add_shape(axes_visible[\"X\"], layer=\"X-Axis\")
exporter.add_shape(axes_visible[\"Y\"], layer=\"Y-Axis\")
exporter.add_shape(axes_visible[\"Z\"], layer=\"Z-Axis\")
exporter.add_shape(all_labels, layer=\"Labels\")

exporter.write(OUTPUT_FILENAME)
"""

PROPOSAL_PROMPT = """You are an expert in python and build123d. 
Look at the following build123d script and the provided render of the model. 
Propose a clear and well-defined 3D CAD modeling task that a user might request.
Focus on a single, reliable geometric change.
The render includes a grid with units shown by the scale bar to help you determine dimensions.

Tasks should involve clear, simple modifications, such as:
- **Feature Addition**: Adding a single practical feature like a mounting hole, a small boss, or a recessed pocket.
- **Geometric Variation**: Modifying an existing shape (e.g., adding a fillet or chamfer to an edge, or changing a single dimension).
- **Subtractive Geometry**: Adding a single, well-defined cutout (e.g., a circular hole, a rectangular slot) to a specific face.
- **Dimension Modification**: Adjusting a primary dimension (length, width, or height) of a component.

The task should be straightforward and require modifying or adding a few lines of build123d code.

Base Code:
```python
{base_code}
```

Output strictly in JSON format matching this schema:
{{
  "user_prompt": "The natural language instruction",
  "explanation": "Brief technical explanation of the change",
  "task_type": "one of: feature_addition, geometric_variation, dimension_modification, subtractive_geometry",
  "edits": [
    {{
      "search": "exact string from base code to replace",
      "replace": "the new string to insert"
    }}
  ],
  "new_code": "Provide the ENTIRE new file code here. This is HIGHLY preferred."
}}"""

FIX_PROMPT = """You are an expert in python and build123d. 
You previously proposed a change that failed.
The render includes a grid and axes (X=Red, Y=Green, Z=Blue) to help you debug placement.

User Request: "{user_prompt}"
Task Type: "{task_type}"

Base Code:
```python
{base_code}
```

Failed Edits (if any):
{failed_edits}

Error Message:
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
A CAD agent was tasked with: \"{user_prompt}\"

Image 1: Original model (multiple views with coordinate axes: X=Red, Y=Green, Z=Blue, and a light gray grid).
Image 2: Modified model (same views and grid).

Your goal is to verify if the modification is exactly as requested and if the rest of the model remains intact.
1. Check if the new features are present and correctly positioned according to the prompt.
2. Verify that NO unintended changes were made to the original geometry.
3. Use the grid and scale bar to ensure dimensions are correct if specified.
4. Use the coordinate axes to verify the orientation and placement of changes.

Be highly critical. If there are any discrepancies, missing features, or unintended distortions, you must conclude with FAIL.
Provide a detailed step-by-step analysis of the changes you observe.
Conclude with EXACTLY the word "SUCCESS" or "FAIL" on a new line."""
