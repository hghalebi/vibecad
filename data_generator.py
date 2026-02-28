import os
import json
import base64
import subprocess
import datetime
import random
import glob

try:
    import cairosvg
except ImportError:
    print("Please install cairosvg: pip install cairosvg")
    print("Note: cairosvg requires the Cairo library (e.g., 'brew install cairo' or 'sudo apt-get install libcairo2')")
    exit(1)

from openai import OpenAI

# ==========================================
# 1. Configuration
# ==========================================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY environment variable not set.")

# Models to use
CODING_MODEL = "anthropic/claude-sonnet-4.6"
VLM_MODEL = "openai/gpt-4o"
#CODING_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"
#VLM_MODEL = "qwen/qwen3-vl-30b-a3b-thinking"

ITERATIONS = 10
OUTPUT_FILE = "build123d_agent_dataset.jsonl"
RUNS_DIR = "runs"
# EXAMPLES can be a glob pattern or a list of specific files
# EXAMPLES = "examples/build123d_examples/*.py"
EXAMPLES = [
    "examples/build123d_examples/clock.py",
    "examples/build123d_examples/holes.py",
    "examples/build123d_examples/loft.py",
    "examples/build123d_examples/lego.py",
    "examples/build123d_examples/key_cap.py",
    "examples/build123d_examples/handle.py",
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

from template import RENDER_TEMPLATE, PROPOSAL_PROMPT, FIX_PROMPT, VALIDATION_PROMPT

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

def generate_proposal(base_code):
    """Uses a coding LLM to propose an edit."""
    prompt = PROPOSAL_PROMPT.format(base_code=base_code)

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content
    parsed = parse_json_response(content)
    if parsed is None:
        print(f"DEBUG: Raw response content: {content}")
        raise ValueError(f"Could not parse JSON from response: {content[:100]}...")
    
    return parsed

def apply_edits(base_code, edits):
    """Applies a list of SEARCH/REPLACE blocks to base_code."""
    new_code = base_code
    for edit in edits:
        search = edit.get('search')
        replace = edit.get('replace')
        if not search: continue
        if search not in new_code:
            return None, f"Search block not found: {search}"
        new_code = new_code.replace(search, replace)
    return new_code, None

def execute_and_render(code, svg_filename, png_filename, base_dir=None, runner_path="temp_runner.py"):
    """Executes the code safely and converts the resulting SVG to PNG. Returns (success, error_msg)"""
    
    # Prepend path setup if base_dir is provided to handle local imports
    path_setup = ""
    if base_dir:
        path_setup = f"import sys\nimport os\nsys.path.append(os.path.abspath('{base_dir}'))\n"

    # Combine user code with the rendering template
    full_code = path_setup + code + "\n" + RENDER_TEMPLATE
    
    # Inject the specific output filename
    executable_code = full_code.replace("OUTPUT_FILENAME", f'"{svg_filename}"')
    
    with open(runner_path, "w") as f:
        f.write(executable_code)
        
    try:
        # Run in a subprocess with a timeout
        # Using -c to avoid issues with current directory if needed, 
        # but here we just run the file.
        result = subprocess.run(["python", runner_path], check=True, timeout=20, capture_output=True)
        # Convert SVG to PNG for the VLM
        if not os.path.exists(svg_filename):
            return False, "SVG was not generated."
        cairosvg.svg2png(url=svg_filename, write_to=png_filename)
        return True, None
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        print(f"Execution Error: {error_msg}")
        return False, error_msg
    except subprocess.TimeoutExpired:
        print("Execution timed out.")
        return False, "Execution timed out."
    except Exception as e:
        print(f"Render Error: {e}")
        return False, str(e)

def generate_fix(base_code, user_prompt, task_type, failed_edits, error_message):
    """Uses a coding LLM to fix a failed edit."""
    prompt = FIX_PROMPT.format(
        user_prompt=user_prompt,
        task_type=task_type,
        base_code=base_code,
        failed_edits=json.dumps(failed_edits, indent=2),
        error_message=error_message
    )

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content
    parsed = parse_json_response(content)
    if parsed is None:
        print(f"DEBUG: Raw fix content: {content}")
        raise ValueError(f"Could not parse JSON from fix response: {content[:100]}...")
    return parsed


def encode_image(image_path):
    """Encodes an image to base64 for the VLM API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def validate_with_vlm(user_prompt, base_png, new_png):
    """Uses a VLM to compare the original and new renders."""
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
            
            print(f"\n--- Iteration {iter_num} (File: {base_file}) ---")
            
            with open(base_file, "r") as f:
                current_base_code = f.read()

            # Render the base model for this iteration
            base_svg = os.path.join(iter_dir, "base.svg")
            base_png = os.path.join(iter_dir, "base.png")
            base_runner = os.path.join(iter_dir, "base_runner.py")
            print("Generating base model render...")
            success, err = execute_and_render(current_base_code, base_svg, base_png, base_dir=base_dir, runner_path=base_runner)
            if not success:
                print(f"Failed to render the base code: {err}. Skipping iteration.")
                with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                    f.write(f"Base render error: {err}")
                continue

            # 2. Generate Proposal
            try:
                proposal = generate_proposal(current_base_code)
                user_prompt = proposal.get('user_prompt')
                task_type = proposal.get('task_type', 'unknown')
                print(f"Prompt: {user_prompt} ({task_type})")
                
                # Save initial proposal
                with open(os.path.join(iter_dir, "proposal.json"), "w") as f:
                    json.dump(proposal, f, indent=2)
            except (ValueError, Exception) as e:
                print(f"Failed to generate valid JSON proposal: {e}. Skipping.")
                with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                    f.write(f"Proposal generation error: {e}")
                continue
                
            # 3. Apply Change & Execute (with retries)
            max_retries = 3
            current_try = 0
            success = False
            
            # Extract initial edits/new_code
            current_edits = proposal.get('edits', [])
            if not current_edits and 'search' in proposal:
                current_edits = [{"search": proposal['search'], "replace": proposal['replace']}]
            current_new_code = proposal.get('new_code')
            
            new_code = ""
            
            while current_try < max_retries:
                error_msg = None
                if current_new_code:
                    new_code = current_new_code
                elif current_edits:
                    new_code, error_msg = apply_edits(current_base_code, current_edits)
                else:
                    error_msg = "No edits or new_code provided in proposal."

                if not error_msg:
                    with open(os.path.join(iter_dir, "generated_code.py"), "w") as f:
                        f.write(new_code)
                    
                    new_svg = os.path.join(iter_dir, "new.svg")
                    new_png = os.path.join(iter_dir, "new.png")
                    new_runner = os.path.join(iter_dir, "new_runner.py")
                    success, error_msg = execute_and_render(new_code, new_svg, new_png, base_dir=base_dir, runner_path=new_runner)
                
                if success:
                    break
            
                print(f"Error applying/rendering: {error_msg}")
                with open(os.path.join(iter_dir, "error.txt"), "a") as f:
                    f.write(f"\n[Try {current_try+1}] {error_msg}")

                current_try += 1
                if current_try < max_retries:
                    print(f"Retry {current_try}/{max_retries} due to error...")
                    try:
                        fix_proposal = generate_fix(current_base_code, user_prompt, task_type, current_edits, error_msg)
                        current_edits = fix_proposal.get('edits', [])
                        current_new_code = fix_proposal.get('new_code')
                    except Exception as e:
                        print(f"Failed to generate fix: {e}")
                        break
                else:
                    print("Max retries reached. Skipping iteration.")
            
            if not success:
                continue
                
            # 4. Validate with VLM
            try:
                is_valid, vlm_output = validate_with_vlm(user_prompt, base_png, new_png)
                print(f"VLM Validation: {'SUCCESS' if is_valid else 'FAIL'}")
                
                with open(os.path.join(iter_dir, "validation.txt"), "w") as f:
                    f.write("SUCCESS" if is_valid else "FAIL")
                
                with open(os.path.join(iter_dir, "vlm_output.txt"), "w") as f:
                    f.write(vlm_output)
            except Exception as e:
                print(f"VLM API Error: {e}. Skipping.")
                with open(os.path.join(iter_dir, "error.txt"), "a") as f:
                    f.write(f"\nVLM error: {e}")
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
                "retries": current_try
            }
            with open(os.path.join(iter_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

            if is_valid:
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
                print(f"Saved successful iteration! (Total valid: {success_count})")



if __name__ == "__main__":
    main()
