# VibeCAD: Synthetic Data Generation for CAD-Coding Agents

This repository contains a suite of tools designed to generate high-quality, Chain-of-Thought (CoT) datasets for fine-tuning Large Language Models (LLMs) and Vision-Language Models (VLMs) on the task of **reality-constrained editing of complex 3D models** using the `build123d` Python library.

## Project Goal
The core objective is to move beyond simple "code generation from scratch" and instead train models that can:
1.  **Understand existing geometry:** Interpret code-defined 3D models and their visual representations.
2.  **Reason about constraints:** Navigate 3D space using robust selectors (e.g., "the top-most face") rather than fragile indices.
3.  **Perform incremental edits:** Modify models based on natural language feedback, industrial design standards, and manufacturability requirements.

---

## Evolutionary History (Reverse Chronological)

### 1. `cot_cad_loop.py` — The Agent-Critic Loop (Final Iteration)
This script implements a sophisticated **Designer-Coder Multi-Agent Loop**. It emulates the real-world workflow between a Senior Industrial Designer (VLM) and a CAD Engineer (LLM).

*   **Mechanism:**
    *   **Incremental Construction:** The model is built one feature at a time (Base -> Secondary Features -> Holes -> Finishing).
    *   **VLM Critic:** After each code execution, a VLM (e.g., Claude 3.5 Sonnet) reviews the 4-view render. It compares the current state against the goal and the previous iteration.
    *   **Chain-of-Thought Guidance:** The Designer Agent provides technical critique (e.g., "Wall thickness is too low," "Add 5mm fillets here") and explicit instructions for the next step.
    *   **Completion Token:** The loop continues until the Designer issues a `[FINAL_MODEL_COMPLETE]` signal.
*   **Data Yield:** High-fidelity multi-turn dialogues where every code change is preceded by expert reasoning and visual verification.

### 2. `data_generator_cot.py` — CoT-Enhanced Inverse Labeling
Building on the inverse generation concept, this iteration focuses on the **internal reasoning** required to perform a mutation.

*   **Mechanism:**
    *   Mutates base models using specific complexity strategies (e.g., "Subtract a Cylinder to create a mounting hole").
    *   Forces the LLM to output a `mutation_thought` before providing the code.
    *   Uses a VLM to generate a `label_thought` by analyzing the visual diff and geometric metrics (volume change, face counts) before formulating the final user instruction.
*   **Data Yield:** Training pairs that include `Instruction -> Reasoning -> Code`.

### 3. `data_generator_inverse.py` — Mutation & Inverse Labeling
This iteration introduced the **Inverse Problem** approach to data generation. Instead of asking a model to "make a change," we change the model first and then ask a VLM what the instruction *should* have been.

*   **Mechanism:**
    *   **Procedural Mutation:** Randomly applies functional features (mounting holes, slots, bosses) to human-written base examples.
    *   **Visual Grounding:** Compares "Before" and "After" renders.
    *   **Labeling:** The VLM "back-derives" the natural language prompt that would justify the observed geometric delta.
*   **Data Yield:** Grounded instructions where the "ground truth" code change is guaranteed to produce the intended visual result.

### 5. `data_generator.py` — Proposal-Validation-Fix Loop
The first iteration to introduce autonomous self-correction.

*   **Mechanism:**
    *   **Proposal Agent:** Suggests a logical edit based on a strategy.
    *   **Validation Agent:** A VLM checks if the resulting render matches the proposal.
    *   **Fix Loop:** If the code fails to compile or the VLM rejects the visual result, a "Fix Agent" is called with the error log and renders to attempt a repair (up to 5 retries).
*   **Data Yield:** Robust code-edit pairs that have been "unit tested" by a visual critic.

### 6. `astgen.py` — Procedural AST Mutation (Initial Baseline)
The foundational approach used pure programmatic generation to create volume.

*   **Mechanism:**
    *   **AST Manipulation:** Directly manipulates the Python Abstract Syntax Tree (AST) to compose `build123d` modules from primitives (Box, Cylinder, Extrude).
    *   **Geometric Deltas:** Calculates exact mathematical differences in topology (volume, bounding box, face types).
    *   **LLM Description:** An LLM converts these raw mathematical deltas into CoT reasoning and user prompts.
*   **Data Yield:** Massive quantities of simple, valid CAD code pairs without requiring human-written templates.

---

## Key Principles & Methodology

*   **Stateless Algebraic API:** All generators prioritize the `build123d` algebraic syntax (e.g., `part = Box() - Hole()`) over stateful builders. This makes the code more readable for LLMs and easier to manipulate programmatically.
*   **Robust Selectors:** Data is filtered to ensure models use coordinate-based or topological selectors (e.g., `.faces().sort_by(Axis.Z)[-1]`) rather than volatile indices (`.faces()[5]`), ensuring edits are stable across geometry changes.
*   **Multi-View Rendering:** Every example is validated using a standardized 4-view layout (Isometric, Front, Top, Right) with coordinate axes and grids, providing the VLM with the spatial context needed for accurate critique.
*   **Geometric Verification:** Beyond visual checks, the pipeline uses `geometry_checker.py` to extract hard metrics (volume, surface area, bounding boxes) to verify that a "hole" actually removed material and a "fillet" actually modified edges.
