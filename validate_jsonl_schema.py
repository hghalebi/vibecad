import json
import os
import sys

def validate_jsonl(file_path, expected_keys, optional_keys=None):
    if optional_keys is None:
        optional_keys = []
    print(f"Validating {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return False

    errors = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                
                # Check for required keys
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    # Special case for agent dataset: it can have (search_block, replace_block) OR (edits)
                    if file_name == "build123d_agent_dataset.jsonl":
                        has_blocks = "search_block" in data and "replace_block" in data
                        has_edits = "edits" in data
                        if not (has_blocks or has_edits):
                            print(f"  Line {i}: Missing both 'edits' and 'search_block'/'replace_block' pairs")
                            errors += 1
                        # Filter out those from missing_keys to avoid double reporting
                        missing_keys = [k for k in missing_keys if k not in ["search_block", "replace_block", "edits"]]
                        if missing_keys:
                             print(f"  Line {i}: Missing keys: {missing_keys}")
                             errors += 1
                    else:
                        print(f"  Line {i}: Missing keys: {missing_keys}")
                        errors += 1
                
                # Check for unexpected keys (not in expected or optional)
                all_allowed = set(expected_keys) | set(optional_keys)
                if file_name == "build123d_agent_dataset.jsonl":
                     all_allowed |= {"search_block", "replace_block", "edits", "task_type"}

                unexpected_keys = [key for key in data if key not in all_allowed]
                # if unexpected_keys:
                #     print(f"  Line {i}: Unexpected keys: {unexpected_keys}")
                #     errors += 1

                # Check types and syntax
                for key, value in data.items():
                    if key in ['metrics_diff', 'edits', 'metadata']:
                        if not isinstance(value, (dict, list, type(None))):
                             print(f"  Line {i}: Key '{key}' has unexpected type {type(value)}")
                             errors += 1
                    elif not isinstance(value, str):
                        print(f"  Line {i}: Key '{key}' has unexpected type {type(value)}")
                        errors += 1
                    
                    # Optional: Check Python syntax for code fields
                    if key in ['base_code', 'new_code'] and isinstance(value, str):
                        try:
                            compile(value, '<string>', 'exec')
                        except SyntaxError as e:
                            print(f"  Line {i}: Syntax error in {key}: {e}")
                            errors += 1

            except json.JSONDecodeError as e:
                print(f"  Line {i}: Invalid JSON: {e}")
                errors += 1

    if errors == 0:
        print(f"  {file_path} is valid.")
    else:
        print(f"  {file_path} has {errors} error(s).")
    return errors == 0

file_name = "" # Global to use in validate_jsonl

def main():
    global file_name
    datasets = {
        "build123d_cot_dataset.jsonl": {
            "required": ["base_code", "base_file", "instruction", "iter_dir", "new_code", "task_type", "technical_summary"],
            "optional": ["label_thought", "metrics_diff", "mutation_thought"]
        },
        "build123d_inverse_dataset.jsonl": {
            "required": ["base_code", "base_file", "instruction", "iter_dir", "new_code", "task_type", "technical_summary"],
            "optional": []
        },
        "build123d_agent_dataset.jsonl": {
            "required": ["base_code", "base_file", "instruction", "iter_dir", "new_code"],
            "optional": ["task_type"]
        },
        "build123d_combined_dataset.jsonl": {
            "required": ["instruction", "base_code", "new_code", "task_type", "thought", "technical_summary", "edits", "metadata"],
            "optional": []
        }
    }

    all_valid = True
    for name, schema in datasets.items():
        file_name = name
        if not validate_jsonl(file_name, schema["required"], schema["optional"]):
            all_valid = False
        print()

    if not all_valid:
        sys.exit(1)

if __name__ == "__main__":
    main()
