import os
import json
import base64
import subprocess
import datetime
import random
import glob

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
OUTPUT_FILE = "build123d_agent_dataset.jsonl"
RUNS_DIR = "runs"
# Expanded list for more complex variety
EXAMPLES = [
    "examples/build123d_examples/clock.py",
    "examples/build123d_examples/holes.py",
    "examples/build123d_examples/loft.py",
    "examples/build123d_examples/lego.py",
    "examples/build123d_examples/key_cap.py",
    "examples/build123d_examples/handle.py",
    "examples/build123d_examples/joints.py",
    "examples/build123d_examples/tea_cup.py",
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

from template import RENDER_TEMPLATE, PROPOSAL_PROMPT, FIX_PROMPT, VALIDATION_PROMPT

# ==========================================
# 2. Complexity Strategies
# ==========================================
COMPLEXITY_STRATEGIES = [
    "Add a single functional feature like a mounting hole (e.g., for an M3 screw) on a flat face.",
    "Introduce a simple geometric modification like adding a fillet or chamfer to specific edges.",
    "Add a single subtractive feature like a circular hole or a rectangular slot on a specific face.",
    "Modify one or two primary dimensions (e.g., length or width) to slightly change the part's size.",
    "Add a small boss, post, or recessed pocket to a main face.",
    "Create a simple linear array of 2 or 3 holes across a flat surface."
]

# ==========================================
# 3. Core Functions
# ==========================================
def parse_json_response(content):
    """Attempts to parse JSON from a string, handling potential markdown blocks."""
    if not content:
        return None

    content = content.strip()

    # Try direct parsing first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Look for markdown blocks
    if "```json" in content:
        try:
            json_str = content.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    if "```" in content:
        try:
            json_str = content.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    # Try to find something that looks like a JSON object
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start:end+1])
        except json.JSONDecodeError:
            pass

    return None

def generate_proposal(base_code, base_png):
    """Uses a coding LLM to propose a clear edit, using the base render for context."""
    strategy = random.choice(COMPLEXITY_STRATEGIES)
    print(f"  [Proposal] Using strategy: {strategy}")
    prompt = PROPOSAL_PROMPT.format(base_code=base_code)
    prompt += f"\n\nIMPORTANT: For this task, focus on this simple, well-defined strategy: {strategy}"

    base64_base = encode_image(base_png)

    print(f"  [Proposal] Calling {CODING_MODEL}...")
    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a world-class CAD engineer specializing in build123d. You propose clear, reliable, and well-defined geometric modifications. You prefer providing full code via 'new_code' to ensure the final script is complete and functional. The renders you receive show 4 views (Isometric, Front, Top, Right) with a grid and coordinate axes (X=Red, Y=Green, Z=Blue) to help you determine scale and placement. Solid parts are shown in light blue with black CAD edges."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_base}"}}
                ]
            }
        ]
    )

    content = response.choices[0].message.content
    parsed = parse_json_response(content)
    if parsed is None:
        print(f"  [Proposal] DEBUG: Raw response content: {content}")
        raise ValueError(f"Could not parse JSON from response: {content[:100]}...")
    
    return parsed

def apply_edits(base_code, edits):
    """Applies a list of SEARCH/REPLACE blocks to base_code."""
    new_code = base_code
    print(f"  [Apply] Applying {len(edits)} SEARCH/REPLACE blocks...")
    for i, edit in enumerate(edits):
        search = edit.get('search')
        replace = edit.get('replace')
        if not search: continue
        if search not in new_code:
            print(f"  [Apply] Error: Search block {i} not found in base code.")
            return None, f"Search block not found: {search}"
        new_code = new_code.replace(search, replace)
    return new_code, None

