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
CODING_MODEL = "anthropic/claude-3.5-sonnet"
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
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

from template import RENDER_TEMPLATE, PROPOSAL_PROMPT, FIX_PROMPT, VALIDATION_PROMPT

# ==========================================
# 3. Core Functions
# ==========================================
def generate_proposal(base_code):
    """Uses a coding LLM to propose an edit."""
    prompt = PROPOSAL_PROMPT.format(base_code=base_code)

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)

def execute_and_render(code, svg_filename, png_filename, base_dir=None):
    """Executes the code safely and converts the resulting SVG to PNG. Returns (success, error_msg)"""
    
    # Prepend path setup if base_dir is provided to handle local imports
    path_setup = ""
    if base_dir:
        path_setup = f"import sys\nimport os\nsys.path.append(os.path.abspath('{base_dir}'))\n"

    # Combine user code with the rendering template
    full_code = path_setup + code + "\n" + RENDER_TEMPLATE
    
    # Inject the specific output filename
    executable_code = full_code.replace("OUTPUT_FILENAME", f'"{svg_filename}"')
    
    with open("temp_runner.py", "w") as f:
        f.write(executable_code)
        
    try:
        # Run in a subprocess with a timeout
        # Using -c to avoid issues with current directory if needed, 
        # but here we just run the file.
        result = subprocess.run(["python", "temp_runner.py"], check=True, timeout=20, capture_output=True)
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

def generate_fix(base_code, user_prompt, failed_search, failed_replace, error_message):
    """Uses a coding LLM to fix a failed edit."""
    prompt = FIX_PROMPT.format(
        user_prompt=user_prompt,
        base_code=base_code,
        failed_search=failed_search,
        failed_replace=failed_replace,
        error_message=error_message
    )

    response = client.chat.completions.create(
        model=CODING_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)

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
    global_iter = 0
    
    with open(OUTPUT_FILE, "a") as dataset_file:
        for base_file in example_files:
            base_dir = os.path.dirname(base_file)
            for i in range(ITERATIONS):
                global_iter += 1
                iter_num = global_iter
                iter_dir = os.path.join(run_dir, f"iter_{iter_num:03d}")
                os.makedirs(iter_dir, exist_ok=True)
                
                print(f"\n--- Iteration {iter_num} (File: {base_file}) ---")
                
                with open(base_file, "r") as f:
                    current_base_code = f.read()

                # Render the base model for this iteration
                base_svg = os.path.join(iter_dir, "base.svg")
                base_png = os.path.join(iter_dir, "base.png")
                print("Generating base model render...")
                success, err = execute_and_render(current_base_code, base_svg, base_png, base_dir=base_dir)
                if not success:
                    print(f"Failed to render the base code: {err}. Skipping iteration.")
                    with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                        f.write(f"Base render error: {err}")
                    continue

                # 2. Generate Proposal
                try:
                    proposal = generate_proposal(current_base_code)
                    user_prompt = proposal.get('user_prompt')
                    search_block = proposal.get('search')
                    replace_block = proposal.get('replace')
                    print(f"Prompt: {user_prompt}")
                    
                    # Save initial proposal
                    with open(os.path.join(iter_dir, "proposal.json"), "w") as f:
                        json.dump(proposal, f, indent=2)
                except Exception as e:
                    print(f"Failed to generate valid JSON proposal: {e}. Skipping.")
                    with open(os.path.join(iter_dir, "error.txt"), "w") as f:
                        f.write(f"Proposal generation error: {e}")
                    continue
                    
                # 3. Apply Diff & Execute (with retries)
                max_retries = 3
                current_try = 0
                success = False
                current_search = search_block
                current_replace = replace_block
                new_code = ""
                
                while current_try < max_retries:
                    if not current_search or current_search not in current_base_code:
                        error_msg = f"Search block not found in base code."
                        print(error_msg)
                    else:
                        new_code = current_base_code.replace(current_search, current_replace)
                        with open(os.path.join(iter_dir, "code.py"), "w") as f:
                            f.write(new_code)
                        
                        new_svg = os.path.join(iter_dir, "new.svg")
                        new_png = os.path.join(iter_dir, "new.png")
                        success, error_msg = execute_and_render(new_code, new_svg, new_png, base_dir=base_dir)
                    
                    if success:
                        # Update search/replace to the ones that actually worked
                        search_block, replace_block = current_search, current_replace
                        break
                
                    with open(os.path.join(iter_dir, "error.txt"), "a") as f:
                        f.write(f"\n[Try {current_try+1}] {error_msg}")

                    current_try += 1
                    if current_try < max_retries:
                        print(f"Retry {current_try}/{max_retries} due to error...")
                        try:
                            fix_proposal = generate_fix(current_base_code, user_prompt, current_search, current_replace, error_msg)
                            current_search = fix_proposal.get('search')
                            current_replace = fix_proposal.get('replace')
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
                "is_valid": is_valid,
                "vlm_output": vlm_output,
                "search_block": search_block,
                "replace_block": replace_block,
                "run_id": timestamp,
                "retries": current_try
            }
            with open(os.path.join(iter_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

            if is_valid:
                dataset_item = {
                    "instruction": user_prompt,
                    "base_code": current_base_code,
                    "search_block": search_block,
                    "replace_block": replace_block,
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
