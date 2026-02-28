import json
import os

def standardize_edits(data):
    """Ensure edits is a list of {"search": ..., "replace": ...}."""
    if "edits" in data and isinstance(data["edits"], list):
        # Already has edits list, ensure keys are correct (search/replace)
        standardized = []
        for edit in data["edits"]:
            if isinstance(edit, dict):
                standardized.append({
                    "search": edit.get("search", ""),
                    "replace": edit.get("replace", "")
                })
        return standardized
    
    if "search_block" in data and "replace_block" in data:
        return [{
            "search": data["search_block"],
            "replace": data["replace_block"]
        }]
    
    return []

def consolidate_thought(data):
    """Consolidate various thought fields into one."""
    thoughts = []
    if data.get("mutation_thought"):
        thoughts.append(f"Mutation Thought:\n{data['mutation_thought']}")
    if data.get("label_thought"):
        thoughts.append(f"Label Thought:\n{data['label_thought']}")
    
    return "\n\n".join(thoughts)

def merge_datasets(output_file):
    datasets = {
        "build123d_cot_dataset.jsonl": "cot",
        "build123d_inverse_dataset.jsonl": "inverse",
        "build123d_agent_dataset.jsonl": "agent"
    }

    total_count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_name, source in datasets.items():
            if not os.path.exists(file_name):
                print(f"Skipping {file_name} (not found)")
                continue
            
            print(f"Processing {file_name}...")
            count = 0
            with open(file_name, 'r', encoding='utf-8') as infile:
                for line in infile:
                    try:
                        data = json.loads(line)
                        
                        # Build standardized record
                        record = {
                            "instruction": data.get("instruction", ""),
                            "base_code": data.get("base_code", ""),
                            "new_code": data.get("new_code", ""),
                            "task_type": data.get("task_type", "general"),
                            "thought": consolidate_thought(data),
                            "technical_summary": data.get("technical_summary", ""),
                            "edits": standardize_edits(data),
                            "metadata": {
                                "source_dataset": source,
                                "base_file": data.get("base_file", ""),
                                "iter_dir": data.get("iter_dir", ""),
                                "metrics_diff": data.get("metrics_diff", {})
                            }
                        }
                        
                        outfile.write(json.dumps(record) + '\n')
                        count += 1
                    except json.JSONDecodeError:
                        continue
            print(f"  Added {count} records.")
            total_count += count

    print(f"\nSuccessfully created {output_file} with {total_count} total records.")

if __name__ == "__main__":
    merge_datasets("build123d_combined_dataset.jsonl")