def execute_and_render(code, svg_filename, png_filename, base_dir=None, runner_path="temp_runner.py"):
    """Executes the code safely and generates a PNG render using pyvista. Returns (success, error_msg)"""
    
    # Prepend path setup if base_dir is provided to handle local imports
    path_setup = "import sys\nimport os\nimport build123d as bd\n"
    if base_dir:
        path_setup += f"sys.path.append(os.path.abspath('{base_dir}'))\n"

    # Combine user code with the rendering template
    full_code = path_setup + code + "\n" + RENDER_TEMPLATE
    
    # Inject the specific output filename
    executable_code = full_code.replace("OUTPUT_FILENAME", f'"{png_filename}"')
    
    with open(runner_path, "w") as f:
        f.write(executable_code)
        
    try:
        # Run in a subprocess with a timeout using xvfb-run
        print(f"  [Render] Running {runner_path} with xvfb-run...")
        result = subprocess.run(["xvfb-run", "-a", "python", runner_path], check=True, timeout=30, capture_output=True)
        
        if not os.path.exists(png_filename):
            print(f"  [Render] Error: {png_filename} not found after execution.")
            # If the script failed, stdout/stderr might have clues
            err = result.stderr.decode('utf-8')
            return False, f"PNG was not generated. Error: {err}"
        
        return True, None
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        print(f"  [Render] Execution Error: {error_msg}")
        return False, error_msg
    except subprocess.TimeoutExpired:
        print("  [Render] Execution timed out.")
        return False, "Execution timed out."
    except Exception as e:
        print(f"  [Render] Error: {e}")
        return False, str(e)

def generate_fix(base_code, user_prompt, task_type, failed_edits, error_message, failed_code=None, base_png=None, new_png=None):
    """Uses a coding LLM to fix a failed edit."""
    print(f"  [Fix] Calling {CODING_MODEL} to fix error...")
    
    failed_code_str = failed_code if failed_code else "No code provided."
    
    prompt = FIX_PROMPT.format(
        user_prompt=user_prompt,
        task_type=task_type,
        base_code=base_code,
        failed_code=failed_code_str,
        failed_edits=json.dumps(failed_edits, indent=2),
        error_message=error_message
    )

    content_list = [{"type": "text", "text": prompt}]
    
    if base_png:
        base64_base = encode_image(base_png)
        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_base}"}})
    
    if new_png and os.path.exists(new_png):
        base64_new = encode_image(new_png)
        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_new}"}})

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a world-class CAD engineer specializing in build123d. You provide robust, high-quality fixes for 3D modeling code. You prefer providing full code via 'new_code' to ensure the final script is correct. The renders show 4 views (Isometric, Front, Top, Right) with a grid and coordinate axes (X=Red, Y=Green, Z=Blue) to help you debug placement. Solid parts are shown in light blue with black CAD edges."},
            {
                "role": "user",
                "content": content_list
            }
        ]
    )

    content = response.choices[0].message.content
    parsed = parse_json_response(content)
    if parsed is None:
        print(f"  [Fix] DEBUG: Raw fix content: {content}")
        raise ValueError(f"Could not parse JSON from fix response: {content[:100]}...")
    return parsed


