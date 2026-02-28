import os
import json
import base64
import subprocess
import datetime
import random
import glob
from PIL import Image
import io
import difflib

from openai import OpenAI

# ==========================================
# 1. Configuration
# ==========================================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY environment variable not set.")

# Models to use
CODING_MODEL = "anthropic/claude-sonnet-4.6"
VLM_MODEL = "anthropic/claude-sonnet-4.6"

ITERATIONS = 50
OUTPUT_FILE = "build123d_cot_dataset.jsonl"
RUNS_DIR = "runs_cot"

# Focus on simple examples for CoT
EXAMPLES = [
    "examples/simple_models/mounting_bracket.py",
    "examples/simple_models/circular_flange.py",
    "examples/simple_models/simple_knob.py",
    "examples/simple_models/spacer.py",
    "examples/simple_models/u_bracket.py",
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

from template import RENDER_TEMPLATE, COT_MUTATION_PROMPT, COT_LABEL_PROMPT, FIX_PROMPT

# Strategies to guide mutation (boolean focused)
COMPLEXITY_STRATEGIES = [
    "Subtract a Cylinder to create a mounting hole on the top face.",
    "Add a Box to create a boss or reinforcement rib on a side face.",
    "Subtract a Box to create a rectangular slot or pocket.",
    "Add a Cylinder to create a post or alignment pin.",
    "Subtract a Sphere to create a hemispherical pocket.",
    "Add a Sphere to create a rounded protrusion.",
    "Subtract a Hexagonal prism (Box with 6 sides) to create a nut pocket.",
    "Apply a fillet to the newly added boolean feature edges.",
    "Apply a chamfer to the newly added boolean feature edges."
]

# ==========================================
# 2. Core Functions
# ==========================================

def parse_json_response(content):
    """Attempts to parse JSON from a string, handling potential markdown blocks."""
    if not content: return None
    content = content.strip()
    try: return json.loads(content)
    except: pass
    if "```json" in content:
        try: return json.loads(content.split("```json")[1].split("```")[0].strip())
        except: pass
    if "```" in content:
        try: return json.loads(content.split("```")[1].split("```")[0].strip())
        except: pass
    start, end = content.find('{'), content.rfind('}')
    if start != -1 and end != -1 and end > start:
        try: return json.loads(content[start:end+1])
        except: pass
    return None

def encode_image(image_path, max_size=(640, 640)):
    """Resizes an image and encodes it to base64 JPEG."""
    with Image.open(image_path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_geometry_metrics(code, base_dir=None):
    """Executes code and extracts geometric properties using geometry_checker.py."""
    with open("geometry_checker.py", "r") as f:
        checker_logic = f.read()
    
    path_setup = """import sys
import os
import build123d as bd
"""
    if base_dir: path_setup += f"sys.path.append(os.path.abspath('{base_dir}'))\n"
    full_code = path_setup + code + "\n" + checker_logic
    
    with open("temp_metrics.py", "w") as f:
        f.write(full_code)
        
    try:
        result = subprocess.run(["python", "temp_metrics.py"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            try: return json.loads(result.stdout.strip())
            except: return {"error": f"Could not parse JSON: {result.stdout}"}
        return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}

def execute_and_render(code, png_filename, base_dir=None, runner_path="temp_runner.py"):
    """Executes the code and generates a PNG render using pyvista."""
    path_setup = """import sys
import os
import build123d as bd
"""
    if base_dir: path_setup += f"sys.path.append(os.path.abspath('{base_dir}'))\n"
    full_code = path_setup + code + "\n" + RENDER_TEMPLATE
    executable_code = full_code.replace("OUTPUT_FILENAME", f'"{png_filename}"')
    
    with open(runner_path, "w") as f:
        f.write(executable_code)
    try:
        subprocess.run(["xvfb-run", "-a", "python", runner_path], check=True, timeout=30, capture_output=True)
        return os.path.exists(png_filename), None
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode('utf-8')
    except Exception as e:
        return False, str(e)

def generate_mutation_cot(base_code, base_png):
    """Asks the coding model to mutate the base code according to a strategy with CoT."""
    strategy = random.choice(COMPLEXITY_STRATEGIES)
    print(f"  [Mutation] Using strategy: {strategy}")
    prompt = COT_MUTATION_PROMPT.format(base_code=base_code, strategy=strategy)
    base64_base = encode_image(base_png)

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a world-class CAD engineer specializing in build123d. Keep modifications SIMPLE and VALID. Always provide your chain of thought."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_base}"}}
                ]
            }
        ]
    )
    return parse_json_response(response.choices[0].message.content)

def generate_instruction_from_vlm_cot(base_code, new_code, base_png, new_png, metrics_diff=None):
    """Uses a VLM to compare the original and new renders/code and write an instruction with CoT."""
    print(f"  [Labeling] Calling VLM for instruction with CoT...")
    
    # Generate diff
    diff = "".join(difflib.unified_diff(
        base_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        fromfile='original.py', tofile='modified.py'
    ))

    metrics_str = json.dumps(metrics_diff, indent=2) if metrics_diff else "No specific geometric metrics available."
    prompt = COT_LABEL_PROMPT.format(code_diff=diff, metrics_diff=metrics_str)
    base64_base = encode_image(base_png)
    base64_new = encode_image(new_png)

    response = client.chat.completions.create(
        model=VLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_base}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_new}"}}
            ]}
        ]
    )
    return parse_json_response(response.choices[0].message.content)

