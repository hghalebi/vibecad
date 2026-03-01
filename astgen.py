import os
import ast
import json
import random
import requests
import copy
import re
import numpy as np
import pyvista as pv
from build123d import *

# Enable headless rendering for environments without an X server
if os.name == "posix" and "DISPLAY" not in os.environ:
    pv.start_xvfb()

def clean_json_string(text):
    """Strips markdown formatting and trailing text from LLM outputs."""
    # Remove markdown code block syntax
    text = re.sub(r"```(?:json)?", "", text).strip()
    return text

# ==========================================
# 1. Configuration
# ==========================================
SEED = int(os.environ.get("SEED", random.randint(0, 1000000)))
random.seed(SEED)
np.random.seed(SEED)
print(f"Using random seed: {SEED}")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "your_openrouter_api_key_here")
MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"
NUM_SAMPLES = 10000 # How many training pairs to generate

# ==========================================
# 2. AST Mechanical Model Generation
# ==========================================

PART_NAMES = ["base_plate", "mounting_bracket", "support_block", "casing", "flange_mount", "heatsink_base", "adapter_plate", "fixture_body", "sensor_mount", "enclosure"]

def make_constant(value):
    return ast.Constant(value=value)

def make_vec3(x, y, z):
    return ast.Tuple(elts=[make_constant(x), make_constant(y), make_constant(z)], ctx=ast.Load())

def make_sketch_primitive():
    """Generates a random build123d 2D sketch AST node."""
    shapes = ['Rectangle', 'Circle', 'RegularPolygon', 'SlotOverall', 'Trapezoid']
    shape = random.choice(shapes)
    
    if shape == 'Rectangle':
        args = [make_constant(random.randint(20, 80)), make_constant(random.randint(20, 80))]
    elif shape == 'Circle':
        args = [make_constant(random.randint(15, 50))]
    elif shape == 'RegularPolygon':
        args = [make_constant(random.randint(15, 45)), make_constant(random.choice([3, 4, 5, 6, 8]))]
    elif shape == 'SlotOverall':
        args = [make_constant(random.randint(30, 80)), make_constant(random.randint(10, 25))]
    elif shape == 'Trapezoid':
        args = [make_constant(random.randint(40, 80)), make_constant(random.randint(20, 40)), make_constant(random.randint(60, 80))]
        
    node = ast.Call(func=ast.Name(id=shape, ctx=ast.Load()), args=args, keywords=[])
    
    # Optional fillet sketch vertices
    if random.random() < 0.3:
        node = ast.Call(
            func=ast.Name(id='fillet', ctx=ast.Load()),
            args=[ast.Call(func=ast.Attribute(value=node, attr='vertices', ctx=ast.Load()), args=[], keywords=[]), make_constant(random.randint(2, 5))],
            keywords=[]
        )
    return node