def encode_image(image_path):
    """Encodes an image to base64 for the VLM API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def validate_with_vlm(user_prompt, base_png, new_png):
    """Uses a VLM to compare the original and new renders."""
    print(f"  [VLM] Comparing renders with {VLM_MODEL}...")
    base64_base = encode_image(base_png)
    base64_new = encode_image(new_png)
    
    prompt = VALIDATION_PROMPT.format(user_prompt=user_prompt)

    response = client.chat.completions.create(
        model=VLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_base}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_new}"}}
                ]
            }
        ]
    )
    
    raw_content = response.choices[0].message.content.strip()
    return "SUCCESS" in raw_content.upper(), raw_content

# ==========================================
# 4. Main Loop
# ==========================================
def main():
    if not OPENROUTER_API_KEY:
        print("Please export OPENROUTER_API_KEY before running.")
        return

    # Create run directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS_DIR, timestamp)
    os.makedirs(run_dir, exist_ok=True)
    print(f"Starting run: {run_dir}")

    # Find all example files
    if isinstance(EXAMPLES, list):
        example_files = EXAMPLES
    else:
        example_files = glob.glob(EXAMPLES)
        
    if not example_files:
        print(f"No example files found for {EXAMPLES}")
        return
    
    success_count = 0
    
    with open(OUTPUT_FILE, "a") as dataset_file:
        for i in range(ITERATIONS):
            base_file = random.choice(example_files)
            base_dir = os.path.dirname(base_file)
            iter_num = i + 1
            iter_dir = os.path.join(run_dir, f"iter_{iter_num:03d}")
            os.makedirs(iter_dir, exist_ok=True)
            
            print(f"\n--- Iteration {iter_num}/{ITERATIONS} (Base: {os.path.basename(base_file)}) ---")
            
            with open(base_file, "r") as f:
                current_base_code = f.read()

            # Render the base model for this iteration
            base_png = os.path.join(iter_dir, "base.png")
            base_runner = os.path.join(iter_dir, "base_runner.py")
            print("  [Step 1] Rendering base model...")
            success, err = execute_and_render(current_base_code, None, base_png, base_dir=base_dir, runner_path=base_runner)
            if not success:
                print(f"  [Error] Failed to render base: {err}. Skipping.")
                with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                    f.write(f"Base render error: {err}")
                continue

            # 2. Generate Proposal
            print("  [Step 2] Generating proposal...")
            try:
                proposal = generate_proposal(current_base_code, base_png)
                proposal['input_code'] = current_base_code # Save the input code for reference
                user_prompt = proposal.get('user_prompt')
                task_type = proposal.get('task_type', 'unknown')
                print(f"  [Proposal] Prompt: {user_prompt} ({task_type})")
            except (ValueError, Exception) as e:
                print(f"  [Error] Failed proposal generation: {e}. Skipping.")
                with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                    f.write(f"Proposal generation error: {e}")
                continue
                
            # 3. Apply Change & Execute (with retries)
            print("  [Step 3] Applying edits and verifying...")
            vlm_retry_count = 0
            max_vlm_retries = 3
            
            # Extract initial edits/new_code
            current_edits = proposal.get('edits', [])
            if not current_edits and 'search' in proposal:
                current_edits = [{"search": proposal['search'], "replace": proposal['replace']}]
            current_new_code = proposal.get('new_code')
            
            new_code = ""
            is_valid = False
            vlm_output = ""
            success = False
            
            while vlm_retry_count <= max_vlm_retries:
                max_retries = 5
                current_try = 0
                success = False
                
                while current_try < max_retries:
                    error_msg = None
                    if current_new_code:
                        print(f"  [Code Try {current_try+1}] Using 'new_code' from LLM.")
                        new_code = current_new_code
                    elif current_edits:
                        print(f"  [Code Try {current_try+1}] Applying SEARCH/REPLACE edits.")
                        new_code, error_msg = apply_edits(current_base_code, current_edits)
                    else:
                        error_msg = "No edits or new_code provided in proposal."

                    if not error_msg:
                        if isinstance(new_code, dict):
                            print(f"  [DEBUG] new_code is a dict! Extracting...")
                            new_code = new_code.get('code', str(new_code))
                        
                        with open(os.path.join(iter_dir, f"generated_code_attempt_{vlm_retry_count + 1}.py"), "w") as f:
                            f.write(new_code)
                        
                        new_png = os.path.join(iter_dir, f"new_attempt_{vlm_retry_count + 1}.png")
                        new_runner = os.path.join(iter_dir, f"new_runner_attempt_{vlm_retry_count + 1}.py")
                        success, error_msg = execute_and_render(new_code, None, new_png, base_dir=base_dir, runner_path=new_runner)
                    
                    if success:
                        print(f"  [Code Try {current_try+1}] Execution successful.")
                        break
                
                    print(f"  [Code Try {current_try+1}] Failed: {error_msg}")
                    with open(os.path.join(iter_dir, "error.txt"), "a") as f:
                        f.write(f"\n[VLM Try {vlm_retry_count}, Code Try {current_try+1}] {error_msg}")

                    current_try += 1
                    if current_try < max_retries:
                        print(f"  [Fix] Attempting code fix {current_try}/{max_retries}...")
                        try:
                            fix_proposal = generate_fix(current_base_code, user_prompt, task_type, current_edits, error_msg, failed_code=new_code, base_png=base_png)
                            current_edits = fix_proposal.get('edits', [])
                            current_new_code = fix_proposal.get('new_code')
                        except Exception as e:
                            print(f"  [Error] Failed to generate fix: {e}")
                            break
                    else:
                        print("  [Error] Max code retries reached for this VLM attempt.")
                
                if not success:
                    break # Failed to get executable code
                    
                # 4. Validate with VLM
                print(f"  [Step 4] VLM Validation (Attempt {vlm_retry_count+1})...")
                try:
                    is_valid, vlm_output = validate_with_vlm(user_prompt, base_png, new_png)
                    print(f"  [VLM Result] {'SUCCESS' if is_valid else 'FAIL'}")
                    
                    # Save validation results
                    v_filename = f"validation_attempt_{vlm_retry_count + 1}.txt"
                    o_filename = f"vlm_output_attempt_{vlm_retry_count + 1}.txt"
                    
                    with open(os.path.join(iter_dir, v_filename), "w") as f:
                        f.write("SUCCESS" if is_valid else "FAIL")
                    
                    with open(os.path.join(iter_dir, o_filename), "w") as f:
                        f.write(vlm_output)
                        
                    if is_valid or vlm_retry_count >= max_vlm_retries:
                        break
                    
                    print(f"  [VLM Feedback] VLM failed validation. Attempting fix based on feedback...")
                    vlm_retry_count += 1
                    try:
                        fix_proposal = generate_fix(current_base_code, user_prompt, task_type, current_edits, vlm_output, failed_code=new_code, base_png=base_png, new_png=new_png)
                        current_edits = fix_proposal.get('edits', [])
                        current_new_code = fix_proposal.get('new_code')
                    except Exception as e:
                        print(f"  [Error] Failed to generate fix from VLM feedback: {e}")
                        break
                except Exception as e:
                    print(f"  [Error] VLM API Error: {e}")
                    with open(os.path.join(iter_dir, "error.txt"), "a") as f:
                        f.write(f"\nVLM error: {e}")
                    break
            
            if not success:
                print(f"  [Skip] Iteration {iter_num} failed to produce valid code.")
                continue
                
            # 5. Save Data
            metadata = {
                "iteration": iter_num,
                "base_file": base_file,
                "instruction": user_prompt,
                "task_type": task_type,
                "is_valid": is_valid,
                "vlm_output": vlm_output,
                "edits": current_edits,
                "has_new_code": bool(current_new_code),
                "run_id": timestamp,
                "retries": current_try,
                "vlm_retries": vlm_retry_count
            }
            with open(os.path.join(iter_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

            if is_valid:
                # Save final proposal only if successful
                proposal['edits'] = current_edits
                proposal['new_code'] = current_new_code
                with open(os.path.join(iter_dir, "proposal.json"), "w") as f:
                    json.dump(proposal, f, indent=2)

                dataset_item = {
                    "instruction": user_prompt,
                    "task_type": task_type,
                    "base_code": current_base_code,
                    "edits": current_edits,
                    "new_code": new_code,
                    "iter_dir": iter_dir,
                    "base_file": base_file
                }
                dataset_file.write(json.dumps(dataset_item) + "\n")
                dataset_file.flush()
                success_count += 1
                print(f"  [Success] Saved valid iteration! (Total valid: {success_count})")
            else:
                print(f"  [Fail] Iteration {iter_num} produced executable but invalid code (VLM check failed).")



if __name__ == "__main__":
    main()
