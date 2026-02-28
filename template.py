BASE_CODE = """from build123d import *

length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex3:
    with BuildSketch() as ex3_sk:
        Circle(width)
        Rectangle(length / 2, width / 2, mode=Mode.SUBTRACT)
    extrude(amount=2 * thickness)
"""

RENDER_TEMPLATE = """
views = {
    "Isometric": (100, -100, 100),
    "Front": (0, -100, 0),
    "Top": (0, 0, 100),
    "Right": (100, 0, 0),
}

all_visible = []
all_hidden = []
spacing = 150

for i, (name, origin) in enumerate(views.items()):
    visible, hidden = ex3.part.project_to_viewport(origin)
    col = i % 2
    row = i // 2
    translation = Pos(col * spacing, -row * spacing)
    visible_moved = [s.moved(translation) for s in visible]
    hidden_moved = [s.moved(translation) for s in hidden]
    all_visible.extend(visible_moved)
    all_hidden.extend(hidden_moved)

combined = Compound(children=all_visible + all_hidden)
max_dimension = max(*combined.bounding_box().size)
exporter = ExportSVG(scale=200 / max_dimension)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(all_visible, layer="Visible")
exporter.add_shape(all_hidden, layer="Hidden")

# The string 'OUTPUT_FILENAME' will be dynamically replaced by our script
exporter.write(OUTPUT_FILENAME)
"""

PROPOSAL_PROMPT = """You are an expert in python and build123d. 
Look at the following build123d script. Propose a natural language user request to modify the CAD geometry (e.g., 'add a 5mm fillet to all edges', 'change the central hole to a polygon', 'increase thickness by 20').
Then, provide the exact SEARCH block (the code to be replaced) and REPLACE block (the new code).

Base Code:
```python
{base_code}
```

Output strictly in JSON format matching this schema:
{{
  "user_prompt": "The natural language instruction",
  "search": "exact string from base code to replace",
  "replace": "the new string to insert"
}}"""

FIX_PROMPT = """You are an expert in python and build123d. 
You previously proposed a change that failed with an error.

User Request: "{user_prompt}"

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
  "search": "exact string from base code to replace",
  "replace": "the new string to insert"
}}"""

VALIDATION_PROMPT = """You are a CAD validation agent. 
The user asked a CAD agent to make the following change to a 3D model: "{user_prompt}"
Image 1 is the original 2D projection. Image 2 is the new 2D projection.
Did the agent successfully make the requested change without destroying the rest of the model? 
Reply with EXACTLY the word "YES" or "NO"."""
