import os
import json
import base64
import subprocess
import textwrap
import ast
import io
from PIL import Image
from openai import OpenAI

# --- CONFIGURATION ---
# Ensure OPENROUTER_API_KEY is set in your environment
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
CODING_MODEL = "anthropic/claude-sonnet-4.6"
DESIGNER_MODEL = "anthropic/claude-sonnet-4.6"
DOCS_PATH = "build123d_reference.md"
OUTPUT_DIR = "agent_iterations"
MAX_ITERATIONS = 100

if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- UTILITIES ---

def encode_image(image_path, max_size=(512, 512)):
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Render logic extracted from template.py
RENDER_LOGIC_TEMPLATE = """
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
"""

def run_cad_code(code, iteration):
    """Executes the code and generates a render."""
    script_path = os.path.join(OUTPUT_DIR, f"iter_{iteration}.py")
    render_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"render_{iteration}.png"))
    
    # Prepend imports if missing and append rendering logic
    full_code = f"from build123d import *\n" if "from build123d import" not in code else ""
    full_code += code + "\n\n" + f"OUTPUT_FILENAME = r'{render_path}'" + "\n" + RENDER_LOGIC_TEMPLATE
    
    with open(script_path, "w") as f:
        f.write(full_code)
    
    try:
        # Using a fresh process for each run to avoid kernel contamination
        result = subprocess.run(["python3", script_path], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return False, result.stderr, None
        return True, result.stdout, render_path
    except Exception as e:
        return False, str(e), None

# --- AGENT PROMPTS ---

CODING_PROMPT = """You are a world-class CAD engineer specializing in build123d.
Your goal is to implement a 3D CAD model INCREMENTALLY based on user instructions and designer feedback.

### Guidelines:
1. **Incremental Development**: DO NOT build the entire model at once. Add only one or two features per iteration (e.g., first the base shape, then the second major component, then holes, then finishing touches like fillets). 
2. **Stateless Algebraic Form**: Prefer the stateless algebraic API (e.g., `part = Box(10, 10, 10) - Cylinder(2, 10)`) over the stateful builder API (`with BuildPart(): ...`).
3. **Step-by-Step Construction**: Start from basic 2D shapes (sketches like `Rectangle`, `Circle`) and extrude them (using `extrude()`), or use 3D primitives directly.
4. **Algebraic Operations**: Create complex shapes by combining basic ones using boolean operators: `+` (union), `-` (difference), and `&` (intersection).
5. **Robustness**: Use ROBUST SELECTORS (e.g., `part.faces().sort_by(Axis.Z)[-1]`) instead of indices like `faces()[2]`.
6. **Context**: Use the provided documentation to ensure correct API usage.
7. **Output**: Provide the ENTIRE updated Python code. Do not use placeholders.

DOCUMENTATION CONTEXT:
{docs_context}
"""

DESIGNER_PROMPT = """You are a senior industrial designer and CAD expert guiding the incremental construction of a 3D model.
The final goal is: "{goal}"

### Comparison Analysis:
1. **Compare Renders & ASTs**: Analyze the visual and structural differences between the PREVIOUS and CURRENT iterations.
2. **Describe Effects**: Explain how the code changes (seen in AST) translated to visual changes in the model.
3. **Verify Intent**: Did the changes achieve the goal set in the previous iteration?

### PREVIOUS Iteration (Last Successful):
AST:
{last_ast_context}

### CURRENT Iteration:
AST:
{current_ast_context}

### Your Task:
1. **Evaluate Current Progress**: 
   - Is the model moving in the right direction towards the final goal?
   - Do not criticize the model for missing features that are planned for later steps.
   - Check if the current features are correctly sized and positioned using the grid and axes (X=Red, Y=Green, Z=Blue).

2. **Suggest the NEXT logical step**:
   - Follow a standard CAD workflow: 
     a) Primary Shapes (Base features)
     b) Secondary Features (Additive/Subtractive details)
     c) Holes and Cutouts
     d) Finishing touches (Fillets, Chamfers)
   - Tell the coding agent EXACTLY what to add or modify next.
   - Suggest the specific `build123d` primitives, boolean operations, and robust selectors for this next step.

Focus on being a mentor who guides the build process one step at a time. Your feedback should confirm if the current shape is "on track" and clearly define the next incremental addition.
"""

# --- MAIN LOOP ---

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    goal = 'design an L-shaped 50x50mm angle bracket from 3mm sheet metal. Start with an L-shaped 2D sketch and extrude it to make it 3D. The angle bracket is used to stiffen a vertical and horizotal panels that are connected together by their end.  The bracket has two mounting holes on each side, suitable for mounting it to the plates. Use good industry standard practices.'
    
    # Save the goal
    with open(os.path.join(OUTPUT_DIR, "goal.txt"), "w") as f:
        f.write(goal)

    docs_context = ""
    if os.path.exists(DOCS_PATH):
        with open(DOCS_PATH, "r", encoding="utf-8") as f:
            # Taking a chunk of docs as context
            docs_context = f.read()
    else:
        print(f"Warning: {DOCS_PATH} not found. Proceeding without context.")

    coding_history = [
        {"role": "system", "content": CODING_PROMPT.format(docs_context=docs_context)},
        {"role": "user", "content": f"Initial Request: {goal}"}
    ]

    last_render_path = None
    last_ast_context = "None (Initial Step)"

    for i in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- Iteration {i} ---")
        
        # 1. Coding Agent generates/fixes code
        print("Coding Agent is generating model...")
        
        # Save coding prompt (history)
        with open(os.path.join(OUTPUT_DIR, f"prompt_coding_{i}.json"), "w") as f:
            json.dump(coding_history, f, indent=2)

        try:
            response = client.chat.completions.create(
                model=CODING_MODEL,
                messages=coding_history,
                temperature=0.2
            )
            raw_response = response.choices[0].message.content
            
            # Save coding response
            with open(os.path.join(OUTPUT_DIR, f"response_coding_{i}.txt"), "w") as f:
                f.write(raw_response)
                
            code = raw_response.strip()
            
            # Extract code from potential markdown block
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
        except Exception as e:
            print(f"API Error (Coding): {e}")
            break
        
        # 2. Execute and Render
        print("Running build123d kernel and rendering views...")
        success, error_msg, render_path = run_cad_code(code, i)
        
        if not success:
            print(f"Execution failed. Feeding back error to agent.")
            # Save error message
            with open(os.path.join(OUTPUT_DIR, f"error_{i}.txt"), "w") as f:
                f.write(error_msg)
                
            coding_history.append({"role": "assistant", "content": f"```python\n{code}\n```"})
            coding_history.append({"role": "user", "content": f"The code produced an error. Please fix it:\n```\n{error_msg}\n```"})
            continue

        # 3. Designer Agent (VLM) Critique
        print("Designer Agent (VLM) is reviewing render...")
        try:
            # Retrieve the AST of the model for structural context
            try:
                tree = ast.parse(code)
                current_ast_context = ast.dump(tree, indent=2)
            except Exception as e:
                current_ast_context = f"Error parsing AST: {e}"

            base64_image = encode_image(render_path)
            
            user_content = [{"type": "text", "text": f"Iteration {i} result."}]
            
            if last_render_path and os.path.exists(last_render_path):
                last_base64 = encode_image(last_render_path)
                user_content.append({"type": "text", "text": "PREVIOUS Render (Last Successful):"})
                user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{last_base64}"}})
            
            user_content.append({"type": "text", "text": "CURRENT Render:"})
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
            user_content.append({"type": "text", "text": "Provide critique and guidance based on the comparison and the current state."})

            designer_messages = [
                {"role": "system", "content": DESIGNER_PROMPT.format(
                    goal=goal, 
                    last_ast_context=last_ast_context, 
                    current_ast_context=current_ast_context
                )},
                {"role": "user", "content": user_content}
            ]
            
            # Save designer prompt (excluding image for brevity)
            compact_designer_messages = [
                {"role": "system", "content": designer_messages[0]["content"]},
                {"role": "user", "content": "Iteration {i} result with previous and current renders."}
            ]
            with open(os.path.join(OUTPUT_DIR, f"prompt_designer_{i}.json"), "w") as f:
                json.dump(compact_designer_messages, f, indent=2)

            designer_response = client.chat.completions.create(
                model=DESIGNER_MODEL,
                messages=designer_messages
            )
            
            critique = designer_response.choices[0].message.content
            print(f"Designer Feedback: {critique}")
            
            # Save designer response
            with open(os.path.join(OUTPUT_DIR, f"response_designer_{i}.txt"), "w") as f:
                f.write(critique)

            # 4. Update coding history for next loop
            coding_history.append({"role": "assistant", "content": f"```python\n{code}\n```"})
            coding_history.append({"role": "user", "content": f"Designer Feedback:\n{critique}\n\nPlease provide the updated code."})

            # Update last successful state
            last_render_path = render_path
            last_ast_context = current_ast_context

            if "SUCCESS" in critique.upper() or "PERFECT" in critique.upper():
                print("Goal reached according to designer feedback!")
                break
                
        except Exception as e:
            print(f"API Error (Designer): {e}")
            break

    print(f"\nProcess complete. Iteration files and renders saved in '{OUTPUT_DIR}/'.")

if __name__ == "__main__":
    main()