def make_location_pattern(x_range=40, y_range=40):
    """Generates a location pattern: Pos, GridLocations, or PolarLocations."""
    loc_type = random.choice(['Pos', 'GridLocations', 'PolarLocations'])
    
    if loc_type == 'Pos':
        args = [make_constant(random.randint(-x_range//2, x_range//2)), make_constant(random.randint(-y_range//2, y_range//2)), make_constant(0)]
        return ast.Call(func=ast.Name(id='Pos', ctx=ast.Load()), args=args, keywords=[])
    elif loc_type == 'GridLocations':
        args = [make_constant(random.randint(20, x_range)), make_constant(random.randint(20, y_range)), make_constant(2), make_constant(2)]
        return ast.Call(func=ast.Name(id='GridLocations', ctx=ast.Load()), args=args, keywords=[])
    else: # PolarLocations
        radius = random.randint(15, x_range//2)
        count = random.choice([3, 4, 6, 8])
        args = [make_constant(radius), make_constant(count)]
        return ast.Call(func=ast.Name(id='PolarLocations', ctx=ast.Load()), args=args, keywords=[])

def make_base():
    """Generates a base solid: Box, Cylinder, Wedge, or Extruded Sketch."""
    base_type = random.choice(['Box', 'Cylinder', 'Wedge', 'Extrude'])
    
    if base_type == 'Box':
        args = [make_constant(random.randint(40, 100)), make_constant(random.randint(40, 100)), make_constant(random.randint(5, 20))]
        node = ast.Call(func=ast.Name(id='Box', ctx=ast.Load()), args=args, keywords=[])
    elif base_type == 'Cylinder':
        args = [make_constant(random.randint(25, 50)), make_constant(random.randint(10, 30))]
        node = ast.Call(func=ast.Name(id='Cylinder', ctx=ast.Load()), args=args, keywords=[])
    elif base_type == 'Wedge':
        args = [make_constant(60), make_constant(60), make_constant(20), make_constant(0), make_constant(0), make_constant(30), make_constant(30)]
        node = ast.Call(func=ast.Name(id='Wedge', ctx=ast.Load()), args=args, keywords=[])
    else: # Extrude
        sketch = make_sketch_primitive()
        node = ast.Call(func=ast.Name(id='extrude', ctx=ast.Load()), args=[sketch, make_constant(random.randint(10, 25))], keywords=[])
    
    return node

def add_hole_feature(current_node):
    """Adds a hole or pattern of holes."""
    hole_type = random.choice(['Hole', 'CounterBoreHole', 'CounterSinkHole'])
    radius = random.randint(2, 6)
    
    locs = make_location_pattern(x_range=50, y_range=50)

    if hole_type == 'Hole':
        hole_call = ast.Call(func=ast.Name(id='Hole', ctx=ast.Load()), args=[make_constant(radius)], keywords=[])
    elif hole_type == 'CounterBoreHole':
        hole_call = ast.Call(
            func=ast.Name(id='CounterBoreHole', ctx=ast.Load()), 
            args=[make_constant(radius), make_constant(radius+2), make_constant(2)], 
            keywords=[]
        )
    else: # CounterSinkHole
        hole_call = ast.Call(
            func=ast.Name(id='CounterSinkHole', ctx=ast.Load()), 
            args=[make_constant(radius), make_constant(radius+2)], 
            keywords=[]
        )
    
    # Plane selection: top or bottom face
    is_top = random.random() < 0.8
    plane_node = ast.Call(
        func=ast.Name(id='Plane', ctx=ast.Load()),
        args=[
            ast.Subscript(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(func=ast.Attribute(value=current_node, attr='faces', ctx=ast.Load()), args=[], keywords=[]),
                        attr='sort_by', ctx=ast.Load()
                    ),
                    args=[], keywords=[]
                ),
                slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)) if is_top else ast.Constant(value=0),
                ctx=ast.Load()
            )
        ],
        keywords=[]
    )
    
    feature = ast.BinOp(left=ast.BinOp(left=plane_node, op=ast.Mult(), right=locs), op=ast.Mult(), right=hole_call)
    return ast.BinOp(left=current_node, op=ast.Sub(), right=feature)

def add_boss_pocket(current_node):
    """Adds an extruded feature (join or cut)."""
    sketch = make_sketch_primitive()
    amount = random.randint(5, 15)
    op = ast.Add() if random.random() < 0.6 else ast.Sub()
    
    feature = ast.Call(func=ast.Name(id='extrude', ctx=ast.Load()), args=[sketch, make_constant(amount)], keywords=[])
    
    # Random position/rotation
    pos = make_location_pattern(x_range=30, y_range=30)
    if isinstance(pos, ast.Call) and isinstance(pos.func, ast.Name) and pos.func.id != 'Pos':
        # Patterns (Grid/Polar) might need Pos to avoid being centered?
        pass

    feature = ast.BinOp(left=pos, op=ast.Mult(), right=feature)
    return ast.BinOp(left=current_node, op=op, right=feature)

def add_text_feature(current_node):
    """Adds embossed or debossed text."""
    text_val = random.choice(["M3", "TOP", "FRONT", "A1", "REV B"])
    font_size = random.randint(5, 12)
    depth = random.randint(1, 2)
    op = ast.Add() if random.random() < 0.5 else ast.Sub()
    
    text_call = ast.Call(
        func=ast.Name(id='Text', ctx=ast.Load()), 
        args=[make_constant(text_val), make_constant(font_size)],
        keywords=[ast.keyword(arg='align', value=ast.Attribute(value=ast.Name(id='Align', ctx=ast.Load()), attr='CENTER', ctx=ast.Load()))]
    )
    
    feature = ast.Call(func=ast.Name(id='extrude', ctx=ast.Load()), args=[text_call, make_constant(depth)], keywords=[])
    
    # Place on largest face
    plane_node = ast.Call(
        func=ast.Name(id='Plane', ctx=ast.Load()),
        args=[
            ast.Subscript(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(func=ast.Attribute(value=current_node, attr='faces', ctx=ast.Load()), args=[], keywords=[]),
                        attr='sort_by', ctx=ast.Load()
                    ),
                    args=[], keywords=[]
                ),
                slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
                ctx=ast.Load()
            )
        ],
        keywords=[]
    )
    
    feature = ast.BinOp(left=plane_node, op=ast.Mult(), right=feature)
    return ast.BinOp(left=current_node, op=op, right=feature)