def generate_fix(base_code, error_message, failed_code, base_png):
    """Attempts to fix code that failed to render."""
    print(f"  [Fix] Attempting to fix mutation code...")
    prompt = FIX_PROMPT.format(
        user_prompt="Mutation modification",
        task_type="mutation",
        base_code=base_code,
        failed_code=failed_code,
        failed_edits="N/A",
        error_message=error_message
    )
    base64_base = encode_image(base_png)
    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a world-class CAD engineer specializing in build123d. Fix the code to make it valid."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_base}"}}
            ]}
        ]
    )
    return parse_json_response(response.choices[0].message.content)

# ==========================================
# 3. Main Loop
# ==========================================

def main():
    if not OPENROUTER_API_KEY:
        print("Please export OPENROUTER_API_KEY before running.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS_DIR, timestamp)
    os.makedirs(run_dir, exist_ok=True)
    
    example_files = EXAMPLES
    success_count = 0
    
    with open(OUTPUT_FILE, "a") as dataset_file:
        for i in range(ITERATIONS):
            base_file = random.choice(example_files)
            base_dir = os.path.dirname(base_file)
            iter_dir = os.path.join(run_dir, f"iter_{i+1:03d}")
            os.makedirs(iter_dir, exist_ok=True)
            
            print(f"\n--- Iteration {i+1}/{ITERATIONS} (Base: {os.path.basename(base_file)}) ---")
            
            with open(base_file, "r") as f:
                base_code = f.read()

            # 1. Render Base and get Metrics
            base_png = os.path.join(iter_dir, "base.png")
            success, err = execute_and_render(base_code, base_png, base_dir=base_dir, runner_path=os.path.join(iter_dir, "base_runner.py"))
            base_metrics = get_geometry_metrics(base_code, base_dir=base_dir)
            
            if not success:
                print(f"  [Error] Failed to render base: {err}")
                continue

            # 2. Mutate with CoT
            mutation = generate_mutation_cot(base_code, base_png)
            if not mutation or 'new_code' not in mutation:
                print("  [Error] Failed to generate mutation.")
                continue
            
            new_code = mutation['new_code']
            task_type = mutation.get('task_type', 'unknown')
            mutation_thought = mutation.get('thought', 'No thought provided.')
            
            # 3. Verify Mutation
            new_png = os.path.join(iter_dir, "new.png")
            success, err = execute_and_render(new_code, new_png, base_dir=base_dir, runner_path=os.path.join(iter_dir, "new_runner.py"))
            
            if not success:
                # Try one fix
                fix = generate_fix(base_code, err, new_code, base_png)
                if fix and 'new_code' in fix:
                    new_code = fix['new_code']
                    success, err = execute_and_render(new_code, new_png, base_dir=base_dir, runner_path=os.path.join(iter_dir, "new_runner_fix.py"))
            
            if not success:
                print(f"  [Error] Mutation failed to render: {err}")
                continue

            # 4. Get New Metrics and Compare
            new_metrics = get_geometry_metrics(new_code, base_dir=base_dir)
            metrics_diff = None
            if "error" not in base_metrics and "error" not in new_metrics:
                metrics_diff = {
                    "volume_change": new_metrics["volume"] - base_metrics["volume"],
                    "num_faces_change": new_metrics["num_faces"] - base_metrics["num_faces"],
                    "num_edges_change": new_metrics["num_edges"] - base_metrics["num_edges"],
                    "bbox_min_diff": [new_metrics["bbox_min"][i] - base_metrics["bbox_min"][i] for i in range(3)],
                    "bbox_max_diff": [new_metrics["bbox_max"][i] - base_metrics["bbox_max"][i] for i in range(3)],
                }
                
                # Check if anything actually changed
                if abs(metrics_diff["volume_change"]) < 1e-6 and metrics_diff["num_faces_change"] == 0:
                    print("  [Warning] Mutation did not change geometry properties. Skipping.")
                    continue

            # 5. Label with VLM CoT
            label_data = generate_instruction_from_vlm_cot(base_code, new_code, base_png, new_png, metrics_diff=metrics_diff)
            if not label_data or 'instruction' not in label_data:
                print("  [Error] VLM failed to generate instruction.")
                continue
            
            instruction = label_data['instruction']
            label_thought = label_data.get('thought', 'No thought provided.')
            print(f"  [Success] Instruction: {instruction}")

            # 6. Save
            dataset_item = {
                "instruction": instruction,
                "task_type": task_type,
                "base_code": base_code,
                "new_code": new_code,
                "mutation_thought": mutation_thought,
                "label_thought": label_thought,
                "technical_summary": label_data.get('technical_summary'),
                "metrics_diff": metrics_diff,
                "iter_dir": iter_dir,
                "base_file": base_file
            }
            dataset_file.write(json.dumps(dataset_item) + "\n")
            dataset_file.flush()
            
            with open(os.path.join(iter_dir, "metadata.json"), "w") as f:
                json.dump(dataset_item, f, indent=2)
                
            success_count += 1
            print(f"  [Done] Total valid: {success_count}")

if __name__ == "__main__":
    main()
