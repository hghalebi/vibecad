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

# Capture logic to find the object to render
def _find_captured_obj():
    # If show() or show_object() was mocked, we might have it.
    # But since we appended this, they already ran.
    # We can inspect globals for common builder names or types.
    best_guess = None
    builders = []
    # We use list(globals().items()) to avoid "dictionary changed size during iteration"
    for name, obj in list(globals().items()):
        if isinstance(obj, (bd.BuildPart, bd.BuildSketch, bd.BuildLine)):
            builders.append(obj)
        elif isinstance(obj, (bd.Part, bd.Sketch, bd.Curve, bd.Compound, bd.Solid, bd.Face, bd.Wire, bd.Edge)):
            best_guess = obj

    if builders:
        # Return the last builder found as it's usually the final object
        obj = builders[-1]
        if isinstance(obj, bd.BuildPart): return obj.part
        if isinstance(obj, bd.BuildSketch): return obj.sketch
        if isinstance(obj, bd.BuildLine): return obj.line

    return best_guess

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
# Calculate spacing based on object size
obj_bb = _captured_obj.bounding_box()
obj_size = max(obj_bb.size.X, obj_bb.size.Y, obj_bb.size.Z)
spacing = 1.5 * obj_size if obj_size > 0 else 150

for i, (name, (origin, up)) in enumerate(views.items()):
    try:
        visible, hidden = _captured_obj.project_to_viewport(origin, viewport_up=up)
    except AttributeError:
        # If it's a sketch or curve, it might not have project_to_viewport
        # Wrap it in a Compound if needed or handle accordingly
        temp_comp = bd.Compound(children=[_captured_obj])
        visible, hidden = temp_comp.project_to_viewport(origin, viewport_up=up)

    col = i % 2
    row = i // 2
    translation = bd.Pos(col * spacing, -row * spacing)
    visible_moved = [s.moved(translation) for s in visible]
    hidden_moved = [s.moved(translation) for s in hidden]
    all_visible.extend(visible_moved)
    all_hidden.extend(hidden_moved)

combined = bd.Compound(children=all_visible + all_hidden)
max_dimension = max(combined.bounding_box().size.X, combined.bounding_box().size.Y)
if max_dimension == 0: max_dimension = 1
exporter = bd.ExportSVG(scale=200 / max_dimension, line_weight=0.3)
exporter.add_layer(\"Visible\")

exporter.add_layer(\"Hidden\", line_color=(99, 99, 99), line_type=bd.LineType.ISO_DOT)
exporter.add_shape(all_visible, layer=\"Visible\")
exporter.add_shape(all_hidden, layer=\"Hidden\")

# The string 'OUTPUT_FILENAME' will be dynamically replaced by our script
exporter.write(OUTPUT_FILENAME)
"""

PROPOSAL_PROMPT = """You are an expert in python and build123d. 
Look at the following build123d script. Propose a natural language user request to modify the CAD geometry.
Then, provide the exact SEARCH block (the code to be replaced) and REPLACE block (the new code).

Available common objects:
- Sketch objects: Circle, Rectangle, RectangleRounded, RegularPolygon, Polygon, SlotCenterPoint, SlotCenterToCenter, SlotOverall, Text, Trapezoid.
- 3D objects: Box, Cylinder, Cone, Sphere, Torus, Wedge.
- Operations: extrude, revolve, sweep, loft, fillet, chamfer, mirror, scale, offset.
- Locations: PolarLocations, GridLocations, HexLocations.

Common pitfalls:
- Use `RectangleRounded(width, height, radius)` instead of `RoundedRectangle`.
- List comprehensions for points should be like `[(x, y, z) for ...]` or `[Vector(x, y, z) for ...]`.
- `fillet(objects, radius)` and `chamfer(objects, length)` are common.
- When adding a sketch object to a builder, it is automatically added unless `mode=Mode.PRIVATE` is used.

Base Code:
```python
{base_code}
```

Output strictly in JSON format matching this schema:
{{
  \"user_prompt\": \"The natural language instruction\",
  \"search\": \"exact string from base code to replace\",
  \"replace\": \"the new string to insert\"
}}"""

FIX_PROMPT = """You are an expert in python and build123d. 
You previously proposed a change that failed with an error.

User Request: \"{user_prompt}\"

Available common objects:
- Sketch objects: Circle, Rectangle, RectangleRounded, RegularPolygon, Polygon, SlotCenterPoint, SlotCenterToCenter, SlotOverall, Text, Trapezoid.
- 3D objects: Box, Cylinder, Cone, Sphere, Torus, Wedge.

Base Code:
```python
{base_code}
```

You tried to replace:
```python
{failed_search}
```
with:
```python
{failed_replace}
```

Error Message:
```
{error_message}
```

Please provide a CORRECTED SEARCH/REPLACE block that achieves the user request.
Output strictly in JSON format matching this schema:
{{
  \"search\": \"exact string from base code to replace\",
  \"replace\": \"the new string to insert\"
}}"""

VALIDATION_PROMPT = """You are a CAD validation agent. 
The user asked a CAD agent to make the following change to a 3D model: \"{user_prompt}\"
Image 1 is the original 2D projection. Image 2 is the new 2D projection.

Analyze both images and determine if the agent successfully made the requested change without destroying the rest of the model.
Provide your reasoning first, and then conclude with EXACTLY the word "SUCCESS" or "FAIL" on a new line."""