def apply_finishing(current_node):
    """Applies fillet or chamfer to specific edges."""
    mod_type = random.choice(['fillet', 'chamfer'])
    val = make_constant(round(random.uniform(0.5, 4.0), 1))
    
    # Edge selection: all vertical edges OR top edges OR all edges
    r = random.random()
    if r < 0.4:
        # filter_by(Axis.Z)
        edges_node = ast.Call(
            func=ast.Attribute(
                value=ast.Call(func=ast.Attribute(value=current_node, attr='edges', ctx=ast.Load()), args=[], keywords=[]),
                attr='filter_by', ctx=ast.Load()
            ),
            args=[ast.Attribute(value=ast.Name(id='Axis', ctx=ast.Load()), attr='Z', ctx=ast.Load())],
            keywords=[]
        )
    elif r < 0.7:
        # sort_by(Axis.Z)[-1] - Top edges
        edges_node = ast.Subscript(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Call(func=ast.Attribute(value=current_node, attr='edges', ctx=ast.Load()), args=[], keywords=[]),
                    attr='sort_by', ctx=ast.Load()
                ),
                args=[ast.Attribute(value=ast.Name(id='Axis', ctx=ast.Load()), attr='Z', ctx=ast.Load())],
                keywords=[]
            ),
            slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
            ctx=ast.Load()
        )
    else:
        # all edges
        edges_node = ast.Call(func=ast.Attribute(value=current_node, attr='edges', ctx=ast.Load()), args=[], keywords=[])
        
    return ast.Call(func=ast.Name(id=mod_type, ctx=ast.Load()), args=[edges_node, val], keywords=[])

def generate_ast_module():
    """Generates a realistic mechanical part with a structured sequence of operations."""
    var_name = random.choice(PART_NAMES)
    body = []
    
    # 1. Base Part
    base_node = make_base()
    body.append(ast.Assign(targets=[ast.Name(id="part", ctx=ast.Store())], value=base_node, lineno=1))
    
    # 2. Add features
    num_features = random.randint(1, 3)
    for i in range(num_features):
        feature_choice = random.random()
        if feature_choice < 0.4:
            new_expr = add_hole_feature(ast.Name(id="part", ctx=ast.Load()))
        elif feature_choice < 0.7:
            new_expr = add_boss_pocket(ast.Name(id="part", ctx=ast.Load()))
        elif feature_choice < 0.9:
            new_expr = add_text_feature(ast.Name(id="part", ctx=ast.Load()))
        else:
            new_expr = apply_finishing(ast.Name(id="part", ctx=ast.Load()))
        
        body.append(ast.Assign(targets=[ast.Name(id="part", ctx=ast.Store())], value=new_expr, lineno=i+2))
            
    # 3. Final Assignment
    body.append(ast.Assign(targets=[ast.Name(id=var_name, ctx=ast.Store())], value=ast.Name(id="part", ctx=ast.Load()), lineno=num_features+2))
    
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    return module, var_name

def mutate_ast(original_module, var_name):
    """Mutates the part by adding one more realistic feature as a new line."""
    new_module = copy.deepcopy(original_module)
    
    r = random.random()
    if r < 0.4:
        new_expr = add_hole_feature(ast.Name(id=var_name, ctx=ast.Load()))
    elif r < 0.7:
        new_expr = add_boss_pocket(ast.Name(id=var_name, ctx=ast.Load()))
    elif r < 0.9:
        new_expr = add_text_feature(ast.Name(id=var_name, ctx=ast.Load()))
    else:
        new_expr = apply_finishing(ast.Name(id=var_name, ctx=ast.Load()))
        
    new_module.body.append(ast.Assign(targets=[ast.Name(id=var_name, ctx=ast.Store())], value=new_expr))
    ast.fix_missing_locations(new_module)
    return new_module

# ==========================================
# 3. LLM Interaction
# ==========================================

def generate_cot_pair(code_original, code_modified, top_original, delta):
    """Asks the LLM to write a user prompt and a CoT reasoning response."""
    
    personas = [
        "a detail-oriented senior mechanical engineer",
        "a non-technical product manager focusing on ergonomics",
        "a manufacturing engineer worried about tool access",
        "a designer focused on sleek aesthetics",
        "a structural analyst needing weight reduction"
    ]
    
    system_prompt = (
        "You are an expert mechanical engineer and AI training data generator. "
        "I will provide you with original python CAD code in the build123d algebraic format, "
        "modified CAD code in the same format, "
        "and the exact geometric changes (delta) that occurred. \n\n"
        f"Your persona is: {random.choice(personas)}.\n\n"
        "Your task is to generate:\n"
        "1. 'user_prompt': A natural language instruction requesting this change. "
        "Vary the tone: sometimes very specific and technical, sometimes brief and informal, "
        "sometimes explaining the 'why' (e.g., 'We need M4 clearance holes here for the mounting plate').\n"
        "2. 'cot_reasoning': A step-by-step 'Chain of Thought' explanation. "
        "Identify the feature being added/modified, analyze the geometric delta (volume, faces), "
        "and explain how the build123d code implements it using algebra and planes.\n\n"
        "Output ONLY valid JSON containing the keys 'user_prompt' and 'cot_reasoning'. "
        "Do not include markdown blocks."
    )
    
    user_prompt = f"""
    Original Code: {code_original}
    Modified Code: {code_modified}
    
    Original Topology: {json.dumps(top_original)}
    Geometric Delta: {json.dumps(delta)}
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if response.status_code != 200:
            print(f"OpenRouter API Error {response.status_code}: {response.text}")
            return None
        result = response.json()['choices'][0]['message']['content']
        cleaned_result = clean_json_string(result)
        return json.loads(cleaned_result)
    except Exception as e:
        print(f"Failed to query LLM: {e}")
        return None

# ==========================================
# 4. Rendering & Evaluation
# ==========================================

def _find_captured_obj(local_env):
    builders = []
    others = []
    for name, obj in list(local_env.items()):
        if name.startswith("_"): continue
        if isinstance(obj, (BuildPart, BuildSketch, BuildLine)):
            builders.append(obj)
        elif isinstance(obj, (Part, Sketch, Curve, Compound, Solid, Face, Wire, Edge)):
            others.append(obj)

    if builders:
        parts = [b for b in builders if isinstance(b, BuildPart)]
        if parts: return parts[-1].part
        sketches = [b for b in builders if isinstance(b, BuildSketch)]
        if sketches: return sketches[-1].sketch
        lines = [b for b in builders if isinstance(b, BuildLine)]
        if lines: return lines[-1].line

    if others:
        parts = [o for o in others if isinstance(o, (Part, Solid, Compound))]
        if parts: return parts[-1]
        sketches = [o for o in others if isinstance(o, (Sketch, Face))]
        if sketches: return sketches[-1]
        return others[-1]
    return None

def render_to_png(obj, filename):
    """Renders a build123d object to a 4-view PNG using PyVista."""
    try:
        verts, triangles = obj.tessellate(tolerance=0.1)
    except:
        verts, triangles = Compound(children=[obj]).tessellate(tolerance=0.1)
        
    def _to_tuple(v):
        if hasattr(v, "X"): return (v.X, v.Y, v.Z)
        return tuple(v)

    pv_verts = np.array([_to_tuple(v) for v in verts])
    pv_faces = np.hstack([[3, *t] for t in triangles])
    mesh = pv.PolyData(pv_verts, pv_faces)
    edges_poly = mesh.extract_feature_edges(boundary_edges=True, feature_edges=True, manifold_edges=True)

    plotter = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(800, 800))
    views = [("Isometric", None), ("Front", None), ("Top", None), ("Right", None)]
    
    for i, (name, _) in enumerate(views):
        plotter.subplot(i // 2, i % 2)
        plotter.add_text(name, font_size=12, color="black")
        plotter.add_mesh(mesh, color="lightblue", smooth_shading=True, specular=0.5, ambient=0.3)
        if edges_poly:
            plotter.add_mesh(edges_poly, color="black", line_width=2)
        plotter.add_axes()
        plotter.show_grid(color='gray')
        plotter.set_background("white")
        
        if name == "Isometric": plotter.view_isometric()
        elif name == "Front": plotter.view_xz(); plotter.camera.up = (0, 0, 1)
        elif name == "Top": plotter.view_xy()
        elif name == "Right": plotter.view_yz(); plotter.camera.up = (0, 0, 1)
        plotter.reset_camera()

    plotter.screenshot(filename)
    plotter.close()

def evaluate_topology(code_str, output_prefix=None):
    """Executes the CAD code and returns geometric facts, optionally renders."""
    local_env = {}
    try:
        exec(code_str, globals(), local_env)
        part = _find_captured_obj(local_env)
        
        if part is None or (hasattr(part, "volume") and part.volume < 1e-6):
            return None # Invalid geometry
            
        if output_prefix:
            render_dir = f"output_renders_{SEED}"
            os.makedirs(render_dir, exist_ok=True)
            render_to_png(part, f"{render_dir}/{output_prefix}.png")
            
        bbox = part.bounding_box().size
        return {
            "volume": round(part.volume, 2) if hasattr(part, "volume") else 0,
            "faces_total": len(part.faces()),
            "faces_planar": len(part.faces().filter_by(GeomType.PLANE)),
            "faces_cylindrical": len(part.faces().filter_by(GeomType.CYLINDER)),
            "edges_total": len(part.edges()),
            "bounding_box": {"x": round(bbox.X, 2), "y": round(bbox.Y, 2), "z": round(bbox.Z, 2)}
        }
    except Exception as e:
        print(f"Eval error: {e}")
        return None

def calculate_delta(top1, top2):
    """Computes the difference in geometry."""
    delta = {}
    for k in top1.keys():
        if isinstance(top1[k], dict):
            delta[k] = {sub_k: round(top2[k][sub_k] - top1[k][sub_k], 2) for sub_k in top1[k]}
        else:
            delta[k] = round(top2[k] - top1[k], 2)
    return delta

# ==========================================
# 5. Main Pipeline
# ==========================================

def main():
    if OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        print("WARNING: OpenRouter API key not set. LLM generation will fail.")
        
    output_file = f"build123d_cot_dataset_{SEED}.jsonl"
    attempts = 0
    successes = 0
    
    print(f"Starting generation of {NUM_SAMPLES} CoT training pairs...")
    
    with open(output_file, "w") as f:
        while successes < NUM_SAMPLES and attempts < (NUM_SAMPLES * 5):
            attempts += 1
            
            # 1. Generate & Evaluate Original
            ast_orig, var_name = generate_ast_module()
            code_orig = ast.unparse(ast_orig)
            top_orig = evaluate_topology(code_orig)
            
            if not top_orig: continue
                
            # 2. Mutate & Evaluate Modified
            ast_mod = mutate_ast(ast_orig, var_name)
            code_mod = ast.unparse(ast_mod)
            top_mod = evaluate_topology(code_mod)
            
            if not top_mod: continue
                
            # 3. Calculate Delta
            delta = calculate_delta(top_orig, top_mod)
            if delta["volume"] == 0: continue
                
            print(f"\n[{successes + 1}/{NUM_SAMPLES}] Valid mutation found. Querying LLM...")
            
            # 4. Generate Chain of Thought
            llm_output = generate_cot_pair(code_orig, code_mod, top_orig, delta)
            
            if llm_output and "user_prompt" in llm_output:
                prefix = f"sample_{successes + 1}"
                evaluate_topology(code_orig, output_prefix=f"{prefix}_before")
                evaluate_topology(code_mod, output_prefix=f"{prefix}_after")
                
                training_example = {
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are a build123d coding assistant. You will be provided with existing code in build123d algebraic format and a request for modification. Think step-by-step before writing code."
                        },
                        {
                            "role": "user", 
                            "content": f"Here is my current code:\n```python\n{code_orig}\n```\n{llm_output['user_prompt']}"
                        },
                        {
                            "role": "assistant", 
                            "content": f"{llm_output['cot_reasoning']}\n\nHere is the updated code:\n```python\n{code_mod}\n```"
                        }
                    ],
                    "images": [f"output_renders_{SEED}/{prefix}_before.png", f"output_renders_{SEED}/{prefix}_after.png"]
                }
                f.write(json.dumps(training_example) + "\n")
                f.flush()
                successes += 1
                print(f"Successfully generated CoT pair for {prefix}.")

    print(f"\nDone! Dataset saved to {output_file}")

if __name__ == "__main__":
    main()
